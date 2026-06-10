from src.config import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS
from src.filters import is_relevant_job, score_job


def test_negative_keywords_filter_senior_job():
    row = {
        "title": "Senior Electrical Engineer",
        "company": "Intel",
        "location": "Austin, TX",
        "description": "Senior role requiring 8+ years of experience.",
        "job_url": "https://example.com/senior",
        "source_type": "jobspy_indeed",
    }

    assert not is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def test_new_grad_job_passes_filter():
    row = {
        "title": "Electrical Engineer New Grad",
        "company": "Texas Instruments",
        "location": "Dallas, TX",
        "description": "Entry level hardware role for new college graduates.",
        "job_url": "https://example.com/new-grad",
        "source_type": "jobspy_indeed",
    }

    assert is_relevant_job(row, ["Texas Instruments"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    assert score_job(row, ["Texas Instruments"], ["Dallas, TX"]) > 0


def test_process_engineer_iii_is_filtered_and_strongly_downgraded():
    row = {
        "title": "Process Engineer III",
        "company": "Applied Materials",
        "location": "Santa Clara, CA",
        "description": "Semiconductor process engineering role.",
        "job_url": "https://example.com/process-iii",
        "source_type": "jobspy_indeed",
    }

    assert score_job(row, ["Applied Materials"], ["Santa Clara, CA"]) < 0
    assert not is_relevant_job(row, ["Applied Materials"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def test_highway_project_engineer_is_filtered():
    row = {
        "title": "Highway Project Engineer",
        "company": "Dewberry",
        "location": "Bloomfield, NJ",
        "description": "Civil highway design project role for new graduates.",
        "job_url": "https://example.com/highway",
        "source_type": "jobspy_indeed",
    }

    assert not is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def test_postdoctoral_fellowship_is_filtered():
    row = {
        "title": "Postdoctoral Fellowship - Robotics and AI",
        "company": "Ludo Robotics",
        "location": "San Francisco, CA",
        "description": "Postdoc research fellowship requiring a PhD.",
        "job_url": "https://example.com/postdoc",
        "source_type": "jobspy_indeed",
    }

    assert not is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def test_electrical_development_without_entry_signal_or_target_company_is_downgraded():
    row = {
        "title": "Electrical Development Engineer",
        "company": "Ensign-Bickford Aerospace & Defense Company",
        "location": "Simsbury, CT",
        "description": "Electrical development role.",
        "job_url": "https://example.com/electrical-development",
        "source_type": "jobspy_indeed",
    }

    assert score_job(row, ["Intel"], ["Dallas, TX"]) < 6
    assert not is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)


def test_hardware_verification_new_college_graduate_passes():
    row = {
        "title": "Hardware Verification Engineer, New College Graduate",
        "company": "Teradyne",
        "location": "North Reading, MA",
        "description": "Hardware verification for new college graduates.",
        "job_url": "https://example.com/hw-verification",
        "source_type": "jobspy_indeed",
    }

    assert is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    assert score_job(row, ["Intel"], []) >= 6


def test_new_graduate_engineer_electrical_passes():
    row = {
        "title": "New Graduate Engineer, Electrical",
        "company": "SpaceX",
        "location": "Bastrop, TX",
        "description": "Electrical engineering launch and test role.",
        "job_url": "https://example.com/new-grad-electrical",
        "source_type": "jobspy_indeed",
    }

    assert is_relevant_job(row, ["Intel"], POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    assert score_job(row, ["Intel"], []) >= 6
