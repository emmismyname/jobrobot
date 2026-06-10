from __future__ import annotations

from typing import Any

import pandas as pd
import requests


REQUEST_TIMEOUT_SECONDS = 20


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _enabled(value: Any) -> bool:
    return _clean(value).casefold() in {"yes", "y", "true", "1", "enabled"}


def _location_from_greenhouse(job: dict[str, Any]) -> str:
    location = job.get("location") or {}
    return _clean(location.get("name"))


def _location_from_lever(job: dict[str, Any]) -> str:
    categories = job.get("categories") or {}
    parts = [
        _clean(categories.get("location")),
        _clean(categories.get("team")),
        _clean(categories.get("commitment")),
    ]
    return ", ".join(part for part in parts if part)


def _location_from_ashby(job: dict[str, Any]) -> str:
    location = job.get("location")
    if isinstance(location, dict):
        return _clean(location.get("name"))
    return _clean(location)


def scrape_greenhouse(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])

    return [
        {
            "title": _clean(job.get("title")),
            "company": company_name or slug,
            "location": _location_from_greenhouse(job),
            "source": "greenhouse",
            "job_url": _clean(job.get("absolute_url")),
            "description": _clean(job.get("content")),
            "search_term": f"official:{slug}",
            "source_type": "official_greenhouse",
        }
        for job in jobs
    ]


def scrape_lever(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json()

    return [
        {
            "title": _clean(job.get("text")),
            "company": company_name or slug,
            "location": _location_from_lever(job),
            "source": "lever",
            "job_url": _clean(job.get("hostedUrl") or job.get("applyUrl")),
            "description": _clean(job.get("descriptionPlain") or job.get("description")),
            "search_term": f"official:{slug}",
            "source_type": "official_lever",
        }
        for job in jobs
    ]


def scrape_ashby(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])

    return [
        {
            "title": _clean(job.get("title")),
            "company": company_name or slug,
            "location": _location_from_ashby(job),
            "source": "ashby",
            "job_url": _clean(job.get("jobUrl") or job.get("applyUrl")),
            "description": _clean(job.get("descriptionPlain") or job.get("description")),
            "search_term": f"official:{slug}",
            "source_type": "official_ashby",
        }
        for job in jobs
    ]


def scrape_workday(company_config: dict[str, Any]) -> list[dict[str, Any]]:
    # TODO: Workday tenants vary by company and often require tenant-specific
    # API URLs and pagination payloads. Keep the interface here and add
    # company-specific parsing once a target Workday URL is confirmed.
    company_name = _clean(company_config.get("Company Name"))
    print(f"[official] Workday scraper TODO for {company_name}")
    return []


def scrape_official_sources(company_db: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for company in company_db:
        if not _enabled(company.get("Use Official Scraper")):
            continue

        company_name = _clean(company.get("Company Name"))
        ats_type = _clean(company.get("ATS Type")).casefold()
        slug = _clean(company.get("ATS Company Slug"))
        if not ats_type or not slug:
            print(f"[official] Skipping {company_name}: missing ATS Type or ATS Company Slug")
            continue

        print(f"[official] Searching {company_name} via {ats_type} ({slug})")
        try:
            if ats_type == "greenhouse":
                jobs = scrape_greenhouse(slug, company_name)
            elif ats_type == "lever":
                jobs = scrape_lever(slug, company_name)
            elif ats_type == "ashby":
                jobs = scrape_ashby(slug, company_name)
            elif ats_type == "workday":
                jobs = scrape_workday(company)
            else:
                print(f"[official] Unsupported ATS Type for {company_name}: {ats_type}")
                jobs = []
        except Exception as exc:
            print(f"[official] Failed {company_name} via {ats_type}: {exc}")
            continue

        rows.extend(jobs)

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    print(f"[official] Total official jobs scraped: {len(frame)}")
    return frame
