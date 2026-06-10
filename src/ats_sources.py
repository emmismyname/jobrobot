from __future__ import annotations

import pandas as pd

from src.official_scrapers import (
    scrape_ashby,
    scrape_greenhouse,
    scrape_lever,
    scrape_official_sources,
    scrape_workday,
)


def discover_ats_jobs(company_db: list[dict]) -> pd.DataFrame:
    return scrape_official_sources(company_db)
