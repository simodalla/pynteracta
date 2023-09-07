from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

from ..utils import to_camel


class InteractaModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    def get_absolute_url(self, base_url: str | None = None) -> str:
        raise NotImplementedError


class InteractaOut(InteractaModel):
    _response: Any = PrivateAttr(None)


class PagedItemsOut(InteractaOut):
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


class InteractaIn(InteractaModel):
    model_config = ConfigDict(validate_assignment=True)

    page_token: str | None = None
    page_size: int = 15
    calculate_total_items_count: bool | None = True
    order_desc: bool | None = None
