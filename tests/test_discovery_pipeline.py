from pathlib import Path

import pandas as pd

from src import discovery_pipeline
from src.discovery_pipeline import split_existing_and_pending, write_pending_companies
from src.investment_sources import discover_crunchbase_companies


def test_existing_company_not_pending():
    master = pd.DataFrame({"Company Name": ["Texas Instruments"]})
    master["Normalized Company Name"] = ["texas instruments"]
    candidates = pd.DataFrame(
        {
            "Company Name": ["Texas Instruments", "New Semi"],
            "Normalized Company Name": ["texas instruments", "new semi"],
        }
    )

    existing, pending = split_existing_and_pending(master, candidates)

    assert existing["Company Name"].tolist() == ["Texas Instruments"]
    assert pending["Company Name"].tolist() == ["New Semi"]


def test_auto_merge_false_keeps_new_company_pending(monkeypatch):
    master = pd.DataFrame(
        {
            "Company Name": ["Texas Instruments"],
            "Normalized Company Name": ["texas instruments"],
            "Industry Focus": ["Semiconductor"],
            "Target Role Family": ["Hardware"],
            "Major Locations": ["Dallas, TX"],
            "H1B Sponsor Signal": ["High"],
        }
    )
    candidate = pd.DataFrame(
        {
            "Company Name": ["New Semi"],
            "Normalized Company Name": ["new semi"],
            "Industry Focus": ["Semiconductor"],
            "Target Role Family": ["Hardware"],
            "Major Locations": ["Austin, TX"],
            "H1B Sponsor Signal": ["High"],
            "Source": ["unit"],
        }
    )
    pending_frames = []
    normalized_counts = []

    monkeypatch.setattr(discovery_pipeline, "load_company_master", lambda path: master)
    monkeypatch.setattr(discovery_pipeline, "collect_candidate_companies", lambda: candidate)
    monkeypatch.setattr(
        discovery_pipeline,
        "write_normalized_workbook",
        lambda frame, path: normalized_counts.append(len(frame)),
    )
    monkeypatch.setattr(
        discovery_pipeline,
        "write_pending_companies",
        lambda frame, path: pending_frames.append(frame.copy()),
    )
    monkeypatch.setattr(discovery_pipeline, "append_discovery_log", lambda pending, existing, path: None)
    monkeypatch.setattr(discovery_pipeline, "load_source_state", lambda: {})
    monkeypatch.setattr(discovery_pipeline, "save_source_state", lambda state: None)
    monkeypatch.setattr(discovery_pipeline, "send_company_discovery_alert", lambda companies: False)

    result = discovery_pipeline.run_discovery_pipeline(auto_merge=False)

    assert result["pending_count"] == 1
    assert pending_frames[0]["Company Name"].tolist() == ["New Semi"]
    assert normalized_counts == [1]


def test_missing_crunchbase_key_skips_without_error(monkeypatch):
    monkeypatch.delenv("CRUNCHBASE_API_KEY", raising=False)

    result = discover_crunchbase_companies()

    assert result.empty


def test_pending_new_companies_workbook_is_generated(tmp_path: Path):
    pending_path = tmp_path / "pending_new_companies.xlsx"
    pending = pd.DataFrame(
        {
            "Company Name": ["New Semi"],
            "Normalized Company Name": ["new semi"],
            "Industry Focus": ["Semiconductor"],
            "Target Role Family": ["Hardware"],
            "Major Locations": ["Austin, TX"],
            "H1B Sponsor Signal": ["High"],
            "Source": ["unit"],
        }
    )

    write_pending_companies(pending, pending_path)

    assert pending_path.exists()
    assert pd.read_excel(pending_path).iloc[0]["Company Name"] == "New Semi"
