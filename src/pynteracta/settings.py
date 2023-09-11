from pydantic import BaseModel

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


class InteractaSettings(BaseModel):
    base_url: str | None = None
    service_file_path: str | None = None
    log_api_calls: bool = False
    operators_group_id: int | None = None
    users: InteractaUsersSettings | None = None
