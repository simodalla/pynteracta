# SPDX-License-Identifier: Apache-2.0
"""Unit tests for --full and --fields CLI options across data-emitting commands."""

from __future__ import annotations

import json
import re

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli._common import EXIT_CONFIG

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _json_output(result: object) -> dict | list:
    """Parse all JSON objects/arrays from CLI output, returning list or dict."""
    output = getattr(result, "output", "")
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    # Try to find the outermost JSON array first (print_output wraps in array for lists)
    bracket = clean.find("[")
    brace = clean.find("{")
    if bracket >= 0 and (brace < 0 or bracket < brace):
        # Array comes first — parse from there
        try:
            return json.loads(clean[bracket:])  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass
    # Multiple JSON objects on separate top-level lines (Rich pretty-prints each)
    # Collect all objects by scanning for top-level { ... }
    objects = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(clean):
        idx = clean.find("{", pos)
        if idx < 0:
            break
        try:
            obj, end = decoder.raw_decode(clean, idx)
            objects.append(obj)
            pos = end
        except json.JSONDecodeError:
            pos = idx + 1
    if len(objects) == 1:
        return objects[0]
    if objects:
        return objects
    raise ValueError(f"No JSON found in output: {output!r}")


# ---------------------------------------------------------------------------
# --full + --fields mutual exclusion
# ---------------------------------------------------------------------------


class TestMutualExclusion:
    @respx.mock
    def test_full_and_fields_together_exit_config(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--full", "--fields", "id"], env=BASE_ENV
        )
        assert result.exit_code == EXIT_CONFIG
        assert "--full and --fields are mutually exclusive" in result.output

    @respx.mock
    def test_full_and_fields_together_posts_exit_config(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--full", "--fields", "id"],
            env=BASE_ENV,
        )
        assert result.exit_code == EXIT_CONFIG


# ---------------------------------------------------------------------------
# Unknown field → EXIT_CONFIG
# ---------------------------------------------------------------------------


class TestUnknownField:
    @respx.mock
    def test_unknown_field_exits_config(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--fields", "nonExistentField"], env=BASE_ENV
        )
        assert result.exit_code == EXIT_CONFIG
        assert "Unknown field" in result.output
        assert "nonExistentField" in result.output

    @respx.mock
    def test_unknown_field_lists_valid_keys(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--fields", "bogusField"], env=BASE_ENV
        )
        assert result.exit_code == EXIT_CONFIG
        assert "Valid top-level fields:" in result.output


# ---------------------------------------------------------------------------
# users list — list command + --full
# ---------------------------------------------------------------------------


