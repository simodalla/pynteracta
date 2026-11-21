# SPDX-License-Identifier: Apache-2.0
"""Fake condivisi dai test del login Google (spec 10): portachiavi, browser, risposte di Google.

Nessuno di questi oggetti fa richieste di rete reali né apre un browser: ``MemoryKeychain``
tiene le voci in un dizionario, ``FakeBrowser`` segue il redirect verso il listener su loopback.
"""

from __future__ import annotations

from pynteracta.keychain import Keychain

# Valori finti e riconoscibili (regola "Segreti fuori dal repository").
CLIENT_ID = "000000000000-example.apps.googleusercontent.com"
CLIENT_SECRET = "GOCSPX-example-not-a-secret"
REFRESH_TOKEN = "1//example-refresh-token"
ACCESS_TOKEN = "ya29.example-access-token"
EMAIL = "mario.rossi@example.org"


class _MemoryBackend:
    """Backend di ``keyring`` in memoria, con le tre operazioni che usa :class:`Keychain`."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        from keyring.errors import PasswordDeleteError  # noqa: PLC0415

        if (service, username) not in self.store:
            raise PasswordDeleteError("not found")
        del self.store[(service, username)]


class MemoryKeychain(Keychain):
    """Un :class:`Keychain` vero su un backend in memoria: passa dalla stessa mappatura errori."""

    def __init__(self) -> None:
        self._memory = _MemoryBackend()
        super().__init__(self._memory)

    @property
    def entries(self) -> dict[str, str]:
        """Le voci salvate, per nome (il servizio è sempre ``pynteracta``)."""
        return {name: value for (_service, name), value in self._memory.store.items()}
