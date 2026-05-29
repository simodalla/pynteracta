# SPDX-License-Identifier: Apache-2.0
import pytest

from pynteracta.urls import WebUrls, build_api_base

_CANONICAL = "https://host/portal/api/external/v2"


@pytest.mark.parametrize(
    ("base_url", "base_path", "version"),
    [
        ("https://host", "/portal", 2),
        ("https://host/", "portal", 2),
        ("host", "/portal/", 2),
        ("https://host//", "//portal//", 2),
    ],
)
def test_build_api_base_normalization(base_url: str, base_path: str, version: int) -> None:
    assert build_api_base(base_url, base_path, version) == _CANONICAL


def test_build_api_base_no_base_path() -> None:
    assert build_api_base("https://host", "", 2) == "https://host/api/external/v2"


def test_build_api_base_version() -> None:
    result = build_api_base("https://host", "/portal", 3)
    assert result == "https://host/portal/api/external/v3"


class TestWebUrls:
    _BASE = "https://interacta.example.it"
    _PATH = "/portal"

    def setup_method(self) -> None:
        self.wu = WebUrls(self._BASE, self._PATH)

    def test_post(self) -> None:
        assert self.wu.post(21269) == "https://interacta.example.it/portal/post/21269"

    def test_user_trailing_slash(self) -> None:
        assert self.wu.user(5225) == "https://interacta.example.it/portal/admin/user/5225/"

    def test_community(self) -> None:
        assert self.wu.community(79) == "https://interacta.example.it/portal/community/79"

    def test_default_base_path(self) -> None:
        wu = WebUrls("https://interacta.example.it")
        assert wu.post(1) == "https://interacta.example.it/portal/post/1"
