# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'config' command group."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pynteracta.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestConfigSet:
    def test_set_creates_profile_key(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "config",
                "set",
                "base_url",
                "https://new.example.com",
            ],
        )
        assert result.exit_code == 0
        content = config_file.read_text(encoding="utf-8")
        assert "https://new.example.com" in content

    def test_set_preserves_existing_comments(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '# keep this comment\ncurrent_profile = "default"\n\n[profiles.default]\nbase_url = "https://old.example.com"\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "config",
                "set",
                "base_url",
                "https://new.example.com",
            ],
        )
        assert result.exit_code == 0
        updated = config_file.read_text(encoding="utf-8")
        assert "# keep this comment" in updated
        assert "https://new.example.com" in updated


class TestConfigGet:
    def test_get_existing_key(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[profiles.default]\nbase_url = "https://api.example.com"\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "config", "get", "base_url"],
        )
        assert result.exit_code == 0
        assert "https://api.example.com" in result.output

    def test_get_missing_key_exits_1(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[profiles.default]\nbase_url = "https://api.example.com"\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "config", "get", "nonexistent_key"],
        )
        assert result.exit_code == 1


class TestConfigList:
    def test_list_shows_all_profiles(
        self, runner: CliRunner, tmp_path: Path, snapshot: object
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'current_profile = "dev"\n\n'
            "[profiles.dev]\n"
            'base_url = "https://dev.example.com"\n\n'
            "[profiles.prod]\n"
            'base_url = "https://prod.example.com"\n',
            encoding="utf-8",
        )
        result = runner.invoke(app, ["--config-file", str(config_file), "config", "list"])
        assert result.exit_code == 0
        assert "dev" in result.output
        assert "prod" in result.output

    def test_list_no_config_exits_0(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "nonexistent_config.toml"
        result = runner.invoke(app, ["--config-file", str(config_file), "config", "list"])
        assert result.exit_code == 0


class TestConfigUseProfile:
    def test_use_profile_updates_current(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'current_profile = "dev"\n\n[profiles.dev]\nbase_url = "https://dev.example.com"\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "config", "use-profile", "prod"],
        )
        assert result.exit_code == 0
        content = config_file.read_text(encoding="utf-8")
        assert 'current_profile = "prod"' in content
