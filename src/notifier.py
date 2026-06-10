from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from src.config import (
    MAX_COMPANY_EMAILS,
    MAX_EMAIL_JOBS,
    MIN_COMPANY_EMAIL_SCORE,
    MIN_EMAIL_SCORE,
)
from src.utils import get_env_value


def build_email_body(jobs: list[dict[str, Any]]) -> str:
    lines = ["New EE / Semiconductor job alerts found:", ""]
    for index, job in enumerate(jobs, start=1):
        source_type = str(job.get("source_type", ""))
        if source_type.startswith("official_"):
            source_label = "[OFFICIAL]"
        elif source_type in {"jobspy_indeed", "jobspy_linkedin"}:
            source_label = "[JOB BOARD]"
        elif source_type == "jobspy_google":
            source_label = "[GOOGLE]"
        else:
            source_label = "[SOURCE]"
        lines.extend(
            [
                f"{index}. {source_label} [{job.get('score', '')}] {job.get('title', '')}",
                f"   Company: {job.get('company', '')}",
                f"   Location: {job.get('location', '')}",
                f"   Source: {job.get('site', job.get('source', ''))}",
                f"   Source type: {source_type}",
                f"   URL: {job.get('job_url', '')}",
                f"   Search term: {job.get('search_term', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def send_job_alert(jobs: list[dict[str, Any]]) -> bool:
    jobs = [
        job
        for job in sorted(jobs, key=lambda item: item.get("score", 0), reverse=True)
        if job.get("score", 0) >= MIN_EMAIL_SCORE
    ][:MAX_EMAIL_JOBS]

    if not jobs:
        print(
            f"[notifier] No jobs at score >= {MIN_EMAIL_SCORE}. Email skipped."
        )
        return False

    email_address = get_env_value("EMAIL_ADDRESS")
    email_app_password = get_env_value("EMAIL_APP_PASSWORD")
    to_email = get_env_value("TO_EMAIL")

    missing = [
        name
        for name, value in [
            ("EMAIL_ADDRESS", email_address),
            ("EMAIL_APP_PASSWORD", email_app_password),
            ("TO_EMAIL", to_email),
        ]
        if not value
    ]
    if missing:
        print(
            "[notifier] Email skipped. Missing environment variables: "
            + ", ".join(missing)
        )
        return False

    message = EmailMessage()
    message["From"] = email_address
    message["To"] = to_email
    message["Subject"] = f"EE Job Alert: {len(jobs)} new jobs found"
    message.set_content(build_email_body(jobs))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_address, email_app_password)
        smtp.send_message(message)

    print(f"[notifier] Email sent to {to_email}: {len(jobs)} jobs.")
    return True


def build_company_discovery_email_body(companies: list[dict[str, Any]]) -> str:
    lines = [
        "New EE/ECE company leads found:",
        "",
        "Note: H-1B sponsor signal is based on public evidence and does not guarantee that a specific job sponsors visas.",
        "",
    ]
    for rank, company in enumerate(companies, start=1):
        lines.extend(
            [
                f"{rank}. [{company.get('overall_company_score', '')}] {company.get('Recommended Action', '')} - {company.get('Company Name', '')}",
                f"   H1B Sponsor Signal: {company.get('H1B Sponsor Signal', 'Unknown')}",
                f"   Industry Focus: {company.get('Industry Focus', '')}",
                f"   Locations / HQ: {company.get('Major Locations', company.get('Headquarters', ''))}",
                f"   Recent jobs found: {company.get('Recent jobs found', '')}",
                f"   Official Careers URL: {company.get('Official Careers URL', '')}",
                f"   Source: {company.get('Source', '')}",
                f"   Discovery Reason: {company.get('Discovery Reason', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def send_company_discovery_alert(companies: list[dict[str, Any]]) -> bool:
    companies = [
        company
        for company in sorted(
            companies,
            key=lambda item: item.get("overall_company_score", 0),
            reverse=True,
        )
        if company.get("overall_company_score", 0) >= MIN_COMPANY_EMAIL_SCORE
    ][:MAX_COMPANY_EMAILS]

    if not companies:
        print(
            f"[notifier] No companies at score >= {MIN_COMPANY_EMAIL_SCORE}. Email skipped."
        )
        return False

    email_address = get_env_value("EMAIL_ADDRESS")
    email_app_password = get_env_value("EMAIL_APP_PASSWORD")
    to_email = get_env_value("TO_EMAIL")

    missing = [
        name
        for name, value in [
            ("EMAIL_ADDRESS", email_address),
            ("EMAIL_APP_PASSWORD", email_app_password),
            ("TO_EMAIL", to_email),
        ]
        if not value
    ]
    if missing:
        print(
            "[notifier] Company discovery email skipped. Missing environment variables: "
            + ", ".join(missing)
        )
        return False

    message = EmailMessage()
    message["From"] = email_address
    message["To"] = to_email
    message["Subject"] = f"New EE/ECE Company Leads: {len(companies)} companies found"
    message.set_content(build_company_discovery_email_body(companies))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_address, email_app_password)
        smtp.send_message(message)

    print(f"[notifier] Company discovery email sent to {to_email}: {len(companies)} companies.")
    return True
