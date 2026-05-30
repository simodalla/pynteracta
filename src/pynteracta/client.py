# SPDX-License-Identifier: Apache-2.0
"""Top-level client façade aggregating resource APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import platformdirs

from pynteracta.api.auth import AuthAPI
from pynteracta.api.posts import PostsAPI
from pynteracta.api.users import UsersAPI
from pynteracta.auth import (
    FileTokenCache,
    MemoryTokenCache,
    ServiceAccountKey,
    TokenCache,
    TokenManager,
    load_service_account_key,
)
from pynteracta.config import Profile, resolve_profile
from pynteracta.hooks import ClientHooks
from pynteracta.transport import HttpTransport
from pynteracta.urls import WebUrls, build_api_base


def _default_token_cache_dir() -> Path:
    return Path(platformdirs.user_cache_dir("pynteracta")) / "tokens"


def _build_token_cache(profile: Profile) -> TokenCache:
    if profile.token_cache == "memory":
        return MemoryTokenCache()
    cache_dir = profile.token_cache_dir or _default_token_cache_dir()
    return FileTokenCache(cache_dir)


class InteractaClient:
    """Façade aggregating auth, users, posts resource clients and web URL helpers."""

    def __init__(  # noqa: PLR0913
        self,
        base_url: str | None = None,
        *,
        base_path: str = "/portal",
        api_version: int = 2,
        credentials: ServiceAccountKey | None = None,
        profile: Profile | None = None,
        hooks: ClientHooks | None = None,
        timeout: float | None = None,
        auth_scheme: str | None = None,
        config_file: Path | None = None,
        profile_name: str | None = None,
    ) -> None:
        if profile is None and base_url is None:
            profile = resolve_profile(profile_name=profile_name, config_file=config_file)

        if profile is not None:
            base_url = str(profile.base_url)
            base_path = profile.base_path
            api_version = profile.api_version
            timeout = profile.timeout_seconds if timeout is None else timeout
            if credentials is None and profile.service_account_key is not None:
                credentials = load_service_account_key(profile.service_account_key)
        elif base_url is None:
            msg = "Either base_url or profile must be provided"
            raise ValueError(msg)

        timeout_seconds = timeout if timeout is not None else 30.0
        api_base = build_api_base(base_url, base_path, api_version)
        self.web_urls = WebUrls(base_url, base_path)

        auth_transport = HttpTransport(base_url=api_base, hooks=hooks, timeout=timeout_seconds)
        token_manager: TokenManager | None = None
        if credentials is not None:
            cache = _build_token_cache(profile) if profile is not None else MemoryTokenCache()
            token_manager = TokenManager(
                key=credentials,
                cache=cache,
                transport=auth_transport,
            )
            api_transport = HttpTransport(
                base_url=api_base,
                token_provider=token_manager.get_token,
                token_invalidator=token_manager.invalidate,
                hooks=hooks,
                timeout=timeout_seconds,
                auth_scheme=auth_scheme,
            )
        else:
            api_transport = auth_transport

        self._auth_transport = auth_transport
        self._api_transport = api_transport
        self._token_manager = token_manager

        self.auth = AuthAPI(
            api_transport,
            unauthenticated_transport=auth_transport,
        )
        self.users = UsersAPI(api_transport)
        self.posts = PostsAPI(api_transport)

    def close(self) -> None:
        """Close underlying HTTP transports."""
        self._api_transport.close()
        if self._api_transport is not self._auth_transport:
            self._auth_transport.close()

    def __enter__(self) -> InteractaClient:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
