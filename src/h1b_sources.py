from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.company_normalizer import normalize_company_name
from src.utils import utc_now_string


DOL_DISCLOSURE_URL = "https://www.dol.gov/agencies/eta/foreign-labor/performance"
USCIS_EMPLOYER_DATA_HUB_URL = "https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub"

RELEVANT_TITLE_KEYWORDS = [
    "electrical engineer",
    "electronics engineer",
    "hardware engineer",
    "firmware engineer",
    "embedded software engineer",
    "semiconductor",
    "process engineer",
    "manufacturing engineer",
    "validation engineer",
    "test engineer",
    "reliability engineer",
    "product engineer",
    "systems engineer",
    "controls engineer",
    "software engineer",
    "robotics engineer",
    "mechanical engineer",
    "biomedical engineer",
    "quality engineer",
    "automation engineer",
    "field service engineer",
    "applications engineer",
]

RELEVANT_SOC_PREFIXES = {"17-", "15-", "19-104", "29-"}


def _find_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {column.upper().replace(" ", "_"): column for column in frame.columns}
    for candidate in candidates:
        key = candidate.upper().replace(" ", "_")
        if key in normalized:
            return normalized[key]
    return None


def load_oflc_disclosure_file(path_or_url: str | Path) -> pd.DataFrame:
    value = str(path_or_url)
    if value.startswith("http"):
        if value.endswith(".xlsx"):
            return pd.read_excel(value)
        return pd.read_csv(value)
    path = Path(value)
    if path.suffix.casefold() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def filter_relevant_h1b_records(records: pd.DataFrame) -> pd.DataFrame:
    title_col = _find_column(records, ["JOB_TITLE", "Job Title", "TITLE"])
    soc_col = _find_column(records, ["SOC_CODE", "SOC Code", "SOC"])
    if title_col is None and soc_col is None:
        return records.iloc[0:0].copy()
    title_text = records[title_col].fillna("").astype(str).str.casefold() if title_col else ""
    title_match = title_text.apply(
        lambda value: any(keyword in value for keyword in RELEVANT_TITLE_KEYWORDS)
    ) if title_col else False
    soc_match = records[soc_col].fillna("").astype(str).apply(
        lambda value: any(value.startswith(prefix) for prefix in RELEVANT_SOC_PREFIXES)
    ) if soc_col else False
    return records[title_match | soc_match].copy()


def summarize_h1b_records(records: pd.DataFrame) -> pd.DataFrame:
    if records.empty:
        return pd.DataFrame()
    employer_col = _find_column(records, ["EMPLOYER_NAME", "Employer Name", "Company Name"])
    title_col = _find_column(records, ["JOB_TITLE", "Job Title", "TITLE"])
    soc_col = _find_column(records, ["SOC_CODE", "SOC Code", "SOC"])
    state_col = _find_column(records, ["WORKSITE_STATE", "Worksite State", "STATE"])
    year_col = _find_column(records, ["FISCAL_YEAR", "Fiscal Year", "YEAR"])
    if employer_col is None:
        return pd.DataFrame()

    rows = []
    for employer, group in records.groupby(employer_col):
        count = len(group)
        signal = "High" if count >= 3 else "Medium" if count >= 2 else "Low"
        rows.append(
            {
                "Company Name": str(employer).strip(),
                "Normalized Company Name": normalize_company_name(employer),
                "H1B Sponsor Signal": signal,
                "H1B Case Count": count,
                "Recent H1B Years": ", ".join(sorted({str(v) for v in group[year_col].dropna().unique()})) if year_col else "",
                "Common Job Titles": ", ".join(group[title_col].dropna().astype(str).value_counts().head(5).index) if title_col else "",
                "Common SOC Codes": ", ".join(group[soc_col].dropna().astype(str).value_counts().head(5).index) if soc_col else "",
                "Common Worksite States": ", ".join(group[state_col].dropna().astype(str).value_counts().head(5).index) if state_col else "",
                "H1B Evidence URL": DOL_DISCLOSURE_URL,
                "Source": "DOL OFLC disclosure data",
                "Last Checked At": utc_now_string(),
            }
        )
    return pd.DataFrame(rows)


def discover_h1b_companies(disclosure_path: str | Path | None = None) -> pd.DataFrame:
    if disclosure_path is None:
        print("[h1b] No local DOL disclosure file configured. Skipping H-1B discovery.")
        return pd.DataFrame()
    records = load_oflc_disclosure_file(disclosure_path)
    return summarize_h1b_records(filter_relevant_h1b_records(records))
