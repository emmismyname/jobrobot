from src.official_scrapers import parse_workday_config, scrape_workday


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, json, headers, timeout):
        self.posts.append((url, json))
        return FakeResponse(
            {
                "total": 1,
                "jobPostings": [
                    {
                        "title": "Electrical Engineer I",
                        "externalPath": "/job/Austin-TX/Electrical-Engineer-I_R1",
                        "locationsText": "Austin, TX",
                    }
                ],
            }
        )

    def get(self, url, headers, timeout):
        self.gets.append(url)
        return FakeResponse(
            {
                "jobPostingInfo": {
                    "jobDescription": "Entry level electrical engineering role."
                }
            }
        )


def test_parse_workday_config_from_slug():
    parsed = parse_workday_config(
        {
            "ATS Company Slug": "intel.wd1.myworkdayjobs.com/en-us/external",
            "Official Job Search URL": "",
        }
    )

    assert parsed["host"] == "intel.wd1.myworkdayjobs.com"
    assert parsed["tenant"] == "intel"
    assert parsed["site"] == "en-us/external"


def test_parse_workday_config_from_job_url():
    parsed = parse_workday_config(
        {
            "ATS Company Slug": "",
            "Official Job Search URL": "https://amat.wd1.myworkdayjobs.com/External/job/Santa-ClaraCA/Engineer_R1",
        }
    )

    assert parsed["host"] == "amat.wd1.myworkdayjobs.com"
    assert parsed["tenant"] == "amat"
    assert parsed["site"] == "External"


def test_parse_workday_config_prefers_full_site_from_job_url():
    parsed = parse_workday_config(
        {
            "ATS Company Slug": "intel.wd1.myworkdayjobs.com/en-us",
            "Official Job Search URL": "https://intel.wd1.myworkdayjobs.com/en-us/external/job/US-Arizona-Phoenix/Engineer_R1",
        }
    )

    assert parsed["site"] == "en-us/external"


def test_scrape_workday_normalizes_jobs(monkeypatch):
    monkeypatch.setattr("src.official_scrapers.WORKDAY_PAGE_LIMIT", 10)
    monkeypatch.setattr("src.official_scrapers.WORKDAY_MAX_PAGES", 1)
    monkeypatch.setattr("src.official_scrapers.WORKDAY_MAX_DETAILS", 10)
    session = FakeSession()

    jobs = scrape_workday(
        {
            "Company Name": "Acme Semi",
            "ATS Company Slug": "acme.wd1.myworkdayjobs.com/External",
        },
        session=session,
    )

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Electrical Engineer I"
    assert jobs[0]["company"] == "Acme Semi"
    assert jobs[0]["source_type"] == "official_workday"
    assert jobs[0]["location"] == "Austin, TX"
    assert "Entry level electrical" in jobs[0]["description"]
    assert session.posts[0][0] == "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/External/jobs"
