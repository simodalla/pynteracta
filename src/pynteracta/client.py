# SPDX-License-Identifier: Apache-2.0
"""Top-level client façade aggregating resource APIs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import platformdirs

from pynteracta.api.auth import AuthAPI
from pynteracta.api.catalogs import CatalogsAPI
from pynteracta.api.communities import CommunitiesAPI
from pynteracta.api.posts import PostsAPI
from pynteracta.api.users import UsersAPI
from pynteracta.auth import (
    FileTokenCache,
    GoogleOAuth2Credentials,
    GoogleOAuth2TokenManager,
    MemoryTokenCache,
    ServiceAccountKey,
    TokenCache,
    TokenManager,
    TokenProvider,
    load_service_account_key,
)
from pynteracta.config import Profile, resolve_profile
from pynteracta.exceptions import AuthenticationError
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
    """Façade aggregating auth, users, posts, communities, and catalogs resource clients."""

    def __init__(  # noqa: PLR0913
        self,
        base_url: str | None = None,
        *,
        base_path: str = "/portal",
        api_version: int = 2,
        credentials: ServiceAccountKey | None = None,
        google_token: str | None = None,
        google_token_provider: Callable[[], str] | None = None,
        profile: Profile | None = None,
        hooks: ClientHooks | None = None,
        timeout: float | None = None,
        auth_scheme: str | None = None,
        config_file: Path | None = None,
        profile_name: str | None = None,
        audit: bool = False,
        audit_bodies: bool = False,
    ) -> None:
        if profile is None and base_url is None:
            profile = resolve_profile(profile_name=profile_name, config_file=config_file)

        auth_method = "service_account"
        if profile is not None:
            base_url = str(profile.base_url)
            base_path = profile.base_path
            api_version = profile.api_version
            timeout = profile.timeout_seconds if timeout is None else timeout
            auth_method = profile.auth_method
            if (
                credentials is None
                and auth_method == "service_account"
                and profile.service_account_key is not None
            ):
                credentials = load_service_account_key(profile.service_account_key)
            if google_token is None:
                google_token = profile.google_oauth2_token
            audit = audit or profile.audit_log
            audit_bodies = audit_bodies or profile.audit_log_bodies
        elif base_url is None:
            msg = "Either base_url or profile must be provided"
            raise ValueError(msg)

        timeout_seconds = timeout if timeout is not None else 30.0
        api_base = build_api_base(base_url, base_path, api_version)
        self.web_urls = WebUrls(base_url, base_path)

        # The Google OAuth2 exchange endpoint lives at {base_url}/{base_path}/api/core/...
        # (no /external/v{n}/ prefix), so it needs a separate transport base.
        google_auth_base = f"{base_url.rstrip('/')}/{base_path.strip('/')}/api"

        auth_transport = HttpTransport(
            base_url=api_base,
            hooks=hooks,
            timeout=timeout_seconds,
            audit=audit,
            audit_bodies=audit_bodies,
        )
        google_exchange_transport = HttpTransport(
            base_url=google_auth_base,
            hooks=hooks,
            timeout=timeout_seconds,
            audit=audit,
            audit_bodies=audit_bodies,
        )
        token_manager = self._build_token_manager(
            auth_method=auth_method,
            credentials=credentials,
            google_token=google_token,
            google_token_provider=google_token_provider,
            profile=profile,
            profile_name=profile_name,
            sa_transport=auth_transport,
            google_transport=google_exchange_transport,
        )
        if token_manager is not None:
            api_transport = HttpTransport(
                base_url=api_base,
                token_provider=token_manager.get_token,
                token_invalidator=token_manager.invalidate,
                hooks=hooks,
                timeout=timeout_seconds,
                auth_scheme=auth_scheme,
                audit=audit,
                audit_bodies=audit_bodies,
            )
        else:
            api_transport = auth_transport

        self._auth_transport = auth_transport
        self._google_exchange_transport = google_exchange_transport
        self._api_transport = api_transport
        self._token_manager = token_manager

        self.auth = AuthAPI(
            api_transport,
            unauthenticated_transport=auth_transport,
        )
        self.users = UsersAPI(api_transport)
        self.posts = PostsAPI(api_transport)
        self.communities = CommunitiesAPI(api_transport)
        self.catalogs = CatalogsAPI(api_transport)

    def _build_token_manager(  # noqa: PLR0913
        self,
        *,
        auth_method: str,
        credentials: ServiceAccountKey | None,
        google_token: str | None,
        google_token_provider: Callable[[], str] | None,
        profile: Profile | None,
        profile_name: str | None,
        sa_transport: HttpTransport,
        google_transport: HttpTransport,
    ) -> TokenProvider | None:
        """Select and build the token manager for the active auth method.

        Explicit ``credentials`` (service-account) take priority; otherwise a Google token /
        provider (explicit kwargs or ``profile.google_oauth2_token``) selects the Google flow.
        Returns ``None`` when no credentials are available (unauthenticated client).
        """
        cache = _build_token_cache(profile) if profile is not None else MemoryTokenCache()

        if credentials is not None:
            return TokenManager(key=credentials, cache=cache, transport=sa_transport)

        if google_token is not None or google_token_provider is not None:
            google_creds = GoogleOAuth2Credentials(
                token=google_token,
                token_provider=google_token_provider,
            )
            return GoogleOAuth2TokenManager(
                google_creds,
                cache,
                google_transport,
                cache_key=profile_name or "default",
            )

        if auth_method == "google_oauth2":
            raise AuthenticationError(
                "auth_method is 'google_oauth2' but no Google access token was provided "
                "(set PYNTERACTA_GOOGLE_OAUTH2_TOKEN, pass --google-token, or supply "
                "google_token / google_token_provider)"
            )

        return None

    def close(self) -> None:
        """Close underlying HTTP transports."""
        self._api_transport.close()
        if self._api_transport is not self._auth_transport:
            self._auth_transport.close()
        self._google_exchange_transport.close()

    def __enter__(self) -> InteractaClient:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
