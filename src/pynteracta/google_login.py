# SPDX-License-Identifier: Apache-2.0
"""Login Google integrato: sessione nel portachiavi e rinnovo senza browser (spec 10).

Superficie pubblica per chi usa la libreria da Python. La sessione di un profilo (refresh
token, email dell'account, data del login) sta nel portachiavi di sistema, in una voce per
tenant e profilo; il client secret in una voce per id del client. Nessuna funzione di questo
modulo scrive sullo standard output, e nessun log contiene token, segreti o l'email.
"""

from __future__ import annotations

import json
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import ValidationError

from pynteracta import google_oauth, keychain
from pynteracta.auth import clear_cached_token
from pynteracta.config import (
    Profile,
    config_file_path,
    resolve_profile,
    resolve_profile_name,
    write_profile_fields,
)
from pynteracta.exceptions import AuthenticationError, ConfigurationError
from pynteracta.hooks import ClientHooks
from pynteracta.keychain import Keychain, client_secret_entry, session_entry
from pynteracta.transport import HttpTransport
from pynteracta.urls import build_api_base

_log = structlog.get_logger("pynteracta.google_login")

# Base del transport dedicato agli endpoint di Google: request_external usa URL assoluti.
GOOGLE_OAUTH_BASE = "https://oauth2.googleapis.com"

LOGIN_HINT = "run `pynteracta auth login --google`"
_NO_SESSION = f"No saved Google session for this profile: {LOGIN_HINT}."


@dataclass(frozen=True)
class _Session:
    """Contenuto della voce della sessione; refresh token ed email non compaiono in ``repr``."""

    refresh_token: str = field(repr=False)
    email: str | None = field(repr=False)
    login_at: str

    def dumps(self) -> str:
        return json.dumps(
            {"refresh_token": self.refresh_token, "email": self.email, "login_at": self.login_at}
        )


def _read_session(kc: Keychain, entry: str) -> _Session | None:
    """La sessione salvata, o ``None`` se la voce manca o non è leggibile."""
    raw = kc.get(entry)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("refresh_token"), str):
        return None
    email = data.get("email")
    login_at = data.get("login_at")
    return _Session(
        refresh_token=data["refresh_token"],
        email=email if isinstance(email, str) else None,
        login_at=login_at if isinstance(login_at, str) else "",
    )


def _api_base(profile: Profile) -> str:
    return build_api_base(str(profile.base_url), profile.base_path, profile.api_version)


class GoogleSessionTokenProvider:
    """Procura un access token Google dalla sessione salvata (``token_provider`` del client).

    Il ``GoogleOAuth2TokenManager`` lo chiama quando il token Interacta manca o sta per
    scadere. Refresh token e client secret si rileggono dal portachiavi a ogni chiamata, così un
    processo lungo vede un nuovo login senza riavvio. Una sola richiesta a Google, nessun nuovo
    tentativo; una sessione rifiutata resta nel portachiavi.
    """

    def __init__(
        self, *, keychain: Keychain, entry: str, client_id: str, transport: HttpTransport
    ) -> None:
        self._keychain = keychain
        self._entry = entry
        self._client_id = client_id
        self._transport = transport

    def __repr__(self) -> str:
        return f"GoogleSessionTokenProvider(entry={self._entry!r})"

    def __call__(self) -> str:
        session = _read_session(self._keychain, self._entry)
        secret = self._keychain.get(client_secret_entry(self._client_id))
        if session is None or secret is None:
            raise AuthenticationError(_NO_SESSION)
        tokens = google_oauth.refresh_access_token(
            self._transport,
            refresh_token=session.refresh_token,
            client_id=self._client_id,
            client_secret=secret,
        )
        if tokens.refresh_token is not None and tokens.refresh_token != session.refresh_token:
            updated = _Session(
                refresh_token=tokens.refresh_token, email=session.email, login_at=session.login_at
            )
            self._keychain.set(self._entry, updated.dumps())
        _log.info("google.token_refreshed", session=self._entry)
        return tokens.access_token


