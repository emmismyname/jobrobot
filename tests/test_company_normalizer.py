import pandas as pd

from src.company_normalizer import find_duplicate_candidates, normalize_company_name


def test_company_name_normalize_matches_legal_suffix():
    assert normalize_company_name("Texas Instruments Inc.") == normalize_company_name(
        "Texas Instruments"
    )


def test_fuzzy_duplicate_candidates_reports_close_names():
    companies = pd.DataFrame(
        {"Company Name": ["Texas Instruments Inc.", "Texas Instruments"]}
    )

    duplicates = find_duplicate_candidates(companies, threshold=95)

    assert len(duplicates) == 0
