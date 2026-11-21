# SPDX-License-Identifier: Apache-2.0
"""Protocollo OAuth 2.0 di Google per il login integrato (spec 10).

PKCE, indirizzo di consenso e listener del redirect su loopback. Nessuna funzione di questo
modulo scrive sullo standard output né registra codici, verificatori o token.
"""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
import socketserver
import time
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import TracebackType
from typing import Any

import httpx
import structlog

from pynteracta.exceptions import AuthenticationError, InteractaError, ServerError
from pynteracta.transport import HttpTransport

_log = structlog.get_logger("pynteracta.google_oauth")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPE = "email"

_LOOPBACK = "127.0.0.1"
_PAGE_OK = "Sign-in complete. You can close this window.\n"
_PAGE_FAILED = "Sign-in failed. Return to the terminal for details.\n"
_SAFE_ERROR = re.compile(r"^[a-z_]{1,64}$")


@dataclass(frozen=True)
class Pkce:
    """Verificatore e challenge PKCE (S256) più il parametro ``state`` di un login."""

    verifier: str = field(repr=False)
    challenge: str
    state: str = field(repr=False)


def new_pkce() -> Pkce:
    """Valori nuovi a ogni login: verificatore di 86 caratteri e ``state`` casuale."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return Pkce(verifier=verifier, challenge=challenge, state=secrets.token_urlsafe(32))


def build_auth_url(*, client_id: str, redirect_uri: str, challenge: str, state: str) -> str:
    """L'indirizzo di consenso: scope ``email`` soltanto, PKCE ``S256``, refresh token chiesto.

    ``access_type=offline`` e ``prompt=consent`` fanno restituire il refresh token anche quando
    il consenso è già stato dato.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


@dataclass
class _Outcome:
    code: str | None = None
    error: str | None = None
    state_ok: bool = False


