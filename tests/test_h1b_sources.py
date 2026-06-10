import pandas as pd

from src.h1b_sources import filter_relevant_h1b_records, summarize_h1b_records


def test_h1b_relevant_records_are_filtered_and_summarized():
    records = pd.DataFrame(
        [
            {
                "EMPLOYER_NAME": "Texas Instruments Inc.",
                "JOB_TITLE": "Electrical Engineer",
                "SOC_CODE": "17-2071",
                "WORKSITE_STATE": "TX",
                "FISCAL_YEAR": 2025,
            },
            {
                "EMPLOYER_NAME": "Road Builder",
                "JOB_TITLE": "Restaurant Manager",
                "SOC_CODE": "11-9051",
                "WORKSITE_STATE": "TX",
                "FISCAL_YEAR": 2025,
            },
        ]
    )

    relevant = filter_relevant_h1b_records(records)
    summary = summarize_h1b_records(relevant)

    assert len(relevant) == 1
    assert summary.iloc[0]["Company Name"] == "Texas Instruments Inc."
    assert summary.iloc[0]["H1B Sponsor Signal"] == "Low"
