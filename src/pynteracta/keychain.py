# SPDX-License-Identifier: Apache-2.0
"""Accesso al portachiavi di sistema per la sessione Google e il client secret (spec 10).

È l'unico modulo che legge e scrive refresh token e client secret. ``keyring`` arriva con
l'extra ``pynteracta[google]`` ed è importato solo dentro :func:`open_keychain`, così
l'installazione base non lo richiede. Sono accettati solo i portachiavi di sistema elencati in
``_ACCEPTED_MODULES``: un backend assente, nullo, che conserva in chiaro su file o sconosciuto è
rifiutato, senza ripiego (RNF-012).
"""

from __future__ import annotations

import importlib
from typing import Any, Protocol

from pynteracta.auth import build_cache_key
from pynteracta.exceptions import ConfigurationError

SERVICE = "pynteracta"

_ACCEPTED_MODULES = frozenset(
    {
        "keyring.backends.macOS",
        "keyring.backends.Windows",
        "keyring.backends.SecretService",
        "keyring.backends.libsecret",
        "keyring.backends.kwallet",
    }
)
_CHAINER_MODULE = "keyring.backends.chainer"

_MISSING_EXTRA = (
    "The integrated Google login needs the system keychain support: install pynteracta[google]."
)
_NO_KEYCHAIN = (
    "No system keychain available: use a static Google token instead "
    "(--google-token or $PYNTERACTA_GOOGLE_OAUTH2_TOKEN)."
)


class KeyringBackend(Protocol):
    """Le tre operazioni di un backend di ``keyring`` usate da :class:`Keychain`."""

    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class Keychain:
    """Voci del servizio ``pynteracta`` nel portachiavi di sistema.

    Un errore del backend diventa :class:`ConfigurationError` con il solo tipo dell'errore: il
    messaggio originale potrebbe contenere il valore, quindi non è riportato né concatenato.
    """

    def __init__(self, backend: KeyringBackend) -> None:
        self._backend = backend

    def get(self, entry: str) -> str | None:
        """Il valore della voce, o ``None`` se non c'è."""
        try:
            return self._backend.get_password(SERVICE, entry)
        except Exception as exc:
            raise _keychain_error("read", exc) from None

    def set(self, entry: str, value: str) -> None:
        """Scrive (o sostituisce) la voce."""
        try:
            self._backend.set_password(SERVICE, entry, value)
        except Exception as exc:
            raise _keychain_error("write", exc) from None

    def delete(self, entry: str) -> None:
        """Elimina la voce; una voce assente non è un errore."""
        if self.get(entry) is None:
            return
        try:
            self._backend.delete_password(SERVICE, entry)
        except Exception as exc:
            raise _keychain_error("delete", exc) from None


def _keychain_error(action: str, exc: Exception) -> ConfigurationError:
    return ConfigurationError(f"System keychain error ({action}): {type(exc).__name__}.")


def session_entry(api_base: str, profile_name: str) -> str:
    """Nome della voce della sessione Google: per tenant e profilo, come la cache del token."""
    return f"google-session:{build_cache_key(api_base, profile_name)}"


def client_secret_entry(client_id: str) -> str:
    """Nome della voce del client secret: legata all'id del client OAuth."""
    return f"google-client-secret:{client_id}"


def _module_of(backend: Any) -> str:
    return str(type(backend).__module__)


def _is_accepted(backend: Any) -> bool:
    module = _module_of(backend)
    if module == _CHAINER_MODULE:
        inner = list(getattr(backend, "backends", []) or [])
        return bool(inner) and all(_module_of(b) in _ACCEPTED_MODULES for b in inner)
    return module in _ACCEPTED_MODULES


def open_keychain() -> Keychain:
    """Apre il portachiavi di sistema.

    Raises:
        ConfigurationError: ``keyring`` non installato (il messaggio cita
            ``pynteracta[google]``), oppure backend non accettato (il messaggio rimanda al token
            statico).
    """
    try:
        keyring = importlib.import_module("keyring")
    except ImportError:
        raise ConfigurationError(_MISSING_EXTRA) from None
    try:
        backend = keyring.get_keyring()
    except Exception:
        raise ConfigurationError(_NO_KEYCHAIN) from None
    if not _is_accepted(backend):
        raise ConfigurationError(_NO_KEYCHAIN)
    return Keychain(backend)
