# utils/telegram_notifier.py
"""
Telegram Notification Node for Job Hunter AI Agent
Sends job alerts, resume summaries, and cover letters to your Telegram chat.

Setup:
1. Message @BotFather on Telegram → /newbot → get your BOT_TOKEN
2. Message your bot once, then visit:
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   to get your CHAT_ID
3. Add both to your .env file
"""

import os
import time
from typing import List, Optional
from loguru import logger

from config.settings import OUTPUT_DIR
from config.state import AgentState, JobListing, ResumeVersion, CoverLetter

# ─────────────────────────────────────────────
# 🔑 CONFIG (set in .env)
# ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ─────────────────────────────────────────────
# 📤 CORE SEND FUNCTIONS
# ─────────────────────────────────────────────

def _send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a text message to your Telegram chat"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    try:
        import requests
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text[:4096],  # Telegram message limit
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def _send_document(file_path: str, caption: str = "") -> bool:
    """Send a file (CSV, DOCX) to your Telegram chat"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        import requests
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{TELEGRAM_API}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]},
                files={"document": f},
                timeout=30,
            )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram document send failed: {e}")
        return False


# ─────────────────────────────────────────────
# 📨 MESSAGE TEMPLATES
# ─────────────────────────────────────────────

def _run_summary_message(state: AgentState) -> str:
    summary = state.get("run_summary", {})
    jobs = state.get("selected_jobs", [])
    import time

    lines = [
        "🤖 *Job Hunter AI Agent — New Jobs Found\\!*",
        "",
        f"🕐 Time: `{time.strftime('%d %b %Y, %I:%M %p')}`",
        f"🔍 Jobs Discovered: `{summary.get('total_discovered', 0)}`",
        f"🎯 Qualifying Jobs \\(≥60%\\): `{summary.get('qualifying_jobs', 0)}`",
        f"📄 Resumes Tailored: `{summary.get('resume_versions', 0)}`",
        f"✉️ Cover Letters: `{summary.get('cover_letters', 0)}`",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "*🏆 Top Matches:*",
        "",
    ]

    for i, job in enumerate(jobs[:5], 1):
        lines.append(
            f"{i}\\. *{job.title}* @ {job.company}\n"
            f"   📍 {job.location} | {job.work_mode}\n"
            f"   🎯 Match: `{job.relevance_score:.0f}%`\n"
            f"   🔗 [Apply Here]({job.job_url})\n"
        )

    if len(jobs) > 5:
        lines.append(f"_...and {len(jobs) - 5} more in your CSV tracker_")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "_Next run: 8AM | 1PM | 6PM daily_",
    ]

    return "\n".join(lines)


def _job_detail_message(
    job: JobListing,
    rv: Optional[ResumeVersion],
    cl: Optional[CoverLetter],
    index: int,
) -> str:
    """Detailed message for a single job"""
    lines = [
        f"📋 *Job #{index}: {job.title}*",
        "",
        f"🏢 *Company:* {job.company}",
        f"📍 *Location:* {job.location} \\({job.work_mode}\\)",
        f"🎯 *Match Score:* `{job.relevance_score:.1f}%`",
        f"🔗 *Apply:* [Click Here]({job.job_url})",
        f"🛠 *Skills Required:* {', '.join(job.required_skills[:6]) or 'See JD'}",
        "",
    ]

    if rv:
        lines += [
            "📄 *Resume Optimization:*",
            f"  • ATS Score: `{rv.ats_score:.1f}%`",
            f"  • Version: `{rv.version_id}`",
            f"  • Keywords Added: {', '.join(rv.keywords_added) or 'None needed'}",
            f"  • Skills Reordered: {', '.join(rv.skills_reordered[:4])}",
            "",
        ]

    if cl:
        lines += [
            "✉️ *Cover Letter Preview:*",
            "```",
            cl.content[:600] + ("..." if len(cl.content) > 600 else ""),
            "```",
        ]

    return "\n".join(lines)


def _no_jobs_message() -> str:
    return (
        "🤖 *Job Hunter AI Agent*\n\n"
        "😕 No qualifying jobs found in this run.\n\n"
        "Try:\n"
        "• Lowering `MIN_RELEVANCE_SCORE` in settings\n"
        "• Adding more search queries\n"
        "• Running again in a few hours\n\n"
        "_Agent will auto-retry on next scheduled run._"
    )


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def telegram_notification_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 6: Send Telegram notifications with job results
    """
    logger.info("=" * 60)
    logger.info("📱 NODE 6: TELEGRAM NOTIFICATIONS")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env")
        return state

    selected_jobs: List[JobListing] = state.get("selected_jobs", [])
    resume_versions: List[ResumeVersion] = state.get("resume_versions", [])
    cover_letters: List[CoverLetter] = state.get("cover_letters", [])

    rv_map = {rv.job_id: rv for rv in resume_versions}
    cl_map = {cl.job_id: cl for cl in cover_letters}

    # ── 1. Send run summary ──
    if not selected_jobs:
        _send_message(_no_jobs_message())
        logger.info("Sent: no jobs found message")
        return state

    summary_msg = _run_summary_message(state)
    _send_message(summary_msg)
    logger.info("✅ Sent run summary to Telegram")
    time.sleep(1)

    # ── 2. Send individual job details (top 5) ──
    for i, job in enumerate(selected_jobs[:5], 1):
        rv = rv_map.get(job.job_id)
        cl = cl_map.get(job.job_id)
        detail_msg = _job_detail_message(job, rv, cl, i)
        _send_message(detail_msg)
        logger.info(f"✅ Sent job #{i}: {job.title} @ {job.company}")
        time.sleep(1.5)  # Avoid Telegram rate limits

    # ── 3. Send CSV tracker file ──
    csv_path = state.get("tracker_export_path", "")
    if csv_path and os.path.exists(csv_path):
        _send_document(
            csv_path,
            caption=f"📊 Full Application Tracker — {len(selected_jobs)} jobs | {time.strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info("✅ Sent CSV tracker to Telegram")

    # ── 4. Send report markdown ──
    report_path = state.get("run_summary", {}).get("report_path", "")
    if report_path and os.path.exists(report_path):
        _send_document(
            report_path,
            caption="📋 Full Job Hunt Report with tailored resumes & cover letters"
        )
        logger.info("✅ Sent full report to Telegram")

    logger.info(f"📱 Telegram: all notifications sent!")
    return state


# ─────────────────────────────────────────────
# 🧪 TEST YOUR TELEGRAM SETUP
# ─────────────────────────────────────────────

def test_telegram():
    """Run this to verify your bot is working: python -c "from utils.telegram_notifier import test_telegram; test_telegram()" """
    print("Testing Telegram connection...")
    success = _send_message(
        "🤖 *Job Hunter AI Agent*\n\n"
        "✅ Telegram connected successfully\\!\n\n"
        "You'll receive job alerts here automatically.",
    )
    if success:
        print("✅ Message sent! Check your Telegram.")
    else:
        print("❌ Failed. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file")
        print("\nSetup guide:")
        print("1. Message @BotFather on Telegram → /newbot")
        print("2. Copy the bot token to TELEGRAM_BOT_TOKEN in .env")
        print("3. Start your bot, then visit:")
        print(f"   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
        print("4. Copy the 'id' field from the result to TELEGRAM_CHAT_ID in .env")
