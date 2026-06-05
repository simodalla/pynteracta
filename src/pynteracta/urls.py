# SPDX-License-Identifier: Apache-2.0
"""URL normalization and construction helpers."""

from __future__ import annotations


def _normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if "://" not in base_url:
        base_url = "https://" + base_url
    return base_url.rstrip("/")


def _normalize_base_path(base_path: str) -> str:
    stripped = base_path.strip().strip("/")
    if not stripped:
        return ""
    return "/" + stripped


def build_api_base(base_url: str, base_path: str, api_version: int) -> str:
    """Return the canonical API base URL.

    All four of these inputs produce ``https://host/portal/api/external/v2``::

        ("https://host",   "/portal",   2)
        ("https://host/",  "portal",    2)
        ("host",           "/portal/",  2)
        ("https://host//", "//portal//", 2)
    """
    url = _normalize_base_url(base_url)
    path = _normalize_base_path(base_path)
    return f"{url}{path}/api/external/v{api_version}"


class WebUrls:
    """Build web-browser URLs for Interacta resources."""

    def __init__(self, base_url: str, base_path: str = "/portal") -> None:
        self._prefix = _normalize_base_url(base_url) + _normalize_base_path(base_path)

    def post(self, post_id: int) -> str:
        return f"{self._prefix}/post/{post_id}"

    def user(self, user_id: int) -> str:
        return f"{self._prefix}/admin/user/{user_id}/"

    def community(self, community_id: int) -> str:
        return f"{self._prefix}/community/{community_id}"

    def group(self, group_id: int) -> str:
        return f"{self._prefix}/admin/group/{group_id}"
