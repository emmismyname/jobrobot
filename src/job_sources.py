from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.ats_sources import discover_ats_jobs
from src.scraper import scrape_all


def discover_jobs(company_db: list[dict], search_terms: Iterable[str], locations: Iterable[str]) -> pd.DataFrame:
    frames = [
        discover_ats_jobs(company_db),
        scrape_all(search_terms, locations),
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat([frame.dropna(axis=1, how="all") for frame in frames], ignore_index=True)