@dataclass(frozen=True)
class GoogleLoginResult:
    """Esito di :func:`login`. Non contiene segreti; l'email non compare in ``repr``."""

    profile_name: str
    base_url: str
    email: str | None = field(repr=False)
    user_name: str


_NO_CLIENT_ID = (
    "No OAuth client configured: set google_client_id in the profile or pass --google-client-id."
)
_NO_SECRET = (
    "No Google OAuth client secret: pass it (CLI: interactive prompt or "
    "--client-secret-stdin) the first time, or after --replace-client-secret."
)
_NOT_LINKED = (
    "The Google account is not linked to an Interacta user: ask the tenant administrator "
    "to link it, then sign in again."
)
_HTTP_401 = 401


def _resolve(
    profile_name: str | None, config_file: Path | None, overrides: dict[str, Any] | None
) -> tuple[str, Profile]:
    name = resolve_profile_name(profile_name, config_file)
    try:
        profile = resolve_profile(name, config_file, overrides=overrides)
    except (KeyError, ValidationError) as exc:
        msg = f"Cannot resolve profile '{name}': set base_url in the profile or pass it."
        raise ConfigurationError(msg) from exc
    return name, profile


def _open_auth_url(
    url: str, *, open_browser: bool, on_auth_url: Callable[[str], Any] | None
) -> None:
    opened = False
    if open_browser:
        try:
            opened = bool(webbrowser.open(url))
        except Exception:
            opened = False
    if not opened and on_auth_url is not None:
        on_auth_url(url)


def _user_name(me: Any) -> str:
    ud = me.user_data_typed
    if ud is None:
        return "(unknown)"
    return f"{ud.firstName or ''} {ud.lastName or ''}".strip() or "(unknown)"


def _validate_with_interacta(
    profile: Profile, name: str, access_token: str, hooks: ClientHooks | None
) -> str:
    """Scambia l'access token Google con Interacta e restituisce il nome dell'utente."""
    from pynteracta.client import InteractaClient  # noqa: PLC0415 (client importa questo modulo)

    val_profile = profile.model_copy(
        update={
            "auth_method": "google_oauth2",
            "token_cache": "memory",
            "google_oauth2_token": None,
        }
    )
    try:
        with InteractaClient(
            profile=val_profile, google_token=access_token, profile_name=name, hooks=hooks
        ) as client:
            return _user_name(client.users.me())
    except AuthenticationError as exc:
        if exc.status_code == _HTTP_401:
            raise AuthenticationError(
                _NOT_LINKED,
                status_code=exc.status_code,
                request_method=exc.request_method,
                request_url=exc.request_url,
                request_id=exc.request_id,
            ) from None
        raise


def _restore(kc: Keychain, entry: str, previous: str | None) -> None:
    if previous is None:
        kc.delete(entry)
    else:
        kc.set(entry, previous)


