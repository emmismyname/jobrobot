from __future__ import annotations

from typing import Any

import pandas as pd


TEXAS_CITIES = [
    "austin",
    "dallas",
    "houston",
    "plano",
    "richardson",
    "round rock",
    "taylor",
    "sherman",
]


def _text(company: dict[str, Any] | pd.Series, *keys: str) -> str:
    parts = []
    for key in keys:
        value = company.get(key, "") if hasattr(company, "get") else ""
        if value is not None and not pd.isna(value):
            parts.append(str(value))
    return " ".join(parts).casefold()


def h1b_score(signal: str) -> int:
    return {"high": 30, "medium": 18, "low": 6, "unknown": 0}.get(
        str(signal or "Unknown").casefold(),
        0,
    )


def industry_fit_score(company: dict[str, Any] | pd.Series) -> int:
    text = _text(company, "Industry Focus", "Category", "Target Role Family", "Target Keywords", "Notes")
    if "civil" in text or "construction only" in text:
        return -20
    if "semiconductor" in text:
        return 20
    if "medical device" in text or "diagnostics" in text:
        return 18
    if any(term in text for term in ["electronics manufacturing", "ems", "pcb"]):
        return 16
    if any(term in text for term in ["industrial automation", "controls"]):
        return 14
    if any(term in text for term in ["energy", "battery", "power electronics"]):
        return 12
    if "software" in text:
        return 5
    return 0


def job_fit_score(company: dict[str, Any] | pd.Series) -> int:
    text = _text(company, "Target Role Family", "Target Keywords", "Recent jobs found", "Notes")
    score = 0
    if any(
        term in text
        for term in [
            "ee",
            "ece",
            "hardware",
            "process",
            "validation",
            "test",
            "firmware",
            "embedded",
            "manufacturing",
            "quality",
        ]
    ):
        score += 20
    if any(term in text for term in ["new grad", "entry level", "engineer i", "associate engineer"]):
        score += 15
    if any(
        term in text
        for term in [
            "field service",
            "applications",
            "test technician",
            "manufacturing engineer i",
        ]
    ):
        score += 12
    return min(score, 35)


def location_score(company: dict[str, Any] | pd.Series) -> int:
    text = _text(company, "Major Locations", "Texas Presence", "Headquarters")
    if any(city in text for city in TEXAS_CITIES):
        return 18
    if "texas" in text or ", tx" in text or " tx" in text:
        return 15
    if "remote" in text and "united states" not in text:
        return 2
    if "united states" in text or "usa" in text or "us" in text:
        return 5
    return 0


def investment_score(company: dict[str, Any] | pd.Series) -> int:
    text = _text(company, "Investment Signal", "Funding Stage", "Source", "Notes")
    if "recent funding" in text or "within 24 months" in text:
        return 12
    if "yc" in text or "vc-backed" in text or "venture" in text:
        return 8
    if "public company" in text or "public" in text:
        return 5
    signal = str(company.get("Investment Signal", "") if hasattr(company, "get") else "").casefold()
    return {"high": 12, "medium": 8, "low": 2}.get(signal, 0)


def source_confidence_score(company: dict[str, Any] | pd.Series) -> int:
    text = _text(company, "Source", "Source URLs", "Official Careers URL", "ATS Type", "H1B Evidence URL")
    score = 0
    if any(term in text for term in ["official_greenhouse", "official_lever", "official_ashby", "official ats"]):
        score = max(score, 15)
    if any(term in text for term in ["dol", "uscis", "oflc"]):
        score = max(score, 15)
    if "official careers" in text or str(company.get("Official Careers URL", "")).strip():
        score = max(score, 12)
    if any(term in text for term in ["crunchbase", "investment api"]):
        score = max(score, 8)
    if "job board" in text or "indeed" in text or "google" in text:
        score = max(score, 3)
    return score


def recommended_action(score: int) -> str:
    if score >= 70:
        return "Apply_Now"
    if score >= 50:
        return "Monitor"
    if score >= 30:
        return "Research"
    return "Low Priority"


def score_company(company: dict[str, Any] | pd.Series) -> dict[str, Any]:
    scores = {
        "h1b_score": h1b_score(str(company.get("H1B Sponsor Signal", "Unknown"))),
        "job_fit_score": job_fit_score(company),
        "location_score": location_score(company),
        "industry_fit_score": industry_fit_score(company),
        "investment_score": investment_score(company),
        "source_confidence_score": source_confidence_score(company),
    }
    overall = sum(scores.values())
    scores["overall_company_score"] = overall
    scores["Recommended Action"] = recommended_action(overall)
    return scores


def add_company_scores(companies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in companies.iterrows():
        enriched = row.to_dict()
        enriched.update(score_company(row))
        rows.append(enriched)
    return pd.DataFrame(rows)
