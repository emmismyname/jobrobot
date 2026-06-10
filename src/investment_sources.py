from __future__ import annotations

import os

import pandas as pd

from src.utils import utc_now_string


CRUNCHBASE_SEARCH_KEYWORDS = [
    "semiconductor",
    "hardware",
    "robotics",
    "medical device",
    "diagnostics",
    "manufacturing",
    "industrial automation",
    "battery",
    "energy storage",
    "lidar",
    "sensors",
    "aerospace",
    "electronics",
    "PCB",
    "embedded",
    "AI hardware",
]


def discover_crunchbase_companies(api_key: str | None = None) -> pd.DataFrame:
    key = api_key or os.getenv("CRUNCHBASE_API_KEY")
    if not key:
        print("[investment] CRUNCHBASE_API_KEY not set. Skipping Crunchbase source.")
        return pd.DataFrame()
    print("[investment] Crunchbase API key detected, but live API integration is not configured yet.")
    return pd.DataFrame()


def discover_yc_companies() -> pd.DataFrame:
    print("[investment] YC public source integration TODO. Skipping.")
    return pd.DataFrame()


def discover_sec_edgar_companies() -> pd.DataFrame:
    print("[investment] SEC EDGAR company profile enrichment TODO. Skipping.")
    return pd.DataFrame()


def discover_investment_companies() -> pd.DataFrame:
    frames = [
        discover_crunchbase_companies(),
        discover_yc_companies(),
        discover_sec_edgar_companies(),
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if "Last Checked At" not in result.columns:
        result["Last Checked At"] = utc_now_string()
    return result