class TestUsersListFull:
    @respx.mock
    def test_full_json_output_has_camel_keys(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--output", "json", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        # camelCase keys from DTO
        assert "firstName" in first or "id" in first
        # snake_case curated keys should NOT be present
        assert "first_name" not in first

    @respx.mock
    def test_full_table_output_vertical_layout(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(app, ["users", "list", "--full"], env=BASE_ENV)
        assert result.exit_code == 0
        # Vertical layout: should have "Field" and "Value" column headers
        assert "Field" in result.output or "firstName" in result.output
        assert result.output == snapshot

    @respx.mock
    def test_fields_json_output_selected_keys_only(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--output", "json", "--fields", "id,firstName"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, list)
        first = data[0]
        assert set(first.keys()) == {"id", "firstName"}

    @respx.mock
    def test_fields_table_output_narrow_columns(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app, ["users", "list", "--fields", "id,firstName"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "id" in result.output
        assert "firstName" in result.output
        assert result.output == snapshot

    @respx.mock
    def test_no_flags_curated_output_unchanged(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(app, ["users", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        # Curated output uses snake_case
        assert "first_name" in result.output or "email" in result.output
        assert result.output == snapshot


# ---------------------------------------------------------------------------
# users profile — detail command + --full
# ---------------------------------------------------------------------------


class TestUsersProfileFull:
    @respx.mock
    def test_full_json_camel_keys(self, runner: CliRunner) -> None:
        mock_json("GET", "core/user-profile/info", load_payload("user_profile_info_response.json"))
        result = runner.invoke(
            app, ["users", "profile", "--output", "json", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, dict)
        # Full dump from .raw should include camelCase API keys
        assert any(k[0].islower() for k in data)

    @respx.mock
    def test_fields_json_dotted_path_not_applicable(self, runner: CliRunner) -> None:
        mock_json("GET", "core/user-profile/info", load_payload("user_profile_info_response.json"))
        result = runner.invoke(
            app,
            ["users", "profile", "--output", "json", "--fields", "id"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert "id" in data

    @respx.mock
    def test_no_flags_curated_unchanged(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", "core/user-profile/info", load_payload("user_profile_info_response.json"))
        result = runner.invoke(app, ["users", "profile"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


# ---------------------------------------------------------------------------
# posts get — detail command + --full / --fields
# ---------------------------------------------------------------------------


class TestPostsGetFull:
    @respx.mock
    def test_full_json_nulls_omitted(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app, ["posts", "get", "21269", "--output", "json", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, dict)
        # No None/null values (exclude_none=True)
        assert all(v is not None for v in data.values() if not isinstance(v, (dict, list)))

    @respx.mock
    def test_fields_subset(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--output", "json", "--fields", "id,title"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert set(data.keys()) == {"id", "title"}

    @respx.mock
    def test_no_flags_curated_unchanged(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["posts", "get", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


# ---------------------------------------------------------------------------
# posts list — list command + --full
# ---------------------------------------------------------------------------


class TestPostsListFull:
    @respx.mock
    def test_full_json_list(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--output", "json", "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]

    @respx.mock
    def test_fields_selected(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--output", "json", "--fields", "id,title"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _json_output(result)
        if data:
            assert set(data[0].keys()) == {"id", "title"}


# ---------------------------------------------------------------------------
# communities list — --full / --fields
# ---------------------------------------------------------------------------


class TestCommunitiesListFull:
    @respx.mock
    def test_full_json(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities",
            load_payload("communities_list.json"),
        )
        result = runner.invoke(
            app, ["communities", "list", "--output", "json", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, list)

    @respx.mock
    def test_fields_json(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities",
            load_payload("communities_list.json"),
        )
        result = runner.invoke(
            app, ["communities", "list", "--output", "json", "--fields", "id"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        if data:
            assert list(data[0].keys()) == ["id"]

    @respx.mock
    def test_no_flags_curated_unchanged(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/settings/communities",
            load_payload("communities_list.json"),
        )
        result = runner.invoke(app, ["communities", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


# ---------------------------------------------------------------------------
# catalogs list — --full / --fields
# ---------------------------------------------------------------------------


class TestCatalogsListFull:
    @respx.mock
    def test_full_json(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs",
            load_payload("catalogs.json"),
        )
        result = runner.invoke(
            app, ["catalogs", "list", "--output", "json", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, list)

    @respx.mock
    def test_fields_json(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs",
            load_payload("catalogs.json"),
        )
        result = runner.invoke(
            app, ["catalogs", "list", "--output", "json", "--fields", "id,name"], env=BASE_ENV
        )
        assert result.exit_code == 0
        data = _json_output(result)
        if data:
            assert set(data[0].keys()) == {"id", "name"}

    @respx.mock
    def test_no_flags_curated_unchanged(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs",
            load_payload("catalogs.json"),
        )
        result = runner.invoke(app, ["catalogs", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


# ---------------------------------------------------------------------------
# Per-command placement: options must come AFTER the command
# ---------------------------------------------------------------------------


class TestOptionPlacement:
    @respx.mock
    def test_full_after_command_accepted(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(app, ["users", "list", "--full"], env=BASE_ENV)
        # Should succeed (exit 0), not be treated as unknown global option
        assert result.exit_code == 0

    def test_full_before_command_not_accepted(self, runner: CliRunner) -> None:
        # --full before subcommand should NOT be accepted by global callback
        result = runner.invoke(app, ["--full", "users", "list"], env=BASE_ENV)
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Bug regression: --fields must not crash on null-valued fields (Bug 1)
# ---------------------------------------------------------------------------


class TestFieldsNullValues:
    """Regression tests: requesting a schema field that is null must NOT raise EXIT_CONFIG."""

    @respx.mock
    def test_fields_null_field_single_object(self, runner: CliRunner) -> None:
        """posts get --fields currentWorkflowState on a post where that field is null."""
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--output", "json", "--fields", "id,currentWorkflowState"],
            env=BASE_ENV,
        )
        # Must succeed, not EXIT_CONFIG
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert "id" in data
        # The null field is present in the output (value is null / None)
        assert "currentWorkflowState" in data
        assert data["currentWorkflowState"] is None

    @respx.mock
    def test_fields_null_field_list_command(self, runner: CliRunner) -> None:
        """posts list --fields descriptionDelta on items where that field is null."""
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--output",
                "json",
                "--fields",
                "id,descriptionDelta",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "descriptionDelta" in data[0]
            # The field is null in the fixture
            assert data[0]["descriptionDelta"] is None

    @respx.mock
    def test_genuinely_unknown_field_still_exits_config(self, runner: CliRunner) -> None:
        """A field name that does not exist in the schema → EXIT_CONFIG (no regression)."""
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--fields", "totallyBogusField"],
            env=BASE_ENV,
        )
        assert result.exit_code == EXIT_CONFIG
        assert "Unknown field" in result.output
        assert "totallyBogusField" in result.output
        assert "Valid top-level fields:" in result.output

    @respx.mock
    def test_full_still_omits_nulls(self, runner: CliRunner) -> None:
        """--full must continue to omit null values (exclude_none=True, no regression)."""
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--output", "json", "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _json_output(result)
        assert isinstance(data, dict)
        # currentWorkflowState is null in fixture → must be absent under --full
        assert "currentWorkflowState" not in data


# ---------------------------------------------------------------------------
# Bug regression: --web-url honored with --full / --fields on list commands (Bug 2)
# ---------------------------------------------------------------------------


class TestWebUrlWithFullAndFields:
    """Regression tests: --web-url must be preserved when combined with --full / --fields."""

    @respx.mock
    def test_posts_list_web_url_with_full(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--output",
                "json",
                "--full",
                "--web-url",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert isinstance(data, list)
        if data:
            assert "web_url" in data[0]

    @respx.mock
    def test_posts_list_web_url_with_fields(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--output",
                "json",
                "--fields",
                "id,web_url",
                "--web-url",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert isinstance(data, list)
        if data:
            assert "web_url" in data[0]
            assert "id" in data[0]

    @respx.mock
    def test_users_list_web_url_with_full(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "admin/data/users",
            load_payload("list_system_users_response.json"),
        )
        result = runner.invoke(
            app,
            ["users", "list", "--output", "json", "--full", "--web-url"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert isinstance(data, list)
        if data:
            assert "web_url" in data[0]

    @respx.mock
    def test_posts_get_web_url_with_full(self, runner: CliRunner) -> None:
        """Single-object command: --web-url --full must still include web_url (no regression)."""
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--output", "json", "--full", "--web-url"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = _json_output(result)
        assert isinstance(data, dict)
        assert "web_url" in data
