"""Configuration loading for ProjectPilot Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _load_yaml_fallback(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by the Day 1 example config."""
    data: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            current_section = {}
            data[key] = current_section
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        parsed_value = _parse_scalar(value)

        if line.startswith(" ") and current_section is not None:
            current_section[key] = parsed_value
        else:
            data[key] = parsed_value
            current_section = None

    return data


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return _load_yaml_fallback(text)

    loaded = yaml.safe_load(text)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("ProjectPilot config must be a YAML mapping.")
    return loaded
