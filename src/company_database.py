from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src import config
from src.company_normalizer import find_duplicate_candidates, normalize_company_name
from src.utils import utc_now_string


COLUMN_ALIASES = {
    "Normalized Name": "Normalized Company Name",
    "Careers URL": "Official Careers URL",
    "Job Search URL": "Official Job Search URL",
    "Source Files": "Source",
    "Last Verified / Added": "Last Updated At",
}


def _clean_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _first_non_empty(values: pd.Series) -> str:
    for value in values:
        clean = _clean_value(value)
        if clean:
            return clean
    return ""


def _merge_text(values: pd.Series) -> str:
    parts = []
    seen = set()
    for value in values:
        clean = _clean_value(value)
        if not clean:
            continue
        for part in clean.replace("\n", ";").split(";"):
            item = part.strip()
            key = item.casefold()
            if item and key not in seen:
                parts.append(item)
                seen.add(key)
    return "; ".join(parts)


def _standardize_columns(frame: pd.DataFrame, source_sheet: str) -> pd.DataFrame:
    frame = frame.rename(columns=COLUMN_ALIASES).copy()
    for column in config.DISCOVERY_COMPANY_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["Company Name"] = frame["Company Name"].fillna("").astype(str).str.strip()
    frame = frame[frame["Company Name"] != ""].copy()
    frame["Normalized Company Name"] = frame["Company Name"].apply(normalize_company_name)
    frame["Source"] = frame["Source"].where(frame["Source"].astype(str).str.strip() != "", source_sheet)
    return frame[config.DISCOVERY_COMPANY_COLUMNS]


def read_company_sheets(path: Path = config.COMPANY_MASTER_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Company master workbook not found: {path}. Put your seed list at data/company_master.xlsx."
        )
    workbook = pd.ExcelFile(path)
    frames = []
    for sheet_name in config.COMPANY_MASTER_SHEETS:
        if sheet_name not in workbook.sheet_names:
            continue
        frame = pd.read_excel(path, sheet_name=sheet_name)
        frames.append(_standardize_columns(frame, sheet_name))
    if not frames:
        raise ValueError(
            f"No supported sheets found in {path}. Expected one of: {', '.join(config.COMPANY_MASTER_SHEETS)}"
        )
    return pd.concat(frames, ignore_index=True)


def dedupe_companies(companies: pd.DataFrame) -> pd.DataFrame:
    companies = companies.copy()
    companies["Normalized Company Name"] = companies["Company Name"].apply(normalize_company_name)
    grouped_rows = []
    merge_columns = {"Source", "Source URLs", "Notes", "Target Keywords", "Major Locations"}
    for _, group in companies.groupby("Normalized Company Name", sort=False):
        row = {}
        for column in config.DISCOVERY_COMPANY_COLUMNS:
            if column in merge_columns:
                row[column] = _merge_text(group[column])
            else:
                row[column] = _first_non_empty(group[column])
        row["Normalized Company Name"] = group["Normalized Company Name"].iloc[0]
        row["Company Name"] = _first_non_empty(group["Company Name"])
        if not row["Last Updated At"]:
            row["Last Updated At"] = utc_now_string()
        grouped_rows.append(row)
    return pd.DataFrame(grouped_rows, columns=config.DISCOVERY_COMPANY_COLUMNS)


def load_company_master(path: Path = config.COMPANY_MASTER_PATH) -> pd.DataFrame:
    return dedupe_companies(read_company_sheets(path))


def write_normalized_workbook(
    companies: pd.DataFrame,
    output_path: Path = config.COMPANY_MASTER_NORMALIZED_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duplicates = find_duplicate_candidates(companies)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        companies.to_excel(writer, sheet_name="normalized_companies", index=False)
        duplicates.to_excel(writer, sheet_name="duplicate_candidates", index=False)


def normalize_master_workbook(
    input_path: Path = config.COMPANY_MASTER_PATH,
    output_path: Path = config.COMPANY_MASTER_NORMALIZED_PATH,
) -> pd.DataFrame:
    companies = load_company_master(input_path)
    write_normalized_workbook(companies, output_path)
    return companies


def existing_normalized_names(companies: pd.DataFrame) -> set[str]:
    return {
        normalize_company_name(name)
        for name in companies["Company Name"].fillna("")
        if normalize_company_name(name)
    }
