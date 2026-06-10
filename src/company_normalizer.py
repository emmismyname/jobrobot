from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
from rapidfuzz import fuzz


LEGAL_SUFFIX_PATTERN = re.compile(
    r"\b(incorporated|inc|llc|l\.l\.c|corporation|corp|co|company|ltd|limited|plc|lp|llp|gmbh|ag|sa|nv)\b\.?",
    re.IGNORECASE,
)


def normalize_company_name(name: object) -> str:
    if name is None or pd.isna(name):
        return ""
    text = str(name).casefold()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = LEGAL_SUFFIX_PATTERN.sub(" ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def choose_display_name(names: Iterable[object]) -> str:
    clean = [str(name).strip() for name in names if str(name).strip() and not pd.isna(name)]
    if not clean:
        return ""
    return sorted(clean, key=lambda value: (-len(value), value))[0]


def find_duplicate_candidates(
    companies: pd.DataFrame,
    threshold: int = 95,
    name_column: str = "Company Name",
) -> pd.DataFrame:
    rows = []
    names = [
        (idx, str(value), normalize_company_name(value))
        for idx, value in companies[name_column].fillna("").items()
        if str(value).strip()
    ]
    for left_pos, (left_idx, left_name, left_norm) in enumerate(names):
        if not left_norm:
            continue
        for right_idx, right_name, right_norm in names[left_pos + 1 :]:
            if not right_norm or left_norm == right_norm:
                continue
            score = fuzz.token_sort_ratio(left_norm, right_norm)
            if score > threshold:
                rows.append(
                    {
                        "left_index": left_idx,
                        "right_index": right_idx,
                        "left_company": left_name,
                        "right_company": right_name,
                        "left_normalized": left_norm,
                        "right_normalized": right_norm,
                        "similarity": score,
                    }
                )
    return pd.DataFrame(rows)
