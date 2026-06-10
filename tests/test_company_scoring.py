from src.company_scoring import score_company


def test_h1b_high_sponsor_scores_above_unknown():
    high = score_company(
        {
            "Company Name": "Micron",
            "H1B Sponsor Signal": "High",
            "Industry Focus": "Semiconductor",
            "Target Role Family": "Hardware Engineering",
            "Major Locations": "Boise, ID",
        }
    )
    unknown = score_company(
        {
            "Company Name": "Unknown Co",
            "H1B Sponsor Signal": "Unknown",
            "Industry Focus": "Semiconductor",
            "Target Role Family": "Hardware Engineering",
            "Major Locations": "Boise, ID",
        }
    )

    assert high["overall_company_score"] > unknown["overall_company_score"]


def test_semiconductor_and_medical_device_score_above_civil():
    semi = score_company({"Industry Focus": "Semiconductor", "Target Role Family": "Hardware"})
    med = score_company({"Industry Focus": "Medical Device / Diagnostics", "Target Role Family": "Quality"})
    civil = score_company({"Industry Focus": "Civil / Construction only", "Target Role Family": "Civil"})

    assert semi["industry_fit_score"] > civil["industry_fit_score"]
    assert med["industry_fit_score"] > civil["industry_fit_score"]


def test_official_ats_source_scores_above_job_board_only():
    official = score_company(
        {
            "Source": "official_greenhouse",
            "Official Careers URL": "https://example.com/careers",
        }
    )
    job_board = score_company({"Source": "job board only indeed"})

    assert official["source_confidence_score"] > job_board["source_confidence_score"]
