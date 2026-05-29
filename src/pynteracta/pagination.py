# SPDX-License-Identifier: Apache-2.0
"""Lazy pagination iterator over paged API responses."""

from __future__ import annotations

from collections.abc import Callable
from typing import Self, TypeVar

T = TypeVar("T")
P = TypeVar("P")


class PageLike[T]:
    """A single page of results with a continuation token."""

    @property
    def next_page_token(self) -> str | None:
        raise NotImplementedError

    def page_items(self) -> list[T]:
        raise NotImplementedError


def _default_token_getter(page: object) -> str | None:
    token = getattr(page, "next_page_token", None)
    if token is None or isinstance(token, str):
        return token
    return None


class PageIterator[T]:
    """Lazy iterator that fetches the next page only when the current one is exhausted.

    Stops when ``nextPageToken`` is empty or ``None``.  Propagates exceptions from
    the underlying page fetch callable.
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], P],
        *,
        items_getter: Callable[[P], list[T]],
        token_getter: Callable[[P], str | None] | None = None,
    ) -> None:
        self._fetch_page = fetch_page
        self._items_getter = items_getter
        self._token_getter = token_getter or _default_token_getter
        self._token: str | None = None
        self._items: list[T] = []
        self._index = 0
        self._done = False

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> T:
        while True:
            if self._index < len(self._items):
                item = self._items[self._index]
                self._index += 1
                return item
            if self._done:
                raise StopIteration
            page = self._fetch_page(self._token)
            self._items = self._items_getter(page)
            self._index = 0
            self._token = self._token_getter(page)
            if not self._token:
                self._done = True
            if self._index >= len(self._items) and self._done:
                raise StopIteration
