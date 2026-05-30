# SPDX-License-Identifier: Apache-2.0
"""Resource API clients for the Interacta external v2 endpoints."""

from pynteracta.api.auth import AuthAPI
from pynteracta.api.posts import PostsAPI
from pynteracta.api.users import UsersAPI

__all__ = ["AuthAPI", "PostsAPI", "UsersAPI"]
