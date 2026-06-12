from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests


REQUEST_TIMEOUT_SECONDS = 20
WORKDAY_PAGE_LIMIT = int(os.getenv("WORKDAY_PAGE_LIMIT", "50"))
WORKDAY_MAX_PAGES = int(os.getenv("WORKDAY_MAX_PAGES", "3"))
WORKDAY_MAX_DETAILS = int(os.getenv("WORKDAY_MAX_DETAILS", "50"))


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _join_url(*parts: str) -> str:
    cleaned = []
    for part in parts:
        if not part:
            continue
        cleaned.append(str(part).strip("/"))
    if not cleaned:
        return ""
    first = cleaned[0]
    rest = cleaned[1:]
    return first + ("/" + "/".join(rest) if rest else "")


def _enabled(value: Any) -> bool:
    return _clean(value).casefold() in {"yes", "y", "true", "1", "enabled"}


def _location_from_greenhouse(job: dict[str, Any]) -> str:
    location = job.get("location") or {}
    return _clean(location.get("name"))


def _location_from_lever(job: dict[str, Any]) -> str:
    categories = job.get("categories") or {}
    parts = [
        _clean(categories.get("location")),
        _clean(categories.get("team")),
        _clean(categories.get("commitment")),
    ]
    return ", ".join(part for part in parts if part)


def _location_from_ashby(job: dict[str, Any]) -> str:
    location = job.get("location")
    if isinstance(location, dict):
        return _clean(location.get("name"))
    return _clean(location)


def scrape_greenhouse(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])

    return [
        {
            "title": _clean(job.get("title")),
            "company": company_name or slug,
            "location": _location_from_greenhouse(job),
            "source": "greenhouse",
            "job_url": _clean(job.get("absolute_url")),
            "description": _clean(job.get("content")),
            "search_term": f"official:{slug}",
            "source_type": "official_greenhouse",
        }
        for job in jobs
    ]


def scrape_lever(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json()

    return [
        {
            "title": _clean(job.get("text")),
            "company": company_name or slug,
            "location": _location_from_lever(job),
            "source": "lever",
            "job_url": _clean(job.get("hostedUrl") or job.get("applyUrl")),
            "description": _clean(job.get("descriptionPlain") or job.get("description")),
            "search_term": f"official:{slug}",
            "source_type": "official_lever",
        }
        for job in jobs
    ]


def scrape_ashby(company_slug: str, company_name: str | None = None) -> list[dict[str, Any]]:
    slug = _clean(company_slug)
    if not slug:
        return []

    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])

    return [
        {
            "title": _clean(job.get("title")),
            "company": company_name or slug,
            "location": _location_from_ashby(job),
            "source": "ashby",
            "job_url": _clean(job.get("jobUrl") or job.get("applyUrl")),
            "description": _clean(job.get("descriptionPlain") or job.get("description")),
            "search_term": f"official:{slug}",
            "source_type": "official_ashby",
        }
        for job in jobs
    ]


def parse_workday_config(company_config: dict[str, Any]) -> dict[str, str]:
    slug = _clean(company_config.get("ATS Company Slug"))
    search_url = _clean(company_config.get("Official Job Search URL"))
    parsed_search = urlparse(search_url) if search_url else None
    url_host = parsed_search.netloc if parsed_search else ""
    url_site = ""
    if parsed_search:
        parts = [part for part in parsed_search.path.split("/") if part]
        if "job" in parts:
            url_site = "/".join(parts[: parts.index("job")])
        elif parts:
            url_site = parts[0]

    if slug and "/" in slug:
        host, site = slug.split("/", 1)
    elif search_url:
        host = url_host
        site = url_site
    else:
        host = slug
        site = ""

    host = host.strip()
    site = site.strip("/")
    if url_host and url_host.casefold() == host.casefold() and url_site:
        if "/" in url_site and "/" not in site:
            site = url_site.strip("/")
    if not host:
        raise ValueError("Missing Workday host in ATS Company Slug or Official Job Search URL")
    if not site:
        raise ValueError("Missing Workday site in ATS Company Slug or Official Job Search URL")

    tenant = host.split(".")[0]
    return {
        "host": host,
        "tenant": tenant,
        "site": site,
        "base_url": f"https://{host}",
    }


def _workday_jobs_endpoint(parsed: dict[str, str]) -> str:
    return _join_url(
        parsed["base_url"],
        "wday/cxs",
        parsed["tenant"],
        parsed["site"],
        "jobs",
    )


def _workday_jobs_endpoint_for_site(parsed: dict[str, str], site: str) -> str:
    return _join_url(
        parsed["base_url"],
        "wday/cxs",
        parsed["tenant"],
        site,
        "jobs",
    )


def _workday_detail_endpoint(parsed: dict[str, str], external_path: str) -> str:
    return _join_url(
        parsed["base_url"],
        "wday/cxs",
        parsed["tenant"],
        parsed["site"],
        external_path,
    )


def _workday_public_url(parsed: dict[str, str], external_path: str) -> str:
    return _join_url(parsed["base_url"], parsed["site"], external_path)


