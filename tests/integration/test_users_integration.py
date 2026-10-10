# SPDX-License-Identifier: Apache-2.0
"""Integration test opt-in del ciclo di scrittura di un utente (spec 05).

Crea ed elimina un utente **reale** sul tenant: parte solo con ``PYNTERACTA_TEST_WRITE_USERS=1``,
oltre all'ambiente integration. Le stampe ``[05-C26]`` servono al maintainer (task T15).
"""

from __future__ import annotations

import os
import time

import pytest

from pynteracta.client import InteractaClient
from pynteracta.exceptions import NotFoundError

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


def _require_flag(name: str) -> None:
    if os.environ.get(name) != "1":
        pytest.skip(f"{name} is not 1")


@pytest.fixture
def client() -> InteractaClient:
    from pathlib import Path  # noqa: PLC0415

    from pynteracta.auth import load_service_account_key  # noqa: PLC0415

    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    api_version = int(os.environ.get("PYNTERACTA_API_VERSION", "2"))
    sa_path = Path(_require_env("PYNTERACTA_SERVICE_ACCOUNT_KEY"))
    if not sa_path.exists():
        pytest.skip(f"Service account key not found: {sa_path}")
    credentials = load_service_account_key(sa_path)
    return InteractaClient(
        base_url, base_path=base_path, api_version=api_version, credentials=credentials
    )


class TestUsersWriteIntegration:
    # criterio: 05-C25
    def test_create_edit_credentials_delete_cycle(self, client: InteractaClient) -> None:
        _require_flag("PYNTERACTA_TEST_WRITE_USERS")
        domain = os.environ.get("PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN") or "example.com"
        stamp = int(time.time())
        email = f"pynteracta-it-{stamp}@{domain}"
        with client:
            created = client.users.create(
                firstname="pynteracta-it",
                lastname=str(stamp),
                contact_email=email,
                user_credentials_configuration={"custom": {"username": email, "active": True}},
                reset_user_custom_credentials_command={"generatePassword": True},
            )
            user_id = created.user_id
            assert user_id is not None
            try:
                password = created.generated_password
                print(
                    f"\n[05-C26] users.create: generated_password tipo={type(password).__name__} "
                    f"elementi={len(password) if password else 0} "
                    f"lunghezze={[len(p) for p in password] if password else None} "
                    f"expired_credentials={created.expired_credentials!r} "
                    f"sent_email_notify={created.sent_email_notify!r}"
                )
                form = client.users.get_for_edit(user_id)
                assert form.occ_token is not None
                # Il server esige firstname e lastname e azzera contactEmail se omessa (T15).
                client.users.edit(
                    user_id,
                    form.occ_token,
                    firstname=form.first_name,
                    lastname=f"{stamp}-edited",
                    contact_email=form.contact_email,
                )
                after_edit = client.users.get_for_edit(user_id)
                print(
                    "[05-C26] users.edit(firstname, lastname, contactEmail) con gli altri campi "
                    f"omessi: external_id={after_edit.external_id!r} "
                    f"userSettings presenti={after_edit.raw.userSettings is not None} "
                    f"userInfo presente={after_edit.raw.userInfo is not None}"
                )
                assert after_edit.last_name == f"{stamp}-edited"
                assert after_edit.contact_email == email
                creds = client.users.get_credentials_for_edit(user_id)
                assert creds.occ_token is not None
                client.users.edit_credentials(
                    user_id,
                    creds.occ_token,
                    custom={
                        "username": email,
                        "canUserManageCustomCredentials": True,
                        "active": True,
                    },
                )
                after_creds = client.users.get_credentials_for_edit(user_id)
                print(
                    "[05-C26] users.edit_credentials(custom=...) con google e microsoft omessi: "
                    f"has_google={after_creds.has_google_credentials!r} "
                    f"has_custom={after_creds.has_custom_credentials!r} "
                    f"custom_active={after_creds.custom_active!r}"
                )
                assert after_creds.custom_username == email
                assert after_creds.occ_token is not None
                client.users.edit_credentials(
                    user_id, after_creds.occ_token, custom={"active": False}
                )
                removed = client.users.get_credentials_for_edit(user_id)
                print(
                    "[05-C26] users.edit_credentials(custom={'active': False}) senza username: "
                    f"has_custom={removed.has_custom_credentials!r}"
                )
                assert removed.has_custom_credentials is False
            finally:
                client.users.delete(user_id)
            try:
                after = client.users.get_for_edit(user_id)
                print(f"[05-C26] dopo delete il form esiste ancora: blocked={after.blocked!r}")
            except NotFoundError:
                print("[05-C26] dopo delete: NotFoundError, l'utente non esiste più")
