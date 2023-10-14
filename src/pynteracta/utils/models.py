from functools import cached_property

from pydantic import BaseModel, computed_field

from ..enums import InteractaLoginProviderEnum
from ..schemas.models import ListSystemUsersElement


class IdsData(BaseModel):
    ids: list[int] = []

    @computed_field
    @property
    def count(self) -> int:
        return len(self.ids)


class UsersStats(BaseModel):
    ids: list[int] = []
    provider_custom: list[int] = []
    provider_google: list[int] = []
    provider_microsoft: list[int] = []
    provider_empty: list[int] = []
    deleted: list[int] = []
    blocked: list[int] = []
    active: list[int] = []

    @computed_field
    @cached_property
    def counts(self) -> dict:
        result = {}
        for field in list(UsersStats.model_json_schema()["properties"].keys()):
            result[field] = len(getattr(self, field))
        return result

    @classmethod
    def create_by_user_list(cls, users: list[ListSystemUsersElement]) -> "UsersStats":
        providers = [provider.value for provider in InteractaLoginProviderEnum]
        data = {f"provider_{provider}": [] for provider in providers}
        data.update({"ids": []})
        for user in users:
            data["ids"].append(user.id)
            for provider in user.login_providers:
                data[f"provider_{provider}"].append(user.id)
            if not user.login_providers:
                data["provider_empty"].append(user.id)
            if user.blocked:
                data["blocked"].append(user.id)
            if user.deleted:
                data["deleted"].append(user.id)
            if not user.deleted and not user.blocked:
                data["active"].append(user.id)

        assert len(data["ids"]) == len(users)
        return cls(data)
