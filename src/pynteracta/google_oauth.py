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

from pynteracta.exceptions import AuthenticationError

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
