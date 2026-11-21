# SPDX-License-Identifier: Apache-2.0
"""Configuration loading with 4-level precedence: defaults < file < env < CLI flags.

CLI-flag overrides are applied in M6 via the ``overrides`` dict of
:func:`resolve_profile`.
"""

from __future__ import annotations

import os
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import platformdirs
import tomlkit
from pydantic import BaseModel, HttpUrl, field_validator
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
    # Id del client OAuth "Desktop" dell'ente per il login Google integrato (spec 10); non è un
    # segreto. Il client secret sta solo nel portachiavi di sistema.
    google_client_id: str | None = None
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

    @field_validator("service_account_key", "token_cache_dir", "audit_log_file", mode="before")
    @classmethod
    def expand_user_paths(cls, v: Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v).expanduser()


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
    google_client_id: str | None = None
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


def config_file_path(config_file: Path | None = None) -> Path:
    """Il percorso di ``config.toml``: argomento, poi ``PYNTERACTA_CONFIG_FILE``, poi il
    predefinito della piattaforma."""
    if config_file is not None:
        return config_file
    env_file = os.environ.get("PYNTERACTA_CONFIG_FILE")
    return Path(env_file) if env_file else _default_config_path()


def write_profile_fields(
    config_path: Path,
    name: str,
    *,
    connection: Profile,
    fields: Mapping[str, str],
) -> None:
    """Scrive in ``config.toml`` i campi ``fields`` del profilo ``name``, con ``tomlkit``.

    Crea il file e il profilo se mancano e conserva commenti e formattazione. Un profilo senza
    ``base_url`` renderebbe il file invalido per ogni comando: se manca, si scrive quello di
    ``connection``, più ``base_path`` e ``api_version`` se diversi dai predefiniti. Un
    ``base_url`` già presente non si tocca.
    """
    if config_path.exists():
        doc = tomlkit.loads(config_path.read_text(encoding="utf-8"))
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        doc = tomlkit.document()
    profiles_table: Any = doc.get("profiles")
    if profiles_table is None:
        profiles_table = tomlkit.table()
        doc.add("profiles", profiles_table)
    if name not in profiles_table:
        profiles_table.add(name, tomlkit.table())
    table = profiles_table[name]
    if "base_url" not in table:
        table["base_url"] = str(connection.base_url).rstrip("/")
        for field in ("base_path", "api_version"):
            value = getattr(connection, field)
            if value != Profile.model_fields[field].default:
                table[field] = value
    for key, value in fields.items():
        table[key] = value
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def load_config(config_file: Path | None = None) -> Config:
    """Load :class:`Config` from a TOML file.

    Falls back to an empty config (no profiles) if the file does not exist.
    """
    path = config_file_path(config_file)

    if not path.exists():
        return Config()

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config.model_validate(raw)


def resolve_profile_name(profile_name: str | None, config_file: Path | None = None) -> str:
    """Il nome del profilo su cui lavorare: quello dato, altrimenti ``current_profile``.

    Senza ``config.toml`` il profilo corrente è ``default``. Lo usano i login e il client che
    risolve da sé il profilo, così sessione e cache finiscono dove i comandi le cercano
    (RF-016b).
    """
    return profile_name or load_config(config_file).current_profile


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
