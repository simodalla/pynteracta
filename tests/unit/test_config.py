# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path

import platformdirs
import pytest

from pynteracta.config import Config, _xdg_config_dir, load_config, resolve_profile

_MINIMAL_TOML = """\
[profiles.dev]
base_url = "https://interacta.example.it"
"""

_FULL_TOML = """\
current_profile = "dev"

[profiles.dev]
base_url        = "https://interacta.example.it"
base_path       = "/myportal"
api_version     = 3
timeout_seconds = 60.0
log_level       = "DEBUG"
"""

_DEFAULT_BASE_PATH = "/portal"
_DEFAULT_API_VERSION = 2
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_TOKEN_CACHE = "file"

_FULL_API_VERSION = 3
_FULL_TIMEOUT = 60.0
_FULL_TIMEOUT_ENV = 99.0
_FULL_TIMEOUT_OVERRIDE = 5.0


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path / "nonexistent.toml")
        assert isinstance(cfg, Config)
        assert cfg.profiles == {}
        assert cfg.current_profile == "default"

    def test_loads_profiles(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _MINIMAL_TOML))
        assert "dev" in cfg.profiles

    def test_current_profile_default(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _MINIMAL_TOML))
        assert cfg.current_profile == "default"

    def test_current_profile_explicit(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _FULL_TOML))
        assert cfg.current_profile == "dev"


class TestProfileDefaults:
    def test_defaults_applied(self, tmp_path: Path) -> None:
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert profile.base_path == _DEFAULT_BASE_PATH
        assert profile.api_version == _DEFAULT_API_VERSION
        assert profile.timeout_seconds == _DEFAULT_TIMEOUT
        assert profile.log_level == _DEFAULT_LOG_LEVEL
        assert profile.token_cache == _DEFAULT_TOKEN_CACHE
        assert profile.service_account_key is None
        assert profile.token_cache_dir is None

    def test_file_values_override_defaults(self, tmp_path: Path) -> None:
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.base_path == "/myportal"
        assert profile.api_version == _FULL_API_VERSION
        assert profile.timeout_seconds == _FULL_TIMEOUT
        assert profile.log_level == "DEBUG"


class TestEnvPrecedence:
    def test_env_base_url_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_URL", "https://override.example.it")
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert str(profile.base_url).rstrip("/") == "https://override.example.it"

    def test_env_base_path_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_PATH", "/env-path")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.base_path == "/env-path"

    def test_env_timeout_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_TIMEOUT", "99.0")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.timeout_seconds == _FULL_TIMEOUT_ENV

    def test_env_log_level_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_LOG_LEVEL", "WARNING")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.log_level == "WARNING"


class TestExplicitOverrides:
    def test_override_wins_over_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_PATH", "/env-path")
        profile = resolve_profile(
            "dev",
            _write(tmp_path, _MINIMAL_TOML),
            overrides={"base_path": "/cli-path"},
        )
        assert profile.base_path == "/cli-path"

    def test_override_wins_over_file(self, tmp_path: Path) -> None:
        profile = resolve_profile(
            "dev",
            _write(tmp_path, _FULL_TOML),
            overrides={"timeout_seconds": _FULL_TIMEOUT_OVERRIDE},
        )
        assert profile.timeout_seconds == _FULL_TIMEOUT_OVERRIDE


_AUDIT_MAX_BYTES_DEFAULT = 10_000_000
_AUDIT_BACKUPS_DEFAULT = 5
_AUDIT_MAX_BYTES_CUSTOM = 5_000_000
_AUDIT_BACKUPS_CUSTOM = 3


class TestAuditFields:
    def test_audit_defaults(self, tmp_path: Path) -> None:
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert profile.audit_log is False
        assert profile.audit_log_file is None
        assert profile.audit_log_bodies is False
        assert profile.audit_log_raw is False
        assert profile.audit_log_max_bytes == _AUDIT_MAX_BYTES_DEFAULT
        assert profile.audit_log_backups == _AUDIT_BACKUPS_DEFAULT

    def test_audit_fields_from_file(self, tmp_path: Path) -> None:
        toml = """\
[profiles.dev]
base_url = "https://interacta.example.it"
audit_log = true
audit_log_bodies = true
audit_log_max_bytes = 5000000
audit_log_backups = 3
"""
        profile = resolve_profile("dev", _write(tmp_path, toml))
        assert profile.audit_log is True
        assert profile.audit_log_bodies is True
        assert profile.audit_log_max_bytes == _AUDIT_MAX_BYTES_CUSTOM
        assert profile.audit_log_backups == _AUDIT_BACKUPS_CUSTOM

    def test_audit_log_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYNTERACTA_AUDIT_LOG", "true")
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert profile.audit_log is True

    def test_audit_log_bodies_env_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_AUDIT_LOG_BODIES", "true")
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert profile.audit_log_bodies is True

    def test_audit_override_wins_over_file(self, tmp_path: Path) -> None:
        profile = resolve_profile(
            "dev",
            _write(tmp_path, _MINIMAL_TOML),
            overrides={"audit_log": True, "audit_log_bodies": True},
        )
        assert profile.audit_log is True
        assert profile.audit_log_bodies is True


class TestXdgConfigDir:
    def test_default_returns_dot_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        result = _xdg_config_dir()
        assert result == Path.home() / ".config" / "pynteracta"

    def test_xdg_config_home_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setattr(sys, "platform", "linux")
        result = _xdg_config_dir()
        assert result == tmp_path / "pynteracta"

    def test_macos_uses_dot_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        result = _xdg_config_dir()
        assert result == Path.home() / ".config" / "pynteracta"

    def test_windows_uses_platformdirs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        result = _xdg_config_dir()
        assert result == Path(platformdirs.user_config_dir("pynteracta"))
