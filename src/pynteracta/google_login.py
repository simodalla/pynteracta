# SPDX-License-Identifier: Apache-2.0
"""Login Google integrato: sessione nel portachiavi e rinnovo senza browser (spec 10).

Superficie pubblica per chi usa la libreria da Python. La sessione di un profilo (refresh
token, email dell'account, data del login) sta nel portachiavi di sistema, in una voce per
tenant e profilo; il client secret in una voce per id del client. Nessuna funzione di questo
modulo scrive sullo standard output, e nessun log contiene token, segreti o l'email.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import structlog

from pynteracta import google_oauth, keychain
from pynteracta.config import Profile
from pynteracta.exceptions import AuthenticationError
from pynteracta.keychain import Keychain, client_secret_entry, session_entry
from pynteracta.transport import HttpTransport
from pynteracta.urls import build_api_base

_log = structlog.get_logger("pynteracta.google_login")

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
