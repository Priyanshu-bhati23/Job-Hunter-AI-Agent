# nodes/application_tracker.py
"""
Node 5: Application Tracker
Stores and exports application data to:
- Local CSV (always)
- Google Sheets (if configured)
- Notion Database (if configured)
"""

import os
import csv
from datetime import datetime, timedelta
from typing import List
from loguru import logger

import pandas as pd

from config.settings import (
    TRACKER_CSV_PATH, GOOGLE_SHEET_ID, GOOGLE_SHEETS_CREDS,
    NOTION_TOKEN, NOTION_DATABASE_ID, OUTPUT_DIR
)
from config.state import (
    AgentState, JobListing, ResumeVersion, CoverLetter, ApplicationRecord
)


# ─────────────────────────────────────────────
# 📊 CSV TRACKER
# ─────────────────────────────────────────────

TRACKER_COLUMNS = [
    "job_id", "company", "role", "location", "work_mode",
    "job_url", "match_score", "applied", "resume_version_id",
    "applied_date", "follow_up_date", "status", "source", "notes"
]


def save_to_csv(records: List[ApplicationRecord], jobs: List[JobListing]) -> str:
    """Save application records to CSV"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    job_map = {j.job_id: j for j in jobs}

    rows = []
    for rec in records:
        job = job_map.get(rec.job_id)
        rows.append({
            "job_id": rec.job_id,
            "company": rec.company,
            "role": rec.role,
            "location": rec.location,
            "work_mode": rec.work_mode,
            "job_url": rec.job_url,
            "match_score": f"{job.relevance_score:.1f}%" if job else "N/A",
            "applied": rec.applied,
            "resume_version_id": rec.resume_version_id,
            "applied_date": rec.applied_date or "",
            "follow_up_date": rec.follow_up_date or "",
            "status": rec.status,
            "source": job.source if job else "",
            "notes": rec.notes,
        })

    df = pd.DataFrame(rows, columns=TRACKER_COLUMNS)

    # Append to existing or create new
    if os.path.exists(TRACKER_CSV_PATH):
        existing = pd.read_csv(TRACKER_CSV_PATH)
        # Update existing entries, add new ones
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["job_id"], keep="last")
        combined.to_csv(TRACKER_CSV_PATH, index=False)
    else:
        df.to_csv(TRACKER_CSV_PATH, index=False)

    logger.info(f"✅ CSV tracker saved: {TRACKER_CSV_PATH}")
    return TRACKER_CSV_PATH


# ─────────────────────────────────────────────
# 📋 GOOGLE SHEETS TRACKER
# ─────────────────────────────────────────────

def sync_to_google_sheets(records: List[ApplicationRecord], jobs: List[JobListing]):
    """Sync application tracker to Google Sheets"""
    if not GOOGLE_SHEET_ID or not os.path.exists(GOOGLE_SHEETS_CREDS):
        logger.warning("Google Sheets not configured. Skipping.")
        return

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDS, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Applications")

        job_map = {j.job_id: j for j in jobs}

        # Get existing data to avoid duplicates
        existing = sheet.get_all_records()
        existing_ids = {row.get("job_id") for row in existing}

        rows_to_add = []
        for rec in records:
            if rec.job_id in existing_ids:
                continue
            job = job_map.get(rec.job_id)
            rows_to_add.append([
                rec.job_id, rec.company, rec.role, rec.location, rec.work_mode,
                rec.job_url, f"{job.relevance_score:.1f}%" if job else "N/A",
                "No", rec.resume_version_id, "", "", rec.status,
                job.source if job else "", "",
            ])

        if rows_to_add:
            sheet.append_rows(rows_to_add)
            logger.info(f"✅ Added {len(rows_to_add)} rows to Google Sheets")
        else:
            logger.info("No new rows to add to Google Sheets")

    except ImportError:
        logger.warning("gspread not installed. Run: pip install gspread google-auth")
    except Exception as e:
        logger.error(f"Google Sheets sync failed: {e}")


# ─────────────────────────────────────────────
# 📓 NOTION TRACKER
# ─────────────────────────────────────────────

def sync_to_notion(records: List[ApplicationRecord], jobs: List[JobListing]):
    """Add application records to a Notion database"""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        logger.warning("Notion not configured. Skipping.")
        return

    try:
        from notion_client import Client
        notion = Client(auth=NOTION_TOKEN)
        job_map = {j.job_id: j for j in jobs}

        for rec in records:
            job = job_map.get(rec.job_id)
            try:
                notion.pages.create(
                    parent={"database_id": NOTION_DATABASE_ID},
                    properties={
                        "Company": {"title": [{"text": {"content": rec.company}}]},
                        "Role": {"rich_text": [{"text": {"content": rec.role}}]},
                        "Status": {"select": {"name": rec.status}},
                        "Work Mode": {"select": {"name": rec.work_mode}},
                        "Job URL": {"url": rec.job_url},
                        "Match Score": {"number": job.relevance_score if job else 0},
                        "Applied": {"checkbox": rec.applied},
                        "Resume Version": {"rich_text": [{"text": {"content": rec.resume_version_id}}]},
                        "Source": {"rich_text": [{"text": {"content": job.source if job else ""}}]},
                    }
                )
            except Exception as e:
                logger.warning(f"Notion page creation failed for {rec.company}: {e}")

        logger.info(f"✅ Synced {len(records)} records to Notion")

    except ImportError:
        logger.warning("notion-client not installed. Run: pip install notion-client")
    except Exception as e:
        logger.error(f"Notion sync failed: {e}")


# ─────────────────────────────────────────────
# 📄 JOB OUTPUT REPORT
# ─────────────────────────────────────────────

def generate_output_report(
    jobs: List[JobListing],
    resume_versions: List[ResumeVersion],
    cover_letters: List[CoverLetter],
) -> str:
    """Generate a human-readable markdown report of all processed jobs"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = f"{OUTPUT_DIR}/job_hunt_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    rv_map = {rv.job_id: rv for rv in resume_versions}
    cl_map = {cl.job_id: cl for cl in cover_letters}

    lines = [
        "# 🤖 Job Hunter AI Agent — Run Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total qualifying jobs processed: {len(jobs)}",
        "",
        "---",
        "",
    ]

    for i, job in enumerate(jobs, 1):
        rv = rv_map.get(job.job_id)
        cl = cl_map.get(job.job_id)

        lines += [
            f"## Job {i}: {job.title}",
            "",
            "### 📋 Job Summary",
            f"- **Role:** {job.title}",
            f"- **Company:** {job.company}",
            f"- **Location:** {job.location}",
            f"- **Work Mode:** {job.work_mode}",
            f"- **Match Score:** {job.relevance_score:.1f}%",
            f"- **Source:** {job.source}",
            f"- **URL:** {job.job_url}",
            f"- **Required Skills:** {', '.join(job.required_skills[:8])}",
            "",
        ]

        if rv:
            lines += [
                "### 📝 Resume Changes",
                f"- **ATS Score:** {rv.ats_score:.1f}%",
                f"- **Version ID:** {rv.version_id}",
                f"- **Skills Reordered:** {', '.join(rv.skills_reordered[:5])}",
                f"- **Keywords Added:** {', '.join(rv.keywords_added) if rv.keywords_added else 'None needed'}",
                f"- **Bullets Modified:** {len(rv.bullets_modified)} project bullets rewritten",
                "",
            ]

        if cl:
            lines += [
                "### ✉️ Cover Letter",
                f"*({cl.word_count} words)*",
                "",
                cl.content,
                "",
            ]

        lines += ["---", ""]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"✅ Report saved: {report_path}")
    return report_path


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def application_tracker_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 5: Create and export application tracking records
    """
    logger.info("=" * 60)
    logger.info("📊 NODE 5: APPLICATION TRACKER STARTED")

    selected_jobs: List[JobListing] = state.get("selected_jobs", [])
    resume_versions: List[ResumeVersion] = state.get("resume_versions", [])
    cover_letters: List[CoverLetter] = state.get("cover_letters", [])

    rv_map = {rv.job_id: rv for rv in resume_versions}
    records: List[ApplicationRecord] = []

    today = datetime.now().strftime("%Y-%m-%d")
    follow_up = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

    for job in selected_jobs:
        rv = rv_map.get(job.job_id)
        record = ApplicationRecord(
            job_id=job.job_id,
            company=job.company,
            role=job.title,
            location=job.location,
            work_mode=job.work_mode,
            job_url=job.job_url,
            applied=False,
            resume_version_id=rv.version_id if rv else "",
            applied_date=None,
            follow_up_date=follow_up,
            status="Discovered",
            notes=f"Match: {job.relevance_score:.1f}% | ATS: {rv.ats_score:.1f}%" if rv else "",
        )
        records.append(record)

    # Export to CSV (always)
    csv_path = save_to_csv(records, selected_jobs)

    # Generate markdown report
    report_path = generate_output_report(selected_jobs, resume_versions, cover_letters)

    # Sync to Google Sheets (if configured)
    sync_to_google_sheets(records, selected_jobs)

    # Sync to Notion (if configured)
    sync_to_notion(records, selected_jobs)

    # Run summary
    state["application_records"] = records
    state["tracker_export_path"] = csv_path
    state["run_summary"] = {
        "total_discovered": len(state.get("raw_jobs", [])),
        "qualifying_jobs": len(selected_jobs),
        "resume_versions": len(resume_versions),
        "cover_letters": len(cover_letters),
        "csv_path": csv_path,
        "report_path": report_path,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"✅ Tracked {len(records)} applications")
    return state
