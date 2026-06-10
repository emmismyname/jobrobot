from __future__ import annotations

from typing import Any
import pandas as pd

from src import config
from src.filters import is_relevant_job, matched_keywords, score_job
from src.notifier import send_job_alert
from src.official_scrapers import scrape_official_sources
from src.scraper import scrape_all
from src.storage import (
    append_jobs_history,
    ensure_storage_files,
    get_soft_id,
    get_strict_id,
    load_seen_ids,
    save_seen_ids,
)


def _row_to_job(row: Any, score: int, keywords: list[str]) -> dict[str, Any]:
    job = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    job["score"] = score
    job["matched_keywords"] = keywords
    job["strict_id"] = get_strict_id(job)
    job["soft_id"] = get_soft_id(job)
    return job


def _combine_sources(official_df: pd.DataFrame, jobspy_df: pd.DataFrame) -> pd.DataFrame:
    frames = [frame for frame in [official_df, jobspy_df] if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat([frame.dropna(axis=1, how="all") for frame in frames], ignore_index=True)


def run() -> list[dict[str, Any]]:
    print("[main] Starting EE / Semiconductor Job Alert")
    ensure_storage_files()

    companies = config.load_company_database()
    company_names = config.company_names(companies)
    search_terms = config.build_search_terms(companies)
    locations = config.build_locations(companies)

    print(f"[main] Active companies: {len(company_names)}")
    print(f"[main] Search terms: {len(search_terms)}")
    print(f"[main] Locations: {len(locations)}")

    official_df = scrape_official_sources(companies)
    jobs_df = scrape_all(search_terms, locations)
    jobs_df = _combine_sources(official_df, jobs_df)
    if jobs_df.empty:
        print("[main] No jobs scraped.")
        return []

    seen_strict_ids, seen_soft_ids = load_seen_ids()
    new_jobs = []
    new_strict_ids = []
    new_soft_ids = []
    current_soft_ids = set(seen_soft_ids)

    for _, row in jobs_df.iterrows():
        if not is_relevant_job(
            row,
            company_names,
            config.POSITIVE_KEYWORDS,
            config.NEGATIVE_KEYWORDS,
        ):
            continue

        strict_id = get_strict_id(row)
        soft_id = get_soft_id(row)
        if strict_id in seen_strict_ids or soft_id in current_soft_ids:
            continue

        score = score_job(row, company_names, locations)
        keywords = matched_keywords(row, config.POSITIVE_KEYWORDS)
        new_jobs.append(_row_to_job(row, score, keywords))
        new_strict_ids.append(strict_id)
        new_soft_ids.append(soft_id)
        current_soft_ids.add(soft_id)

    new_jobs.sort(key=lambda job: job.get("score", 0), reverse=True)
    print(f"[main] New relevant jobs: {len(new_jobs)}")
    alert_jobs = [
        job for job in new_jobs if job.get("score", 0) >= config.MIN_EMAIL_SCORE
    ][: config.MAX_EMAIL_JOBS]
    print(f"[main] Jobs selected for email: {len(alert_jobs)}")

    if alert_jobs:
        email_sent = send_job_alert(alert_jobs)
        if email_sent:
            sent_strict_ids = {job["strict_id"] for job in alert_jobs}
            sent_soft_ids = {job["soft_id"] for job in alert_jobs}
            updated_strict_ids = set(seen_strict_ids) | sent_strict_ids
            updated_soft_ids = set(seen_soft_ids) | sent_soft_ids
            append_jobs_history(alert_jobs)
            save_seen_ids(updated_strict_ids, updated_soft_ids)
        else:
            print("[main] Email was not sent. Jobs were not marked as seen.")
    else:
        print("[main] Nothing new to notify.")

    print("[main] Done.")
    return new_jobs


if __name__ == "__main__":
    run()
