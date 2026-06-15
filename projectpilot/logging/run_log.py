"""Minimal JSON run log writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_run_log(
    run_id: str,
    status: str,
    message: str,
    output_dir: str | Path = "run_logs",
    started_at: str | None = None,
    finished_at: str | None = None,
    extra_fields: dict[str, object] | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    record: dict[str, object] = {
        "run_id": run_id,
        "status": status,
        "started_at": started_at or utc_now_iso(),
        "finished_at": finished_at or utc_now_iso(),
        "message": message,
    }
    if extra_fields:
        record.update(extra_fields)

    log_path = output_path / "latest_run.json"
    log_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return log_path
