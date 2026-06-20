"""Shared AI runtime configuration.

Public provider mode is intentionally small:
`auto`, `local`, `api`, or `none`. Model choice lives in YAML catalog plus
provider-specific key availability.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_AI_MODES = {"auto", "local", "api", "none"}
VALID_ORCHESTRATION_MODES = {"legacy", "langgraph"}
DEFAULT_API_MODEL = "openai/qwen3.5-plus"
DEFAULT_QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


@dataclass(frozen=True)
class AIProviderConfig:
    name: str
    provider_type: str
    model: str
    base_url: Optional[str] = None
    env_key: Optional[str] = None
    priority: int = 100
    is_local: bool = False


@dataclass(frozen=True)
class AISettings:
    mode: str
    config_path: Path
    providers: List[AIProviderConfig]
    rag_enabled: bool
    rag_top_k: int
    rag_min_score: float
    embedding_model: str
    temperature: float
    max_tokens: int
    top_p: float
    timeout_seconds: int
    orchestration_mode: str = "legacy"


def normalize_mode(value: Optional[str]) -> str:
    """Normalize legacy/invalid provider modes to the new public set."""
    mode = (value or "auto").strip().lower()
    if mode == "mock":
        return "none"
    if mode not in VALID_AI_MODES:
        return "auto"
    return mode


def _patch_feedparser_compat() -> None:
    """Feedparser 6.x removed _parse_date from package-level exports.

    Patch feedparser.datetimes so internal imports in feedparser/http.py
    (from .datetimes import _parse_date) continue to work.
    """
    try:
        from feedparser.datetimes import _parse as _parse_module
        import feedparser.datetimes as _dt
        if not hasattr(_dt, "_parse_date"):
            _dt._parse_date = getattr(_parse_module, "_parse_date", None)
    except Exception:
        pass  # feedparser not installed or already patched
    """Resolve provider key with Qwen legacy alias support."""
    if env_key == "DASHSCOPE_API_KEY":
        return os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY", "")
    if not env_key:
        return ""
    return os.environ.get(env_key, "")


def _default_config_path(mode: str) -> Path:
    root = Path(__file__).resolve().parent
    if mode == "api":
        return root / "configs" / "ai.api.yaml"
    if mode in {"local", "auto"}:
        return root / "configs" / "ai.local.yaml"
    return root / "configs" / "ai.test.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_settings() -> AISettings:
    """Load AI settings from env plus YAML catalog."""
    mode = normalize_mode(os.environ.get("AI_MODE"))
    config_path_value = os.environ.get("AI_CONFIG_PATH", "").strip()
    config_path = Path(config_path_value).expanduser() if config_path_value else Path()
    if not config_path_value:
        config_path = _default_config_path(mode)

    config = _load_yaml(config_path)
    inference = config.get("inference") or {}
    rag = config.get("rag") or {}
    provider_rows = config.get("providers") or []
    providers: List[AIProviderConfig] = []

    for row in provider_rows:
        if not isinstance(row, dict):
            continue
        provider_type = str(row.get("type") or "")
        public_name = str(row.get("public_provider") or "").strip().lower()
        if public_name not in {"local", "api", "none"}:
            public_name = "local" if row.get("is_local") or provider_type == "vllm" else "api"
        if provider_type == "none":
            public_name = "none"
        providers.append(
            AIProviderConfig(
                name=public_name,
                provider_type=provider_type,
                model=str(row.get("model") or DEFAULT_API_MODEL),
                base_url=row.get("base_url"),
                env_key=row.get("env_key"),
                priority=int(row.get("priority") or 100),
                is_local=bool(row.get("is_local") or provider_type == "vllm"),
            )
        )

    if not any(p.name == "api" for p in providers):
        providers.append(
            AIProviderConfig(
                name="api",
                provider_type="litellm",
                model=DEFAULT_API_MODEL,
                base_url=DEFAULT_QWEN_BASE_URL,
                env_key="DASHSCOPE_API_KEY",
                priority=10,
            )
        )

    providers.append(
        AIProviderConfig(
            name="none",
            provider_type="none",
            model="lmview-none",
            priority=999,
        )
    )

    orch_mode = os.environ.get("AI_ORCHESTRATION", "legacy").strip().lower()
    if orch_mode not in VALID_ORCHESTRATION_MODES:
        orch_mode = "legacy"

    return AISettings(
        mode=mode,
        config_path=config_path,
        providers=sorted(providers, key=lambda p: p.priority),
        rag_enabled=bool(rag.get("enabled", True)),
        rag_top_k=int(rag.get("top_k", 6)),
        rag_min_score=float(rag.get("min_score", 0.25)),
        embedding_model=str(rag.get("embedding_model") or "all-MiniLM-L6-v2"),
        temperature=float(inference.get("temperature", 0.3)),
        max_tokens=int(inference.get("max_tokens", 2048)),
        top_p=float(inference.get("top_p", 0.95)),
        timeout_seconds=int(inference.get("timeout_seconds", 60)),
        orchestration_mode=orch_mode,
    )


# ── Multi-key rotation ───────────────────────────────────────────────────────

_API_KEY_INDEX: int = 0
"""Current active key index (module-level state for rotation)."""


def get_api_keys(env_key: str) -> list:
    """Resolve all available API keys for a provider."""
    if env_key == "DASHSCOPE_API_KEY":
        multi = os.environ.get("DASHSCOPE_API_KEYS", "")
        if multi:
            keys = [k.strip() for k in multi.split(",") if k.strip()]
            if keys:
                return keys
        single = os.environ.get("DASHSCOPE_API_KEY", "") or os.environ.get("QWEN_API_KEY", "")
        return [single] if single else []
    if not env_key:
        return []
    key = os.environ.get(env_key, "")
    return [key] if key else []


def get_api_key(env_key: str) -> str:
    """Return the first (default) API key for a provider."""
    keys = get_api_keys(env_key)
    return keys[0] if keys else ""


def rotate_api_key(env_key: str) -> str:
    """Rotate to the next API key; return it. Round-robin."""
    global _API_KEY_INDEX
    keys = get_api_keys(env_key)
    if not keys:
        return ""
    _API_KEY_INDEX = (_API_KEY_INDEX + 1) % len(keys)
    return keys[_API_KEY_INDEX]


def get_current_api_key(env_key: str) -> str:
    """Get current active API key (after rotation)."""
    keys = get_api_keys(env_key)
    return keys[_API_KEY_INDEX % len(keys)] if keys else ""

def list_available_api_models(settings: Optional[AISettings] = None) -> List[str]:
    """Return API models with available keys."""
    cfg = settings or load_settings()
    models = []
    for provider in cfg.providers:
        if provider.name != "api":
            continue
        if provider.env_key and not get_api_key(provider.env_key):
            continue
        models.append(provider.model.replace("openai/", ""))
    return models
