from pydantic import BaseModel, PrivateAttr
from pydantic.typing import Any

from ..utils import to_camel


class InteractaModel(BaseModel):
    class Config:
        alias_generator = to_camel

    def get_absolute_url(self, base_url: str | None = None) -> str:
        raise NotImplementedError


class SchemaOut(InteractaModel):
    _response: Any = PrivateAttr(None)


class PagedItemsOut(SchemaOut):
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
