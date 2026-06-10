from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.config import DATA_DIR, JOBS_HISTORY_PATH, SEEN_JOBS_PATH, SOURCE_STATE_PATH
from src.utils import read_json, write_json


HISTORY_COLUMNS = [
    "date_found",
    "score",
    "title",
    "company",
    "location",
    "source",
    "source_type",
    "job_url",
    "search_term",
    "matched_keywords",
    "strict_id",
    "soft_id",
]


def _value(row: Any, key: str) -> str:
    if isinstance(row, dict):
        value = row.get(key, "")
    else:
        value = getattr(row, key, "")
        if value == "" and hasattr(row, "get"):
            value = row.get(key, "")
    if pd.isna(value):
        return ""
    return str(value).strip()


def ensure_storage_files(
    seen_path: Path = SEEN_JOBS_PATH,
    history_path: Path = JOBS_HISTORY_PATH,
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not seen_path.exists() or not seen_path.read_text(encoding="utf-8").strip():
        seen_path.write_text('{"strict_ids": [], "soft_ids": []}\n', encoding="utf-8")
    if not history_path.exists() or history_path.stat().st_size == 0:
        with history_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
            writer.writeheader()
    else:
        history_df = pd.read_csv(history_path)
        missing_columns = [
            column for column in HISTORY_COLUMNS if column not in history_df.columns
        ]
        if missing_columns:
            for column in missing_columns:
                history_df[column] = ""
            history_df = history_df[HISTORY_COLUMNS]
            history_df.to_csv(history_path, index=False, encoding="utf-8")


def _normalize_id_text(value: str) -> str:
    text = value.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_strict_id(row: Any) -> str:
    raw = "|".join(
        [
            _value(row, "company").casefold(),
            _value(row, "title").casefold(),
            _value(row, "location").casefold(),
            _value(row, "job_url").casefold(),
        ]
    )
    return _hash(raw)


def get_soft_id(row: Any) -> str:
    raw = "|".join(
        [
            _normalize_id_text(_value(row, "company")),
            _normalize_id_text(_value(row, "title")),
            _normalize_id_text(_value(row, "location")),
        ]
    )
    return _hash(raw)


def get_job_hash(row: Any) -> str:
    return get_strict_id(row)


def load_seen_ids(path: Path = SEEN_JOBS_PATH) -> tuple[set[str], set[str]]:
    ensure_storage_files(path, JOBS_HISTORY_PATH)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[storage] Invalid seen jobs file. Resetting: {path}")
        return set(), set()

    if isinstance(data, list):
        legacy_ids = {str(item) for item in data}
        return legacy_ids, set()
    if isinstance(data, dict):
        strict_ids = {str(item) for item in data.get("strict_ids", [])}
        soft_ids = {str(item) for item in data.get("soft_ids", [])}
        return strict_ids, soft_ids
    return set(), set()


def load_seen_jobs(path: Path = SEEN_JOBS_PATH) -> set[str]:
    strict_ids, soft_ids = load_seen_ids(path)
    return strict_ids | soft_ids


def save_seen_jobs(seen: Iterable[str], path: Path = SEEN_JOBS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted({str(item) for item in seen})
    path.write_text(
        json.dumps({"strict_ids": ordered, "soft_ids": []}, indent=2) + "\n",
        encoding="utf-8",
    )


def save_seen_ids(
    strict_ids: Iterable[str],
    soft_ids: Iterable[str],
    path: Path = SEEN_JOBS_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "strict_ids": sorted({str(item) for item in strict_ids}),
        "soft_ids": sorted({str(item) for item in soft_ids}),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_jobs_history(
    jobs: list[dict[str, Any]],
    path: Path = JOBS_HISTORY_PATH,
) -> None:
    ensure_storage_files(SEEN_JOBS_PATH, path)
    if not jobs:
        return
    date_found = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = []
    for job in jobs:
        rows.append(
            {
                "date_found": date_found,
                "score": job.get("score", ""),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "source": job.get("site", job.get("source", "")),
                "source_type": job.get("source_type", ""),
                "job_url": job.get("job_url", ""),
                "search_term": job.get("search_term", ""),
                "matched_keywords": ", ".join(job.get("matched_keywords", []))
                if isinstance(job.get("matched_keywords"), list)
                else job.get("matched_keywords", ""),
                "strict_id": job.get("strict_id", ""),
                "soft_id": job.get("soft_id", ""),
            }
        )
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
        writer.writerows(rows)


def load_source_state(path: Path = SOURCE_STATE_PATH) -> dict[str, Any]:
    return read_json(path, default={})


def save_source_state(state: dict[str, Any], path: Path = SOURCE_STATE_PATH) -> None:
    write_json(path, state)
