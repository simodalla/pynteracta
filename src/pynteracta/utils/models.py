from functools import cached_property

from pydantic import BaseModel, computed_field


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
    deleted: list[int] = []
    blocked: list[int] = []

    @computed_field
    @cached_property
    def counts(self) -> dict:
        result = {}
        for field in list(UsersStats.model_json_schema()["properties"].keys()):
            result[field] = len(getattr(self, field))
        return result