class _Server(HTTPServer):
    """``HTTPServer`` su loopback che non risolve il nome dell'host (``getfqdn`` è lento)."""

    expected_state: str = ""
    outcome: _Outcome | None = None

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        self.server_name = _LOOPBACK
        self.server_port = self.server_address[1]


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def do_GET(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        code = query.get("code", [None])[0]
        error = query.get("error", [None])[0]
        if code is None and error is None:
            # Per esempio /favicon.ico: non è la risposta al redirect e non conta.
            self._reply(404, "Not found.\n")
            return
        state = query.get("state", [""])[0] or ""
        outcome = _Outcome(
            code=code,
            error=error,
            state_ok=secrets.compare_digest(state, self.server.expected_state),
        )
        self.server.outcome = outcome
        ok = outcome.code is not None and outcome.error is None and outcome.state_ok
        self._reply(200, _PAGE_OK if ok else _PAGE_FAILED)

    def _reply(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # La riga di richiesta contiene il codice di autorizzazione: non si registra nulla.
        return


@dataclass(frozen=True)
class GoogleTokens:
    """Token restituiti dal token endpoint; nessuno dei due compare in ``repr``."""

    access_token: str = field(repr=False)
    refresh_token: str | None = field(default=None, repr=False)


_INVALID_GRANT = (
    "Google rejected the saved session (invalid_grant): run `pynteracta auth login --google` again."
)
_INVALID_CLIENT = (
    "Google rejected the OAuth client (invalid_client): run "
    "`pynteracta auth login --google --replace-client-secret` with the current client secret."
)
_HTTP_5XX = 500


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _raise_for_google_error(transport: HttpTransport, response: httpx.Response, url: str) -> Any:
    """Restituisce il corpo JSON di una risposta riuscita, altrimenti solleva l'errore mappato.

    L'eccezione porta in ``response_body`` solo ``error`` ed ``error_description``, mai il corpo
    intero, e passa da ``hooks.on_error``. Il log ``google.token_error`` ha il solo codice.
    """
    body = _json_or_none(response)
    common: dict[str, Any] = {
        "status_code": response.status_code,
        "request_method": response.request.method,
        "request_url": url,
    }
    err: InteractaError
    if response.is_success and isinstance(body, dict):
        return body
    if response.status_code >= _HTTP_5XX:
        err = ServerError(f"Google server error {response.status_code}", **common)
    elif isinstance(body, dict) and isinstance(body.get("error"), str):
        raw = body["error"]
        code = raw if _SAFE_ERROR.match(raw) else "unknown_error"
        description = body.get("error_description")
        common["response_body"] = {
            "error": code,
            "error_description": description if isinstance(description, str) else None,
        }
        _log.warning("google.token_error", error=code)
        if code == "invalid_grant":
            err = AuthenticationError(_INVALID_GRANT, **common)
        elif code == "invalid_client":
            err = AuthenticationError(_INVALID_CLIENT, **common)
        else:
            err = AuthenticationError(f"Google OAuth error: {code}.", **common)
    else:
        err = AuthenticationError(
            f"Unexpected response from Google (HTTP {response.status_code}).", **common
        )
    transport.notify_error(err)
    raise err


def _tokens(transport: HttpTransport, body: dict[str, Any], url: str) -> GoogleTokens:
    access = body.get("access_token")
    refresh = body.get("refresh_token")
    if not isinstance(access, str) or not access:
        err = AuthenticationError("Google token response has no access token.", request_url=url)
        transport.notify_error(err)
        raise err
    return GoogleTokens(
        access_token=access, refresh_token=refresh if isinstance(refresh, str) else None
    )


def exchange_code(  # noqa: PLR0913
    transport: HttpTransport,
    *,
    code: str,
    verifier: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> GoogleTokens:
    """Scambia il codice di autorizzazione con access e refresh token (una richiesta).

    Raises:
        AuthenticationError: errore OAuth di Google (``invalid_client`` indica
            ``--replace-client-secret``) o risposta senza refresh token.
        ServerError: risposta ``5xx``. TransportError: timeout o rete.
    """
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    response = transport.request_external("POST", TOKEN_URL, form=form)
    tokens = _tokens(transport, _raise_for_google_error(transport, response, TOKEN_URL), TOKEN_URL)
    if tokens.refresh_token is None:
        err = AuthenticationError(
            "Google did not return a refresh token: sign in again.", request_url=TOKEN_URL
        )
        transport.notify_error(err)
        raise err
    return tokens


def refresh_access_token(
    transport: HttpTransport, *, refresh_token: str, client_id: str, client_secret: str
) -> GoogleTokens:
    """Un access token nuovo dal refresh token (una richiesta, nessun nuovo tentativo).

    ``refresh_token`` del risultato è valorizzato solo se Google ne restituisce uno nuovo.
    """
    form = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    response = transport.request_external("POST", TOKEN_URL, form=form)
    return _tokens(transport, _raise_for_google_error(transport, response, TOKEN_URL), TOKEN_URL)


def fetch_email(transport: HttpTransport, access_token: str) -> str | None:
    """L'email dell'account dall'endpoint userinfo, o ``None`` se Google non la restituisce.

    L'email serve solo a ``auth status``: una risposta d'errore o senza email non fa fallire il
    login. Timeout ed errori di rete restano :class:`TransportError`.
    """
    response = transport.request_external("GET", USERINFO_URL, bearer_token=access_token)
    body = _json_or_none(response) if response.is_success else None
    if not isinstance(body, dict):
        _log.info("google.userinfo_unavailable", status=response.status_code)
        return None
    email = body.get("email")
    return email if isinstance(email, str) and email else None


def revoke(transport: HttpTransport, token: str) -> None:
    """Revoca il refresh token presso Google (una richiesta).

    Un token già non valido (``invalid_token``) conta come revocato.
    """
    response = transport.request_external("POST", REVOKE_URL, form={"token": token})
    if response.is_success:
        return
    body = _json_or_none(response)
    if (
        response.status_code < _HTTP_5XX
        and isinstance(body, dict)
        and body.get("error") == "invalid_token"
    ):
        return
    _raise_for_google_error(transport, response, REVOKE_URL)


class LoopbackReceiver:
    """Listener del redirect OAuth su ``127.0.0.1``, porta scelta dal sistema.

    Accetta una sola risposta al redirect: dopo la prima chiude il socket. Le richieste senza
    ``code`` né ``error`` ricevono ``404`` e non contano. Va chiuso in ogni caso, anche su
    ``KeyboardInterrupt``: si usa come context manager o con :meth:`close` in un ``finally``.
    """

    def __init__(self) -> None:
        self._server = _Server((_LOOPBACK, 0), _Handler)
        self._closed = False

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    @property
    def redirect_uri(self) -> str:
        return f"http://{_LOOPBACK}:{self.address[1]}"

    def wait(self, state: str, timeout: float) -> str:
        """Attende la risposta al redirect e restituisce il codice di autorizzazione.

        Raises:
            AuthenticationError: ``state`` diverso da quello inviato, errore restituito da
                Google (per esempio ``access_denied``), nessuna risposta entro ``timeout``.
        """
        self._server.expected_state = state
        deadline = time.monotonic() + timeout
        try:
            while self._server.outcome is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    msg = f"No sign-in response within {timeout:g} seconds."
                    raise AuthenticationError(msg)
                self._server.timeout = remaining
                self._server.handle_request()
        finally:
            self.close()
        outcome = self._server.outcome
        if outcome.error is not None:
            error = outcome.error if _SAFE_ERROR.match(outcome.error) else "unknown_error"
            raise AuthenticationError(f"Google sign-in failed: {error}.")
        if not outcome.state_ok:
            raise AuthenticationError(
                "Sign-in response does not match this login (state mismatch)."
            )
        assert outcome.code is not None  # garantito dal handler
        return outcome.code

    def close(self) -> None:
        """Chiude il socket; chiamarlo più volte non è un errore."""
        if not self._closed:
            self._closed = True
            self._server.server_close()

    def __enter__(self) -> LoopbackReceiver:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
