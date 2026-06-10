from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from src.config import A_LIST_COMPANIES

ROLE_FAMILY_KEYWORDS = [
    "process",
    "hardware",
    "electrical",
    "validation",
    "test engineer",
    "reliability",
    "failure analysis",
    "firmware",
    "embedded",
    "asic",
    "fpga",
    "vlsi",
    "silicon",
    "semiconductor",
    "field applications",
    "applications engineer",
    "customer engineer",
    "product engineer",
    "manufacturing engineer",
    "controls engineer",
]

EARLY_CAREER_KEYWORDS = [
    "new grad",
    "new graduate",
    "new college grad",
    "entry level",
    "entry-level",
    "associate engineer",
    "engineer i",
]

STRONG_NEGATIVE_KEYWORDS = [
    "senior",
    "staff",
    "principal",
    "manager",
    "director",
    "engineer iii",
    "engineer iv",
    "postdoc",
    "postdoctoral",
    "phd required",
    "civil",
    "highway",
    "structural",
    "forensic",
    "korean bilingual",
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
    return str(value)


def _job_text(row: Any) -> str:
    fields = [
        "title",
        "company",
        "location",
        "description",
        "job_type",
        "job_url",
        "source_type",
    ]
    return " ".join(_value(row, field) for field in fields).casefold()


def _company_list(companies: Iterable[Any]) -> list[str]:
    names = []
    for company in companies:
        if isinstance(company, dict):
            name = company.get("Company Name", "")
        else:
            name = company
        if str(name).strip():
            names.append(str(name).strip())
    return names


def contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    text_folded = text.casefold()
    return any(keyword.casefold() in text_folded for keyword in keywords)


def matched_keywords(row: Any, keywords: Iterable[str]) -> list[str]:
    text = _job_text(row)
    return [keyword for keyword in keywords if keyword.casefold() in text]


def has_role_family_match(row: Any) -> bool:
    title = _value(row, "title").casefold()
    text = _job_text(row)
    return contains_keyword(title, ROLE_FAMILY_KEYWORDS) or contains_keyword(
        text, ROLE_FAMILY_KEYWORDS
    )


def has_early_career_signal(row: Any) -> bool:
    return contains_keyword(_job_text(row), EARLY_CAREER_KEYWORDS)


def has_strong_negative_signal(row: Any) -> bool:
    return contains_keyword(_job_text(row), STRONG_NEGATIVE_KEYWORDS)


def is_official_source(row: Any) -> bool:
    return _value(row, "source_type").casefold().startswith("official_")


def is_target_company(row: Any, companies: Iterable[Any]) -> bool:
    company = _value(row, "company").casefold()
    return any(target.casefold() in company for target in _company_list(companies))


def is_relevant_job(
    row: Any,
    companies: Iterable[Any],
    positive_keywords: Iterable[str],
    negative_keywords: Iterable[str],
) -> bool:
    text = _job_text(row)

    if contains_keyword(text, negative_keywords) or has_strong_negative_signal(row):
        return False

    if not has_role_family_match(row):
        return False

    score = score_job(row, companies, [])
    if has_early_career_signal(row):
        return True
    if is_target_company(row, companies) and score >= 6:
        return True
    if is_official_source(row) and score >= 7:
        return True
    return False


def score_job(row: Any, companies: Iterable[Any], target_locations: Iterable[str]) -> int:
    text = _job_text(row)
    company = _value(row, "company").casefold()
    location = _value(row, "location").casefold()
    job_url = _value(row, "job_url").strip()
    source_type = _value(row, "source_type").casefold()

    score = 0

    if source_type.startswith("official_"):
        score += 10
    if source_type in {"official_greenhouse", "official_lever", "official_ashby"}:
        score += 9
    if source_type == "official_workday":
        score += 8
    if source_type == "jobspy_google":
        score += 3
    if source_type == "jobspy_indeed":
        score += 1
    if source_type == "jobspy_linkedin":
        score += 1

    if any(
        phrase in text
        for phrase in ["new grad", "new graduate", "new college grad"]
    ):
        score += 5
    if any(
        phrase in text
        for phrase in ["entry level", "entry-level", "associate engineer", "engineer i"]
    ):
        score += 4
    if any(name in company for name in A_LIST_COMPANIES):
        score += 2
    if has_role_family_match(row):
        score += 3
    if any(place.casefold() in location for place in target_locations):
        score += 2
    if has_strong_negative_signal(row):
        score -= 20
    if not job_url:
        score -= 3

    return score
