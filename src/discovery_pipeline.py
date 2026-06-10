from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from src import config
from src.company_database import (
    existing_normalized_names,
    load_company_master,
    write_normalized_workbook,
)
from src.company_normalizer import normalize_company_name
from src.company_scoring import add_company_scores
from src.h1b_sources import discover_h1b_companies
from src.investment_sources import discover_investment_companies
from src.notifier import send_company_discovery_alert
from src.storage import load_source_state, save_source_state
from src.utils import utc_now_string


PENDING_COLUMNS = [
    "Company Name",
    "Normalized Company Name",
    "overall_company_score",
    "Recommended Action",
    "H1B Sponsor Signal",
    "Industry Focus",
    "Major Locations",
    "Headquarters",
    "Official Careers URL",
    "Official Job Search URL",
    "ATS Type",
    "ATS Company Slug",
    "Source",
    "Source URL",
    "Discovery Reason",
    "Last Checked At",
]


def _empty_pending() -> pd.DataFrame:
    return pd.DataFrame(columns=PENDING_COLUMNS)


def _standardize_candidate_frame(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    if frame.empty:
        return _empty_pending()
    result = frame.copy()
    aliases = {
        "Company URL": "Company URL",
        "Careers URL": "Official Careers URL",
        "Source URLs": "Source URL",
        "H1B Evidence URL": "Source URL",
        "Company URL": "Source URL",
    }
    result = result.rename(columns=aliases)
    for column in PENDING_COLUMNS:
        if column not in result.columns:
            result[column] = ""
    result["Company Name"] = result["Company Name"].fillna("").astype(str).str.strip()
    result = result[result["Company Name"] != ""].copy()
    result["Normalized Company Name"] = result["Company Name"].apply(normalize_company_name)
    result["Source"] = result["Source"].where(result["Source"].astype(str).str.strip() != "", source)
    result["Last Checked At"] = result["Last Checked At"].where(
        result["Last Checked At"].astype(str).str.strip() != "",
        utc_now_string(),
    )
    return result[PENDING_COLUMNS]


def collect_candidate_companies() -> pd.DataFrame:
    frames = [
        _standardize_candidate_frame(discover_h1b_companies(), "H1B"),
        _standardize_candidate_frame(discover_investment_companies(), "Investment"),
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return _empty_pending()
    candidates = pd.concat(frames, ignore_index=True)
    candidates = candidates.drop_duplicates(subset=["Normalized Company Name"], keep="first")
    return candidates


def split_existing_and_pending(master: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidates.empty:
        return candidates.copy(), candidates.copy()
    existing_names = existing_normalized_names(master)
    is_existing = candidates["Normalized Company Name"].isin(existing_names)
    return candidates[is_existing].copy(), candidates[~is_existing].copy()


def write_pending_companies(pending: pd.DataFrame, path: Path = config.PENDING_NEW_COMPANIES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scored = add_company_scores(pending) if not pending.empty else _empty_pending()
    if not scored.empty:
        scored = scored.sort_values("overall_company_score", ascending=False)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        scored.to_excel(writer, sheet_name="pending_new_companies", index=False)


def append_discovery_log(
    pending: pd.DataFrame,
    existing_updates: pd.DataFrame,
    path: Path = config.COMPANY_DISCOVERY_LOG_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "event_type",
        "company_name",
        "normalized_company_name",
        "source",
        "score",
        "recommended_action",
    ]
    file_exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        timestamp = utc_now_string()
        for event_type, frame in [("pending_new_company", pending), ("existing_company_signal", existing_updates)]:
            scored = add_company_scores(frame) if not frame.empty else frame
            for _, row in scored.iterrows():
                writer.writerow(
                    {
                        "timestamp": timestamp,
                        "event_type": event_type,
                        "company_name": row.get("Company Name", ""),
                        "normalized_company_name": row.get("Normalized Company Name", ""),
                        "source": row.get("Source", ""),
                        "score": row.get("overall_company_score", ""),
                        "recommended_action": row.get("Recommended Action", ""),
                    }
                )


def merge_new_companies_into_master(master: pd.DataFrame, pending: pd.DataFrame) -> pd.DataFrame:
    if pending.empty:
        return master
    new_rows = []
    for _, row in pending.iterrows():
        new_row = {column: "" for column in config.DISCOVERY_COMPANY_COLUMNS}
        for column in new_row:
            if column in row:
                new_row[column] = row[column]
        new_row["Monitoring Status"] = new_row.get("Monitoring Status") or "Pending Review"
        new_row["Last Updated At"] = utc_now_string()
        new_rows.append(new_row)
    return pd.concat([master, pd.DataFrame(new_rows)], ignore_index=True)


def run_discovery_pipeline(auto_merge: bool = config.AUTO_MERGE_NEW_COMPANIES) -> dict[str, Any]:
    print("[discovery] Starting company discovery pipeline")
    master = load_company_master(config.COMPANY_MASTER_PATH)
    master = add_company_scores(master)
    write_normalized_workbook(master, config.COMPANY_MASTER_NORMALIZED_PATH)
    print(f"[discovery] Normalized master companies: {len(master)}")

    candidates = collect_candidate_companies()
    existing_updates, pending = split_existing_and_pending(master, candidates)
    pending_scored = add_company_scores(pending) if not pending.empty else _empty_pending()
    write_pending_companies(pending, config.PENDING_NEW_COMPANIES_PATH)
    append_discovery_log(pending, existing_updates, config.COMPANY_DISCOVERY_LOG_PATH)

    if auto_merge and not pending.empty:
        print("[discovery] AUTO_MERGE_NEW_COMPANIES enabled. Merging pending rows in normalized output only.")
        merged = merge_new_companies_into_master(master, pending)
        write_normalized_workbook(merged, config.COMPANY_MASTER_NORMALIZED_PATH)

    source_state = load_source_state()
    source_state["last_company_discovery_run"] = utc_now_string()
    source_state["last_pending_count"] = int(len(pending))
    source_state["last_existing_signal_count"] = int(len(existing_updates))
    save_source_state(source_state)

    if not pending_scored.empty:
        send_company_discovery_alert(pending_scored.to_dict(orient="records"))

    print(
        f"[discovery] Done. pending={len(pending)} existing_signals={len(existing_updates)}"
    )
    return {
        "normalized_count": len(master),
        "candidate_count": len(candidates),
        "pending_count": len(pending),
        "existing_signal_count": len(existing_updates),
    }


if __name__ == "__main__":
    run_discovery_pipeline()
