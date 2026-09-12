# SPDX-License-Identifier: Apache-2.0
"""Tests for audit logging helpers in logging.py."""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path

import pytest

from pynteracta.logging import (
    _AUDIT_LOGGER_NAME,
    build_audit_file_handler,
    redact_body,
    setup_default_logging,
)

_FAKE_JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
_REDACTED = "***REDACTED***"


class TestBuildAuditFileHandler:
    def test_returns_rotating_handler(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        handler = build_audit_file_handler(log_file)
        assert isinstance(handler, logging.handlers.RotatingFileHandler)
        handler.close()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        log_file = tmp_path / "sub" / "dir" / "audit.log"
        handler = build_audit_file_handler(log_file)
        assert log_file.parent.exists()
        handler.close()

    def test_writes_json_lines(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        handler = build_audit_file_handler(log_file, max_bytes=0, backup_count=0)

        audit_logger = logging.getLogger("pynteracta.audit.test_writes")
        audit_logger.setLevel(logging.DEBUG)
        audit_logger.propagate = False
        audit_logger.addHandler(handler)
        audit_logger.info("test event", extra={"_extra": "data"})
        handler.flush()
        handler.close()

        lines = [line for line in log_file.read_text().splitlines() if line.strip()]
        assert len(lines) >= 1
        parsed = json.loads(lines[0])
        assert "event" in parsed or "message" in parsed

    def test_respects_max_bytes(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        # Very small max triggers rotation
        handler = build_audit_file_handler(log_file, max_bytes=1, backup_count=2)
        assert handler.maxBytes == 1
        assert handler.backupCount == 2  # noqa: PLR2004
        handler.close()

    def test_redaction_applied_to_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        handler = build_audit_file_handler(log_file)

        audit_logger = logging.getLogger("pynteracta.audit.test_redaction_file")
        audit_logger.setLevel(logging.DEBUG)
        audit_logger.propagate = False
        audit_logger.addHandler(handler)
        # Log a record with a JWT in the message
        audit_logger.info(_FAKE_JWT)
        handler.flush()
        handler.close()

        content = log_file.read_text()
        assert _FAKE_JWT not in content
        assert _REDACTED in content


class TestSetupDefaultLoggingAudit:
    def test_audit_false_no_audit_logger_handlers(self) -> None:
        # Remove any leftover handlers from previous tests
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        setup_default_logging(audit=False)
        assert len(audit_logger.handlers) == 0

    def test_audit_true_adds_console_handler(self) -> None:
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        setup_default_logging(audit=True)
        assert len(audit_logger.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in audit_logger.handlers)
        audit_logger.handlers.clear()

    def test_audit_file_adds_rotating_handler(self, tmp_path: Path) -> None:
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        log_file = tmp_path / "audit.log"
        setup_default_logging(audit=True, audit_file=log_file)
        handler_types = [type(h) for h in audit_logger.handlers]
        assert logging.handlers.RotatingFileHandler in handler_types
        for h in audit_logger.handlers:
            h.close()
        audit_logger.handlers.clear()

    def test_audit_file_implies_audit_enabled(self, tmp_path: Path) -> None:
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        log_file = tmp_path / "audit.log"
        setup_default_logging(audit=False, audit_file=log_file)
        assert len(audit_logger.handlers) >= 1
        for h in audit_logger.handlers:
            h.close()
        audit_logger.handlers.clear()

    def test_audit_raw_emits_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import pynteracta.logging as plog  # noqa: PLC0415

        plog._AUDIT_RAW_WARNED = False  # reset the global flag

        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        with caplog.at_level(logging.WARNING, logger="pynteracta"):
            setup_default_logging(audit=True, audit_raw=True)

        assert any("audit.redaction_disabled" in r.message for r in caplog.records)
        audit_logger.handlers.clear()
        plog._AUDIT_RAW_WARNED = False  # reset for other tests

    def test_audit_does_not_propagate(self) -> None:
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.handlers.clear()

        setup_default_logging(audit=True)
        assert not audit_logger.propagate
        audit_logger.handlers.clear()


class TestSensitiveKeyCoverage:
    """Fix 1b (v0.9.3): the key regex must cover the auth payloads, not just ``token``."""

    @pytest.mark.parametrize(
        "key",
        [
            "accessToken",
            "access_token",
            "assertion",
            "jwt",
            "googleOAuth2Token",
            "password",
            "clientSecret",
            "privateKey",
        ],
    )
    def test_sensitive_keys_are_redacted(self, key: str) -> None:
        assert redact_body({key: _FAKE_JWT}) == {key: _REDACTED}

    @pytest.mark.parametrize("key", ["id", "title", "description", "email", "communityId"])
    def test_ordinary_keys_are_untouched(self, key: str) -> None:
        assert redact_body({key: "plain value"}) == {key: "plain value"}

    def test_google_opaque_token_is_redacted_by_key(self) -> None:
        """``ya29.`` values are not JWT-shaped, so only the key match can catch them."""
        body = {"googleOAuth2Token": "ya29.a0ARrdaM-opaque-value"}
        assert redact_body(body) == {"googleOAuth2Token": _REDACTED}

    def test_nested_payload_is_redacted(self) -> None:
        body = {"data": {"accessToken": _FAKE_JWT, "userId": 7}}
        assert redact_body(body) == {"data": {"accessToken": _REDACTED, "userId": 7}}
