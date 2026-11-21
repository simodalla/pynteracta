# SPDX-License-Identifier: Apache-2.0
"""Fake condivisi dai test del login Google (spec 10): portachiavi, browser, risposte di Google.

Nessuno di questi oggetti fa richieste di rete reali né apre un browser: ``MemoryKeychain``
tiene le voci in un dizionario, ``FakeBrowser`` segue il redirect verso il listener su loopback.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.parse
import urllib.request

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


AUTH_CODE = "4/example-authorization-code"


class FakeBrowser:
    """Al posto di ``webbrowser.open``: segue il redirect verso il listener su loopback.

    Legge ``redirect_uri`` e ``state`` dall'indirizzo di consenso e, in un thread, fa le
    richieste che farebbe il browser dopo il consenso (``urllib``, che ``respx`` non
    intercetta). ``query`` sostituisce i parametri della risposta (per esempio un ``state``
    diverso o ``error=access_denied``); ``before`` sono percorsi richiesti prima del redirect
    (per esempio ``/favicon.ico``) e ``after`` dopo; ``follow=False`` non fa alcuna richiesta
    (timeout); ``opens`` è il valore restituito, come ``webbrowser.open``.
    """

    def __init__(
        self,
        *,
        opens: bool = True,
        follow: bool = True,
        query: dict[str, str] | None = None,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
    ) -> None:
        self.opens = opens
        self.follow = follow
        self.query = query
        self.before = before
        self.after = after
        self.urls: list[str] = []
        self.pages: list[tuple[int, str]] = []
        self.refused_after: list[bool] = []
        self._thread: threading.Thread | None = None

    def __call__(self, url: str) -> bool:
        self.urls.append(url)
        if self.follow:
            self.start(url)
        return self.opens

    def start(self, url: str) -> None:
        """Segue il redirect di ``url`` (usato anche quando il browser "non si apre")."""
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        query = self.query or {"code": AUTH_CODE, "state": params["state"]}
        redirect = params["redirect_uri"]
        self._thread = threading.Thread(target=self._visit, args=(redirect, query), daemon=True)
        self._thread.start()

    def _get(self, url: str) -> None:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                self.pages.append((resp.status, resp.read().decode("utf-8")))
        except urllib.error.HTTPError as exc:
            self.pages.append((exc.code, exc.read().decode("utf-8")))

    def _visit(self, redirect: str, query: dict[str, str]) -> None:
        for path in self.before:
            self._get(f"{redirect}{path}")
        self._get(f"{redirect}/?{urllib.parse.urlencode(query)}")
        for path in self.after:
            try:
                self._get(f"{redirect}{path}")
                self.refused_after.append(False)
            except (urllib.error.URLError, OSError):
                self.refused_after.append(True)

    def join(self) -> None:
        if self._thread is not None:
            self._thread.join(timeout=10)

    @property
    def called(self) -> bool:
        return bool(self.urls)
