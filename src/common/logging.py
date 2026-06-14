"""
Standardized structured logging for LMView.

Two modes are supported:

1. **Plain text** (default for backwards compat). Uses Python's
   stdlib ``basicConfig`` with a thread/time/level prefix:

   ::

       2026-06-13 00:42:15 [INFO] MainThread WebSocket client connected

2. **JSON** (recommended for containerised deployments). Emits
   one JSON object per line so Loki / Promtail can parse it
   with ``| json``:

   ::

       {"ts":"2026-06-13T00:42:15.123Z","level":"INFO","logger":"backend.api.websocket",
        "module":"websocket","line":229,"thread":"MainThread","request_id":"8f3e2c1a",
        "message":"Stream all error for BTCUSDT: Connection reset",
        "context":{"symbol":"BTCUSDT","interval":"1m"}}

The JSON mode is opt-in via the ``json=True`` flag of
``setup_logging``. We deliberately do not pull in
``python-json-logger`` (or any other third-party library) so
that the logging module stays a zero-dependency part of the
runtime.

Helpers
-------
- :func:`setup_logging` — entry point. Call once per process.
- :func:`bind_request_id` — attach a request-id to every
  subsequent log line emitted by *this* call stack.
- :func:`current_request_id` — read back the request-id (or
  ``"-"`` if none).
- :func:`log_with_context` — emit a single line with a custom
  ``context`` dict, even if the call site doesn't want to use
  ``extra=``.
"""

from __future__ import annotations

import contextvars
import datetime as _dt
import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional

# ── Request-id context ────────────────────────────────────────────────────
# ContextVars are the stdlib-blessed way to carry per-request
# state through async call stacks. Each asyncio task gets its
# own copy of the var, so a request-id set in one task never
# leaks to another.
_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "lmview_request_id", default="-"
)


def bind_request_id(rid: str) -> None:
    """Set the request-id for the current call stack.

    Subsequent log lines in the same task/thread will pick up
    this value automatically.
    """
    _REQUEST_ID.set(rid)


def current_request_id() -> str:
    """Return the request-id set via :func:`bind_request_id`, or ``"-"``."""
    return _REQUEST_ID.get()


# ── Formatter ────────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line on stdout.

    The output is always a single line — multiline records
    (e.g. tracebacks) are inlined with ``\\n`` escapes. This
    matches Loki's ``| json`` parser expectations.

    Standard fields produced for every record:

    * ``ts``      — RFC3339 timestamp with milliseconds, always UTC.
    * ``level``   — ``"DEBUG"``/``"INFO"``/``"WARNING"``/``"ERROR"``/``"CRITICAL"``.
    * ``logger``  — the logger name (e.g. ``"backend.api.websocket"``).
    * ``module``  — the source module (``"websocket"``).
    * ``line``    — the source line number.
    * ``thread``  — the thread name.
    * ``request_id`` — the value of :data:`_REQUEST_ID`.
    * ``message`` — the formatted log message.
    * ``context`` — a dict built from ``record.__dict__`` minus
      the standard ``LogRecord`` fields (and minus ``message``).

    If the record carries an exception, two extra fields are
    added: ``exc_info`` (the multi-line traceback) and
    ``exc_type`` (the exception class name).
    """

    # Standard LogRecord attributes that we never want to dump
    # into the ``context`` dict. Sourced from the CPython source
    # so the list stays in sync across Python versions.
    _RESERVED = frozenset(
        (
            "args", "asctime", "created", "exc_info", "exc_text",
            "filename", "funcName", "levelname", "levelno",
            "lineno", "message", "module", "msecs", "msg", "name",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName", "taskName",
        )
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: Dict[str, Any] = {
            "ts": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "thread": record.threadName,
            "request_id": current_request_id(),
            "message": record.getMessage(),
        }
        # Pull custom fields out of the record so they're easy
        # to filter on in Loki. We drop the reserved set first.
        ctx: Dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self._RESERVED
            and not k.startswith("_")
        }
        if ctx:
            payload["context"] = ctx
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__
            payload["exc_info"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            # Last-ditch: never let a bad field crash the logger.
            return json.dumps(
                {
                    **payload,
                    "context": {"_serialise_error": str(exc)},
                },
                ensure_ascii=False,
            )


# ── Helper: log with context dict ─────────────────────────────────────────
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a single log line with a structured ``context`` dict.

    Equivalent to ``logger.log(level, message, extra=context)``
    but with a friendlier signature — call-sites don't have to
    import ``extra=`` semantics.
    """
    logger.log(level, message, extra=context or {})


# ── Public entry point ───────────────────────────────────────────────────
_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    name: str = __name__,
    level: int = logging.INFO,
    json: bool = False,
    stream=None,
) -> logging.Logger:
    """Configure the root logger and return a named logger.

    Args:
        name:  The name of the logger to return (e.g. ``"producer"``).
        level: The minimum log level. Default is ``INFO``.
        json:  If ``True``, emit structured JSON. Default is
            ``False`` (plain text) for backwards compatibility
            with the existing local-dev workflow.
        stream: Optional output stream. Defaults to
            ``sys.stdout`` (the standard for containers).
    """
    root = logging.getLogger()
    # Clear existing handlers so re-calling ``setup_logging``
    # (e.g. in a test fixture) doesn't double-log every line.
    for h in list(root.handlers):
        root.removeHandler(h)
    if stream is None:
        stream = sys.stdout

    handler = logging.StreamHandler(stream)
    if json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, _DEFAULT_DATEFMT))
    root.addHandler(handler)
    root.setLevel(level)

    # Tame the noisy third-party loggers that the stdlib picks up
    # by default. These are very chatty at INFO and drown out
    # the application signal in the dashboard.
    for noisy in (
        "aiokafka",
        "asyncio",
        "kafka",
        "pyflink",
        "uvicorn.access",
        "uvicorn.error",
        "websockets",
        "aiormq",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger(name)


# ── Env-var shortcut ──────────────────────────────────────────────────────
def setup_logging_from_env() -> logging.Logger:
    """Convenience wrapper that reads the standard env vars.

    * ``LMVIEW_LOG_LEVEL`` — one of DEBUG/INFO/WARNING/ERROR.
      Defaults to ``INFO``.
    * ``LMVIEW_LOG_JSON`` — ``"1"``, ``"true"``, ``"yes"`` enable
      JSON mode. Defaults to ``"1"`` in containers (we detect
      the container via the ``DOCKER_CONTAINER`` env var that
      Compose sets), ``"0"`` otherwise.

    Returns the named logger ``"lmview"``.
    """
    level_name = os.environ.get("LMVIEW_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    is_container = bool(os.environ.get("DOCKER_CONTAINER"))
    default_json = "1" if is_container else "0"
    json_flag = os.environ.get("LMVIEW_LOG_JSON", default_json).lower() in (
        "1", "true", "yes", "on",
    )
    return setup_logging("lmview", level=level, json=json_flag)
