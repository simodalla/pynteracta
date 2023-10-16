from functools import cached_property

from pydantic import BaseModel, computed_field

from ..schemas.models import ListSystemUsersElement, User


class IdsData(BaseModel):
    ids: list[int] = []

    @computed_field
    @property
    def count(self) -> int:
        return len(self.ids)


class UsersStatsList(BaseModel):
    ids: list[int] = []
    provider_custom: list[int] = []
    provider_google: list[int] = []
    provider_microsoft: list[int] = []
    no_provider: list[int] = []
    deleted: list[int] = []
    blocked: list[int] = []
    active: list[int] = []

    @computed_field
    @cached_property
    def counts(self) -> dict:
        result = {}
        for field in list(self.model_json_schema()["properties"].keys()):
            result[field] = len(getattr(self, field))
        return result

    @classmethod
    def create_by_user_list(cls, users: list[ListSystemUsersElement]) -> "UsersStatsList":
        data = {p: [] for p in cls.model_json_schema()["properties"]}
        for user in users:
            data["ids"].append(user.id)
            for provider in user.login_providers:
                data[f"provider_{provider}"].append(user.id)
            if not user.login_providers:
                data["no_provider"].append(user.id)
            if user.blocked:
                data["blocked"].append(user.id)
            if user.deleted:
                data["deleted"].append(user.id)
            if not user.deleted and not user.blocked:
                data["active"].append(user.id)

        assert len(data["ids"]) == len(users)
        return cls(**data)


class UsersStats(BaseModel):
    provider_custom: dict[int, ListSystemUsersElement | User] = {}
    provider_google: dict[int, ListSystemUsersElement | User] = {}
    provider_microsoft: dict[int, ListSystemUsersElement | User] = {}
    no_provider: dict[int, ListSystemUsersElement | User] = {}
    deleted: dict[int, ListSystemUsersElement | User] = {}
    blocked: dict[int, ListSystemUsersElement | User] = {}
    active: dict[int, ListSystemUsersElement | User] = {}

    @computed_field
    @cached_property
    def counts(self) -> dict:
        result = {}
        for field in list(self.model_json_schema()["properties"].keys()):
            result[field] = len(getattr(self, field).keys())
        return result

    @classmethod
    def create_by_user_list(cls, users: list[ListSystemUsersElement]) -> "UsersStats":
        data = {p: {} for p in cls.model_json_schema()["properties"]}

        for user in users:
            for provider in user.login_providers:
                data[f"provider_{provider}"].update({user.id: user})
            if not user.login_providers:
                data["no_provider"].update({user.id: user})
            if user.blocked:
                data["blocked"].update({user.id: user})
            elif user.deleted:
                data["deleted"].update({user.id: user})
            else:
                data["active"].update({user.id: user})
        return cls(**data)
