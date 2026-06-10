from pathlib import Path

import pandas as pd

from src import main
from src.storage import (
    get_job_hash,
    get_soft_id,
    load_seen_jobs,
    load_source_state,
    save_seen_jobs,
    save_source_state,
)


def test_job_hash_is_stable():
    row = {
        "title": "Validation Engineer New Grad",
        "company": "Micron",
        "location": "Boise, ID",
        "job_url": "https://example.com/job",
        "source_type": "jobspy_indeed",
    }

    assert get_job_hash(row) == get_job_hash(row)


def test_seen_jobs_read_write():
    seen_path = Path("tests_runtime_seen_jobs.json")
    job_hashes = {"abc123", "def456"}

    try:
        save_seen_jobs(job_hashes, seen_path)

        assert load_seen_jobs(seen_path) == job_hashes
    finally:
        if seen_path.exists():
            seen_path.unlink()


def test_main_does_not_mark_seen_when_email_not_sent(monkeypatch):
    row = {
        "title": "Electrical Engineer New Grad",
        "company": "Texas Instruments",
        "location": "Dallas, TX",
        "description": "Entry level hardware role for new college graduates.",
        "job_url": "https://example.com/new-grad-main",
        "site": "indeed",
        "search_term": "Electrical Engineer New Grad",
        "source_type": "jobspy_indeed",
    }
    saved_seen_ids = []
    appended_history = []

    monkeypatch.setattr(main.config, "load_company_database", lambda: [{"Company Name": "Texas Instruments"}])
    monkeypatch.setattr(main.config, "company_names", lambda companies: ["Texas Instruments"])
    monkeypatch.setattr(main.config, "build_search_terms", lambda companies: ["Electrical Engineer New Grad"])
    monkeypatch.setattr(main.config, "build_locations", lambda companies: ["Dallas, TX"])
    monkeypatch.setattr(main, "scrape_official_sources", lambda companies: pd.DataFrame())
    monkeypatch.setattr(main, "scrape_all", lambda search_terms, locations: pd.DataFrame([row]))
    monkeypatch.setattr(main, "load_seen_ids", lambda: (set(), set()))
    monkeypatch.setattr(main, "send_job_alert", lambda jobs: False)
    monkeypatch.setattr(
        main,
        "save_seen_ids",
        lambda strict_ids, soft_ids: saved_seen_ids.append((set(strict_ids), set(soft_ids))),
    )
    monkeypatch.setattr(main, "append_jobs_history", lambda jobs: appended_history.append(jobs))

    new_jobs = main.run()

    assert len(new_jobs) == 1
    assert saved_seen_ids == []
    assert appended_history == []


def test_soft_id_dedupes_same_company_title_location_with_different_urls():
    first = {
        "title": "Hardware Engineer New Grad",
        "company": "Texas Instruments",
        "location": "Dallas, TX",
        "job_url": "https://indeed.example/job-1",
    }
    second = {
        "title": "Hardware Engineer New Grad",
        "company": "Texas Instruments",
        "location": "Dallas, TX",
        "job_url": "https://indeed.example/job-2",
    }

    assert get_job_hash(first) != get_job_hash(second)
    assert get_soft_id(first) == get_soft_id(second)


def test_source_state_read_write(tmp_path: Path):
    path = tmp_path / "source_state.json"
    state = {"last_company_discovery_run": "2026-06-10 00:00:00 UTC"}

    save_source_state(state, path)

    assert load_source_state(path) == state