def _workday_public_url_for_site(parsed: dict[str, str], site: str, external_path: str) -> str:
    return _join_url(parsed["base_url"], site, external_path)


def _workday_location(job: dict[str, Any]) -> str:
    if _clean(job.get("locationsText")):
        return _clean(job.get("locationsText"))
    locations = job.get("locations")
    if isinstance(locations, list):
        names = []
        for location in locations:
            if isinstance(location, dict):
                name = _clean(location.get("displayName") or location.get("name"))
            else:
                name = _clean(location)
            if name:
                names.append(name)
        return ", ".join(names)
    return _clean(job.get("location"))


def _workday_description(detail_json: dict[str, Any]) -> str:
    posting = detail_json.get("jobPostingInfo") or detail_json.get("jobPosting") or {}
    return _clean(
        posting.get("jobDescription")
        or posting.get("description")
        or posting.get("jobDescriptionText")
    )


def scrape_workday(
    company_config: dict[str, Any],
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    company_name = _clean(company_config.get("Company Name"))
    parsed = parse_workday_config(company_config)
    session = session or requests.Session()
    rows: list[dict[str, Any]] = []
    detail_count = 0

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "jobrobot/1.0 (+https://github.com/emmismyname/jobrobot)",
    }

    site_candidates = [parsed["site"]]
    if "/" in parsed["site"]:
        site_candidates.append(parsed["site"].split("/")[-1])

    for site in dict.fromkeys(site_candidates):
        rows = []
        detail_count = 0
        jobs_endpoint = _workday_jobs_endpoint_for_site(parsed, site)
        try:
            for page in range(WORKDAY_MAX_PAGES):
                offset = page * WORKDAY_PAGE_LIMIT
                payload = {
                    "appliedFacets": {},
                    "limit": WORKDAY_PAGE_LIMIT,
                    "offset": offset,
                    "searchText": "",
                }
                response = session.post(
                    jobs_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                if response.status_code == 405:
                    response = session.get(
                        jobs_endpoint,
                        params={"limit": WORKDAY_PAGE_LIMIT, "offset": offset},
                        headers=headers,
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                response.raise_for_status()
                data = response.json()
                postings = data.get("jobPostings") or data.get("jobs") or []
                if not postings:
                    break

                for job in postings:
                    external_path = _clean(
                        job.get("externalPath")
                        or job.get("url")
                        or job.get("jobUrl")
                        or job.get("externalUrl")
                    )
                    title = _clean(job.get("title"))
                    description = ""
                    if external_path and detail_count < WORKDAY_MAX_DETAILS:
                        try:
                            detail_response = session.get(
                                _workday_detail_endpoint(
                                    {**parsed, "site": site},
                                    external_path,
                                ),
                                headers=headers,
                                timeout=REQUEST_TIMEOUT_SECONDS,
                            )
                            detail_response.raise_for_status()
                            description = _workday_description(detail_response.json())
                            detail_count += 1
                        except Exception as exc:
                            print(f"[official] Workday detail skipped for {company_name} / {title}: {exc}")

                    rows.append(
                        {
                            "title": title,
                            "company": company_name or parsed["tenant"],
                            "location": _workday_location(job),
                            "source": "workday",
                            "job_url": _workday_public_url_for_site(parsed, site, external_path)
                            if external_path
                            else jobs_endpoint,
                            "description": description,
                            "search_term": f"official:{parsed['host']}/{site}",
                            "source_type": "official_workday",
                        }
                    )

                total = data.get("total")
                if isinstance(total, int) and offset + WORKDAY_PAGE_LIMIT >= total:
                    break
                if len(postings) < WORKDAY_PAGE_LIMIT:
                    break
            if rows:
                return rows
        except requests.HTTPError as exc:
            if site == site_candidates[-1]:
                raise
            print(f"[official] Workday site fallback for {company_name}: {site} failed ({exc})")
            continue

    return rows


def scrape_official_sources(company_db: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for company in company_db:
        if not _enabled(company.get("Use Official Scraper")):
            continue

        company_name = _clean(company.get("Company Name"))
        ats_type = _clean(company.get("ATS Type")).casefold()
        slug = _clean(company.get("ATS Company Slug"))
        if not ats_type or not slug:
            print(f"[official] Skipping {company_name}: missing ATS Type or ATS Company Slug")
            continue

        print(f"[official] Searching {company_name} via {ats_type} ({slug})")
        try:
            if ats_type == "greenhouse":
                jobs = scrape_greenhouse(slug, company_name)
            elif ats_type == "lever":
                jobs = scrape_lever(slug, company_name)
            elif ats_type == "ashby":
                jobs = scrape_ashby(slug, company_name)
            elif ats_type == "workday":
                jobs = scrape_workday(company)
            else:
                print(f"[official] Unsupported ATS Type for {company_name}: {ats_type}")
                jobs = []
        except Exception as exc:
            print(f"[official] Failed {company_name} via {ats_type}: {exc}")
            continue

        rows.extend(jobs)

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    print(f"[official] Total official jobs scraped: {len(frame)}")
    return frame
