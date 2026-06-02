# SPDX-License-Identifier: Apache-2.0
"""Configuration loading with 4-level precedence: defaults < file < env < CLI flags.

CLI-flag overrides are applied in M6 via the ``overrides`` dict of
:func:`resolve_profile`.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any, Literal

import platformdirs
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Profile(BaseModel):
    """Active connection profile."""

    base_url: HttpUrl
    base_path: str = "/portal"
    api_version: int = 2
    auth_method: Literal["service_account", "google_oauth2"] = "service_account"
    service_account_key: Path | None = None
    # Google OAuth2 access token; supplied per-session via env/flag, never persisted to
    # config.toml by the CLI (short-lived + sensitive).
    google_oauth2_token: str | None = None
    token_cache: Literal["file", "memory"] = "file"
    token_cache_dir: Path | None = None
    timeout_seconds: float = 30.0
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    audit_log: bool = False
    audit_log_file: Path | None = None
    audit_log_bodies: bool = False
    audit_log_raw: bool = False
    audit_log_max_bytes: int = 10_000_000
    audit_log_backups: int = 5


class Config(BaseModel):
    """Top-level config; maps profile names to :class:`Profile` objects."""

    current_profile: str = "default"
    profiles: dict[str, Profile] = {}


class _EnvSettings(BaseSettings):
    """Reads profile-level overrides from environment variables.

    ``timeout_seconds`` maps to ``PYNTERACTA_TIMEOUT`` (not ``…_TIMEOUT_SECONDS``)
    to match the documented env-var table; all other fields follow the
    ``PYNTERACTA_<FIELD_NAME_UPPER>`` pattern with ``env_prefix``.
    """

    model_config = SettingsConfigDict(env_prefix="PYNTERACTA_", env_ignore_empty=True)

    base_url: str | None = None
    base_path: str | None = None
    api_version: int | None = None
    auth_method: Literal["service_account", "google_oauth2"] | None = None
    service_account_key: Path | None = None
    google_oauth2_token: str | None = None
    token_cache: Literal["file", "memory"] | None = None
    token_cache_dir: Path | None = None
    # Field name "timeout" → env var PYNTERACTA_TIMEOUT (matches the documented table).
    timeout: float | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] | None = None
    audit_log: bool | None = None
    audit_log_file: Path | None = None
    audit_log_bodies: bool | None = None
    audit_log_raw: bool | None = None
    audit_log_max_bytes: int | None = None
    audit_log_backups: int | None = None

    def to_profile_overrides(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        raw = self.model_dump(exclude_none=True)
        for key, value in raw.items():
            out_key = "timeout_seconds" if key == "timeout" else key
            data[out_key] = value
        return data


def _xdg_config_dir() -> Path:
    """Return the pynteracta config directory using XDG conventions on Linux/macOS."""
    if sys.platform == "win32":
        return Path(platformdirs.user_config_dir("pynteracta"))
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg) if xdg else Path("~/.config").expanduser()
    return base / "pynteracta"


def _default_config_path() -> Path:
    return _xdg_config_dir() / "config.toml"


def load_config(config_file: Path | None = None) -> Config:
    """Load :class:`Config` from a TOML file.

    Falls back to an empty config (no profiles) if the file does not exist.
    """
    if config_file is None:
        env_file = os.environ.get("PYNTERACTA_CONFIG_FILE")
        path = Path(env_file) if env_file else _default_config_path()
    else:
        path = config_file

    if not path.exists():
        return Config()

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config.model_validate(raw)


def resolve_profile(
    profile_name: str | None = None,
    config_file: Path | None = None,
    *,
    overrides: dict[str, Any] | None = None,
) -> Profile:
    """Resolve the active :class:`Profile` with precedence: defaults < file < env < overrides.

    Args:
        profile_name: Profile to load; defaults to ``config.current_profile``.
        config_file: Path to ``config.toml``; None uses the platform default or
            ``PYNTERACTA_CONFIG_FILE``.
        overrides: Explicit field overrides (highest precedence; used by CLI flags in M6).

    Raises:
        KeyError: If ``profile_name`` is not found in the config and no ``base_url`` can
            be resolved from env or overrides.
        pydantic.ValidationError: If the merged data does not satisfy :class:`Profile`.
    """
    config = load_config(config_file)
    name = profile_name or config.current_profile

    profile_data: dict[str, Any] = {}
    if name in config.profiles:
        profile_data = config.profiles[name].model_dump(exclude_none=True)

    env = _EnvSettings()
    profile_data.update(env.to_profile_overrides())

    if overrides:
        profile_data.update({k: v for k, v in overrides.items() if v is not None})

    return Profile.model_validate(profile_data)