def login(  # noqa: PLR0913
    profile_name: str | None = None,
    *,
    config_file: Path | None = None,
    overrides: dict[str, Any] | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    replace_client_secret: bool = False,
    open_browser: bool = True,
    timeout: float = 300.0,
    on_auth_url: Callable[[str], Any] | None = None,
    hooks: ClientHooks | None = None,
) -> GoogleLoginResult:
    """Login Google dal browser per un profilo; salva la sessione nel portachiavi.

    Senza ``profile_name`` lavora sul profilo corrente di ``config.toml``. ``client_id``
    sostituisce quello del profilo; ``client_secret`` quello salvato, che è usato se il
    parametro manca (``replace_client_secret=True`` lo ignora e richiede il parametro).
    L'indirizzo di consenso è aperto nel browser; se il browser non si apre, o con
    ``open_browser=False``, è passato a ``on_auth_url``. La funzione non scrive sullo standard
    output.

    Profilo e portachiavi si scrivono solo dopo lo scambio riuscito con Interacta; se un passo
    fallisce restano com'erano. Un login riuscito sostituisce la sessione precedente ed elimina
    il token Interacta in cache.

    Raises:
        ConfigurationError: id del client, client secret, extra ``pynteracta[google]`` o
            portachiavi mancanti; profilo senza indirizzo del tenant. Nessuna richiesta di rete.
        AuthenticationError: consenso negato, ``state`` diverso, timeout, risposta senza refresh
            token, client secret rifiutato, account non collegato a un utente Interacta.
        TransportError: timeout o errore di rete verso Google o Interacta.
    """
    name, profile = _resolve(profile_name, config_file, overrides)
    client_id = client_id or profile.google_client_id
    if not client_id:
        raise ConfigurationError(_NO_CLIENT_ID)
    kc = keychain.open_keychain()
    secret_name = client_secret_entry(client_id)
    stored_secret = kc.get(secret_name)
    secret = client_secret or (None if replace_client_secret else stored_secret)
    if not secret:
        raise ConfigurationError(_NO_SECRET)

    pkce = google_oauth.new_pkce()
    with google_oauth.LoopbackReceiver() as receiver:
        url = google_oauth.build_auth_url(
            client_id=client_id,
            redirect_uri=receiver.redirect_uri,
            challenge=pkce.challenge,
            state=pkce.state,
        )
        _open_auth_url(url, open_browser=open_browser, on_auth_url=on_auth_url)
        code = receiver.wait(pkce.state, timeout)
        redirect_uri = receiver.redirect_uri

    with HttpTransport(
        GOOGLE_OAUTH_BASE,
        hooks=hooks,
        timeout=profile.timeout_seconds,
        audit=profile.audit_log,
        audit_bodies=profile.audit_log_bodies,
    ) as transport:
        tokens = google_oauth.exchange_code(
            transport,
            code=code,
            verifier=pkce.verifier,
            client_id=client_id,
            client_secret=secret,
            redirect_uri=redirect_uri,
        )
        email = google_oauth.fetch_email(transport, tokens.access_token)
    user_name = _validate_with_interacta(profile, name, tokens.access_token, hooks)

    # --- solo da qui si scrive ---
    api_base = _api_base(profile)
    entry = session_entry(api_base, name)
    previous_session = kc.get(entry)
    assert tokens.refresh_token is not None  # garantito da exchange_code
    session = _Session(
        refresh_token=tokens.refresh_token,
        email=email,
        login_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
    kc.set(entry, session.dumps())
    try:
        if secret != stored_secret:
            kc.set(secret_name, secret)
        write_profile_fields(
            config_file_path(config_file),
            name,
            connection=profile,
            fields={"auth_method": "google_oauth2", "google_client_id": client_id},
        )
    except BaseException:
        _restore(kc, entry, previous_session)
        _restore(kc, secret_name, stored_secret)
        raise
    clear_cached_token(profile, name, api_base)
    _log.info("google.login_ok", session=entry)
    return GoogleLoginResult(
        profile_name=name,
        base_url=str(profile.base_url).rstrip("/"),
        email=email,
        user_name=user_name,
    )


KEYCHAIN_AVAILABLE = "available"


@dataclass(frozen=True)
class GoogleSessionStatus:
    """Stato del profilo e della sessione Google, letto senza rete (``auth status``).

    ``keychain`` vale ``"available"`` oppure il motivo per cui il portachiavi non è leggibile;
    in quel caso ``google_session`` e ``client_secret_saved`` sono ``None``. Nessun segreto tra
    i campi; l'email non compare in ``repr``.
    """

    profile: str
    base_url: str
    auth_method: str
    google_client_id: str | None
    keychain: str
    google_session: bool | None
    google_account: str | None = field(repr=False)
    google_login_at: str | None
    client_secret_saved: bool | None


def status(
    profile_name: str | None = None,
    *,
    config_file: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> GoogleSessionStatus:
    """Lo stato del profilo (corrente, se ``profile_name`` manca) senza richieste di rete."""
    name, profile = _resolve(profile_name, config_file, overrides)
    client_id = profile.google_client_id
    keychain_state = KEYCHAIN_AVAILABLE
    session: _Session | None = None
    has_session: bool | None = None
    secret_saved: bool | None = None
    try:
        kc = keychain.open_keychain()
        session = _read_session(kc, session_entry(_api_base(profile), name))
        has_session = session is not None
        secret_saved = client_id is not None and kc.get(client_secret_entry(client_id)) is not None
    except ConfigurationError as exc:
        keychain_state = str(exc)
    return GoogleSessionStatus(
        profile=name,
        base_url=str(profile.base_url).rstrip("/"),
        auth_method=profile.auth_method,
        google_client_id=client_id,
        keychain=keychain_state,
        google_session=has_session,
        google_account=session.email if session is not None else None,
        google_login_at=(session.login_at or None) if session is not None else None,
        client_secret_saved=secret_saved,
    )


@dataclass(frozen=True)
class GoogleLogoutResult:
    """Esito di :func:`logout`; ``keychain_error`` è il motivo se il portachiavi non è leggibile."""

    profile_name: str
    cache_cleared: bool
    session_removed: bool
    client_secret_removed: bool
    revoked: bool
    keychain_error: str | None = None


def logout(
    profile_name: str | None = None,
    *,
    config_file: Path | None = None,
    overrides: dict[str, Any] | None = None,
    forget_client_secret: bool = False,
    revoke: bool = False,
) -> GoogleLogoutResult:
    """Elimina la cache del token Interacta e la sessione Google del profilo.

    Senza rete, salvo ``revoke=True``: prima chiede a Google di revocare il refresh token (la
    revoca fa decadere il consenso a quel client anche per le altre sessioni dello stesso
    account), poi elimina comunque la sessione locale e rilancia l'eventuale errore della
    revoca. Il client secret resta, salvo ``forget_client_secret=True``. Senza portachiavi
    elimina solo la cache e lo riporta in ``keychain_error``.
    """
    name, profile = _resolve(profile_name, config_file, overrides)
    api_base = _api_base(profile)
    clear_cached_token(profile, name, api_base)
    try:
        kc = keychain.open_keychain()
    except ConfigurationError as exc:
        return GoogleLogoutResult(
            profile_name=name,
            cache_cleared=True,
            session_removed=False,
            client_secret_removed=False,
            revoked=False,
            keychain_error=str(exc),
        )
    entry = session_entry(api_base, name)
    had_session = kc.get(entry) is not None
    session = _read_session(kc, entry)
    secret_name = (
        client_secret_entry(profile.google_client_id) if profile.google_client_id else None
    )
    secret_removed = False
    revoked = False
    try:
        if revoke and session is not None:
            with HttpTransport(
                GOOGLE_OAUTH_BASE,
                timeout=profile.timeout_seconds,
                audit=profile.audit_log,
                audit_bodies=profile.audit_log_bodies,
            ) as transport:
                google_oauth.revoke(transport, session.refresh_token)
            revoked = True
    finally:
        if had_session:
            kc.delete(entry)
            _log.info("google.session_removed", session=entry)
        if forget_client_secret and secret_name is not None and kc.get(secret_name) is not None:
            kc.delete(secret_name)
            secret_removed = True
    return GoogleLogoutResult(
        profile_name=name,
        cache_cleared=True,
        session_removed=had_session,
        client_secret_removed=secret_removed,
        revoked=revoked,
    )


def session_token_provider(
    profile: Profile, profile_name: str, transport: HttpTransport
) -> GoogleSessionTokenProvider:
    """Il provider della sessione salvata per ``profile_name`` sul tenant di ``profile``.

    Controlla subito che la sessione esista, così l'errore arriva alla costruzione del client.

    Raises:
        AuthenticationError: profilo senza id del client o senza sessione salvata.
        ConfigurationError: extra ``pynteracta[google]`` assente o portachiavi non disponibile.
    """
    kc = keychain.open_keychain()
    entry = session_entry(_api_base(profile), profile_name)
    if profile.google_client_id is None or _read_session(kc, entry) is None:
        raise AuthenticationError(_NO_SESSION)
    return GoogleSessionTokenProvider(
        keychain=kc, entry=entry, client_id=profile.google_client_id, transport=transport
    )
