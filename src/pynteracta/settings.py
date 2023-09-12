import json
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    HttpUrl,
    SecretStr,
    computed_field,
)
from pydantic_settings_toml import TomlSettings

from pynteracta.models import ServiceAccountModel

from .enums import InteractaLoginProvider


class CommunitySettings(BaseModel):
    community_id: int = 0
    custom_fields: dict[str, int] = {}
    default_watcher_user_ids: list[int] | None = None

    @property
    def aliases(self):
        aliases = {}
        for attr, value in self.custom_fields.items():
            aliases[attr] = str(value)
        return aliases

    @property
    def custom_fields_id(self) -> list[int]:
        return list(self.custom_fields.values())


class InteractaUsersSettings(BaseModel):
    check_by_email: bool = True
    check_by_external_auth_service: bool = False
    external_login_providers: InteractaLoginProvider | None = None


class ApiSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    base_url: HttpUrl
    api_version: str = "v2"
    api_endpoint_path: str = "portal/api/external/"
    auth_service_file_path: Path | None = None
    auth_service_account: ServiceAccountModel | None = None
    auth_username: EmailStr | None = None
    auth_password: SecretStr | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.auth_service_file_path:
            try:
                with open(self.auth_service_file_path) as f:
                    data = json.load(f)
                    self.auth_service_account = ServiceAccountModel(**data)
                return
            except Exception as exc:
                raise ValueError(f"Wrong service account settings: {exc}") from exc
        if not self.auth_username or not self.auth_password:
            raise ValueError("No authentication settings is set")

    @computed_field
    @cached_property
    def api_url(self) -> HttpUrl:
        url = f"{self.base_url}{self.api_endpoint_path}{self.api_version}"
        return url


class InteractaSettings(ApiSettings):
    log_api_calls: bool = False
    operators_group_id: int | None = None
    users: InteractaUsersSettings | None = None


class AppSettings(TomlSettings):
    interacta: InteractaSettings | None = None
