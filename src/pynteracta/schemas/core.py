from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr
from pydantic.alias_generators import to_camel


class InteractaModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        validate_assignment=True,
    )

    def get_absolute_url(self, base_url: str | None = None) -> str:
        raise NotImplementedError


class InteractaOut(InteractaModel):
    _response: Any = PrivateAttr(None)


class PaginatedOut(InteractaOut):
    items: list | None = []
    next_page_token: str | None = None
    total_items_count: int | None = None

    def count(self):
        if not self.items:
            return 0
        return len(self.items)

    def has_items(self):
        if self.count():
            return True
        return False


class ItemCreatedEditedOut(InteractaOut):
    next_occ_token: int | None = None


class PaginatedIn(InteractaModel):
    page_token: str | None = None
    page_size: int = 15
    calculate_total_items_count: bool | None = True


class InteractaIn(PaginatedIn):
    order_desc: bool | None = None
