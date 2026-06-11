"""Knowledge-base registry validation and ingestion filtering."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = {
    "source_id",
    "title",
    "domain",
    "language",
    "source_type",
    "credibility_level",
    "review_status",
    "reviewer",
    "reviewed_date",
    "lmview_version_scope",
    "source_urls",
    "tags",
    "allowed_for_rag",
    "file_path",
}

ALLOWED_REVIEW_STATUS = {"approved", "pending", "draft", "deprecated"}
ALLOWED_CREDIBILITY = {"verified", "reviewed", "reference", "ai_generated", "draft", "unknown"}


def knowledge_base_root() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "ai" / "knowledge_base"


def registry_path() -> Path:
    return knowledge_base_root() / "registry.yml"


def load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load registry YAML."""
    target = path or registry_path()
    if not target.exists():
        return {"sources": []}
    text = target.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except ImportError:
        data = _load_registry_without_yaml(text)
    return data if isinstance(data, dict) else {"sources": []}


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _load_registry_without_yaml(text: str) -> Dict[str, Any]:
    """Small fallback parser for the registry's simple YAML shape."""
    data: Dict[str, Any] = {"sources": []}
    current: Optional[Dict[str, Any]] = None
    in_sources = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped == "sources:":
            in_sources = True
            continue
        if not in_sources:
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                data[key.strip()] = _parse_scalar(value)
            continue
        if stripped.startswith("- "):
            if current is not None:
                data["sources"].append(current)
            current = {}
            rest = stripped[2:].strip()
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = _parse_scalar(value)

    if current is not None:
        data["sources"].append(current)
    return data


def validate_registry(data: Dict[str, Any]) -> List[str]:
    """Return validation errors for registry metadata."""
    errors: List[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list):
        return ["registry.sources must be a list"]

    seen_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - set(source))
        if missing:
            errors.append(f"{source.get('source_id', index)} missing fields: {', '.join(missing)}")
        source_id = str(source.get("source_id") or "")
        if source_id in seen_ids:
            errors.append(f"duplicate source_id: {source_id}")
        seen_ids.add(source_id)
        if source.get("review_status") not in ALLOWED_REVIEW_STATUS:
            errors.append(f"{source_id}: invalid review_status")
        if source.get("credibility_level") not in ALLOWED_CREDIBILITY:
            errors.append(f"{source_id}: invalid credibility_level")
        if not isinstance(source.get("source_urls"), list):
            errors.append(f"{source_id}: source_urls must be a list")
        if not isinstance(source.get("tags"), list):
            errors.append(f"{source_id}: tags must be a list")
        if not isinstance(source.get("allowed_for_rag"), bool):
            errors.append(f"{source_id}: allowed_for_rag must be boolean")
        if source.get("review_status") == "approved":
            if not source.get("reviewer") or not source.get("reviewed_date"):
                errors.append(f"{source_id}: approved sources require reviewer and reviewed_date")
            if not source.get("allowed_for_rag"):
                errors.append(f"{source_id}: approved source must set allowed_for_rag true")
    return errors


def registry_entries(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return [item for item in load_registry(path).get("sources", []) if isinstance(item, dict)]


def entry_for_file(file_path: Path, path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Find registry entry for a markdown file."""
    root = knowledge_base_root()
    try:
        rel = file_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = file_path.as_posix()
    for entry in registry_entries(path):
        if entry.get("file_path") == rel:
            return entry
    return None


def allowed_for_ingestion(file_path: Path, path: Optional[Path] = None) -> bool:
    """Production ingestion gate: approved and allowed only."""
    entry = entry_for_file(file_path, path)
    if not entry:
        return False
    return entry.get("review_status") == "approved" and entry.get("allowed_for_rag") is True
