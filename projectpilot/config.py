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
    """Parse the small YAML subset used by the example config."""
    data: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if not line.startswith(" ") and line.endswith(":"):
            key = stripped[:-1].strip()
            current_section = {}
            data[key] = current_section
            current_list_key = None
            continue

        if stripped.startswith("- ") and current_section is not None and current_list_key:
            section_list = current_section.setdefault(current_list_key, [])
            if isinstance(section_list, list):
                section_list.append(_parse_scalar(stripped[2:]))
            continue

        if ":" not in line:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        if not value.strip():
            parsed_value: Any = []
            current_list_key = key
        else:
            parsed_value = _parse_scalar(value)
            current_list_key = None

        if indent > 0 and current_section is not None:
            current_section[key] = parsed_value
        else:
            data[key] = parsed_value
            current_section = None
            current_list_key = None

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
