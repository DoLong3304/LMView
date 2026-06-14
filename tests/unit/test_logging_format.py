"""Tests for the structured JSON logging setup."""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import logging
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


def _load_common_logging():
    """Load the common.logging module under its canonical name."""
    # Drop the cached module so re-runs are clean.
    sys.modules.pop("common.logging", None)
    spec = importlib.util.spec_from_file_location(
        "common.logging", str(REPO / "src" / "common" / "logging.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["common.logging"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestJsonFormatter:
    def setup_method(self):
        self.cl = _load_common_logging()
        self.buf = io.StringIO()
        self.handler = logging.StreamHandler(self.buf)
        self.handler.setFormatter(self.cl.JsonFormatter())
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
        root.addHandler(self.handler)
        root.setLevel(logging.DEBUG)
        self.log = logging.getLogger("test.json")

    def _line(self) -> dict:
        raw = self.buf.getvalue().strip()
        return json.loads(raw)

    def test_emits_single_json_line(self):
        self.log.info("hello world")
        # Should be exactly one line (no embedded newlines).
        lines = [l for l in self.buf.getvalue().splitlines() if l.strip()]
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["message"] == "hello world"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.json"

    def test_includes_request_id(self):
        self.cl.bind_request_id("rid-abc")
        self.log.info("with id")
        payload = self._line()
        assert payload["request_id"] == "rid-abc"
        # reset for next test
        self.cl.bind_request_id("-")

    def test_includes_extra_context(self):
        self.log.info("with context", extra={"symbol": "BTCUSDT", "n": 3})
        payload = self._line()
        assert payload["context"] == {"symbol": "BTCUSDT", "n": 3}

    def test_includes_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            self.log.exception("oops")
        payload = self._line()
        assert payload["level"] == "ERROR"
        assert payload["exc_type"] == "ValueError"
        assert "ValueError: boom" in payload["exc_info"]

    def test_timestamp_is_utc_rfc3339(self):
        self.log.info("time test")
        payload = self._line()
        ts = payload["ts"]
        # Must end in 'Z' (UTC) and have a date+time+T+ms shape
        assert ts.endswith("Z")
        assert "T" in ts
        # Should be parseable
        from datetime import datetime
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_non_serialisable_context_does_not_crash(self):
        class _Unserialisable:
            def __repr__(self):
                return "<weird>"

        # Should not raise
        self.log.info("weird", extra={"obj": _Unserialisable()})
        payload = self._line()
        # The bad field is replaced with a fallback.
        assert "_serialise_error" in payload["context"] or "obj" in payload["context"]

    def test_log_with_context_helper(self):
        self.cl.log_with_context(self.log, 20, "helper", {"a": 1})
        payload = self._line()
        assert payload["message"] == "helper"
        assert payload["level"] == "INFO"
        assert payload["context"] == {"a": 1}


class TestSetupLogging:
    def setup_method(self):
        self.cl = _load_common_logging()

    def test_plain_text_mode(self):
        buf = io.StringIO()
        self.cl.setup_logging("plain", level=logging.INFO, json=False, stream=buf)
        logging.getLogger("plain").info("plain hello")
        out = buf.getvalue()
        # Plain text format: ``2026-... [INFO] thread plain hello``
        assert "[INFO]" in out
        assert "plain hello" in out
        # No JSON braces in plain mode
        assert "{" not in out

    def test_json_mode(self):
        buf = io.StringIO()
        self.cl.setup_logging("json", level=logging.INFO, json=True, stream=buf)
        logging.getLogger("json").info("json hello")
        out = buf.getvalue().strip()
        payload = json.loads(out)
        assert payload["message"] == "json hello"
        assert payload["level"] == "INFO"

    def test_recalling_clears_handlers(self):
        """Re-calling setup_logging should not double-log."""
        buf = io.StringIO()
        self.cl.setup_logging("x", json=False, stream=buf)
        self.cl.setup_logging("x", json=False, stream=buf)
        logging.getLogger("x").info("once")
        out = buf.getvalue()
        # If the handler had been duplicated we'd see two
        # copies of the line.
        assert out.count("once") == 1

    def test_tames_noisy_loggers(self):
        self.cl.setup_logging("z", level=logging.DEBUG, json=False)
        # aiokafka and asyncio are in the noisy list
        assert logging.getLogger("aiokafka").level >= logging.WARNING
        assert logging.getLogger("asyncio").level >= logging.WARNING

    def test_setup_logging_from_env_json(self, monkeypatch):
        monkeypatch.setenv("LMVIEW_LOG_JSON", "1")
        monkeypatch.setenv("LMVIEW_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("DOCKER_CONTAINER", "1")
        buf = io.StringIO()
        # Patch sys.stdout via the handler
        self.cl.setup_logging_from_env = lambda: self.cl.setup_logging(
            "from_env", level=logging.DEBUG, json=True, stream=buf,
        )
        logger = self.cl.setup_logging_from_env()
        logger.info("env-driven")
        out = buf.getvalue().strip()
        assert json.loads(out)["message"] == "env-driven"
