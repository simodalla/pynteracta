# SPDX-License-Identifier: Apache-2.0
"""Tests for PageIterator pagination helper."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pynteracta.exceptions import NotFoundError
from pynteracta.pagination import PageIterator


@dataclass
class _FakePage:
    items: list[int]
    next_page_token: str | None


class TestPageIterator:
    def test_yields_all_items_single_page(self) -> None:
        pages = [_FakePage(items=[1, 2, 3], next_page_token=None)]
        it = PageIterator(
            fetch_page=lambda _token: pages.pop(0),
            items_getter=lambda page: page.items,
            token_getter=lambda page: page.next_page_token,
        )
        assert list(it) == [1, 2, 3]

    def test_stops_on_empty_next_page_token(self) -> None:
        calls: list[str | None] = []

        def fetch(token: str | None) -> _FakePage:
            calls.append(token)
            if token is None:
                return _FakePage(items=[1], next_page_token="")
            return _FakePage(items=[2], next_page_token=None)

        it = PageIterator(
            fetch_page=fetch,
            items_getter=lambda page: page.items,
            token_getter=lambda page: page.next_page_token,
        )
        assert list(it) == [1]
        assert calls == [None]

    def test_fetches_next_page_when_exhausted(self) -> None:
        pages = {
            None: _FakePage(items=[1], next_page_token="tok-2"),
            "tok-2": _FakePage(items=[2], next_page_token=None),
        }

        def fetch(token: str | None) -> _FakePage:
            return pages[token]

        it = PageIterator(
            fetch_page=fetch,
            items_getter=lambda page: page.items,
            token_getter=lambda page: page.next_page_token,
        )
        assert list(it) == [1, 2]

    def test_propagates_fetch_error(self) -> None:
        def fetch(_token: str | None) -> _FakePage:
            raise NotFoundError("missing")

        it = PageIterator(
            fetch_page=fetch,
            items_getter=lambda page: page.items,
            token_getter=lambda page: page.next_page_token,
        )
        with pytest.raises(NotFoundError):
            list(it)
