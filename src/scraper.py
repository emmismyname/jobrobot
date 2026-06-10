from __future__ import annotations

from typing import Iterable

import pandas as pd
from jobspy import scrape_jobs

from src import config


def scrape_for_search(
    search_term: str,
    location: str,
    site_name: list[str] | None = None,
    results_wanted: int = config.RESULTS_WANTED,
    hours_old: int = config.HOURS_OLD,
    country_indeed: str = config.COUNTRY_INDEED,
) -> pd.DataFrame:
    sites = site_name or list(config.SITE_NAMES)
    if config.ENABLE_LINKEDIN and "linkedin" not in sites:
        sites.append("linkedin")

    print(f"[scraper] Searching: {search_term!r} in {location!r} via {sites}")
    jobs = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
        country_indeed=country_indeed,
    )
    if jobs is None or jobs.empty:
        return pd.DataFrame()
    jobs = jobs.copy()
    jobs["search_term"] = search_term
    if "site" in jobs.columns:
        source = jobs["site"]
    elif "source" in jobs.columns:
        source = jobs["source"]
    else:
        source = pd.Series(["unknown"] * len(jobs), index=jobs.index)
    jobs["source_type"] = source.apply(
        lambda value: f"jobspy_{str(value).strip().casefold()}"
        if str(value).strip()
        else "jobspy_unknown"
    )
    return jobs


def scrape_all(search_terms: Iterable[str], locations: Iterable[str]) -> pd.DataFrame:
    frames = []
    for search_term in search_terms:
        for location in locations:
            try:
                frame = scrape_for_search(search_term, location)
            except Exception as exc:
                print(f"[scraper] Search failed for {search_term!r} / {location!r}: {exc}")
                continue
            if not frame.empty:
                frames.append(frame)

    if not frames:
        return pd.DataFrame()

    frames = [frame.dropna(axis=1, how="all") for frame in frames if not frame.empty]
    jobs = pd.concat(frames, ignore_index=True)
    if "job_url" in jobs.columns:
        jobs = jobs.drop_duplicates(subset=["job_url"], keep="first")
    else:
        jobs = jobs.drop_duplicates()
    print(f"[scraper] Total unique jobs scraped: {len(jobs)}")
    return jobs
