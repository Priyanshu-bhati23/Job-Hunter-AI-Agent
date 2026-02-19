# agent.py
"""
🤖 Job Hunter AI Agent — Main LangGraph Orchestrator

Workflow:
Job Discovery → Relevance Scoring → Resume Optimization → Cover Letters → Tracker

Run: python agent.py
"""

from datetime import date
from typing import Any
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from langgraph.graph import StateGraph, END

from config.state import AgentState
from config.settings import (
    SEARCH_QUERIES, ALL_SKILLS, CANDIDATE, MIN_RELEVANCE_SCORE
)
from nodes.job_discovery import job_discovery_node
from nodes.relevance_scoring import relevance_scoring_node
from nodes.resume_optimizer import resume_optimization_node
from nodes.cover_letter import cover_letter_node
from nodes.application_tracker import application_tracker_node
from utils.telegram_notifier import telegram_notification_node


console = Console()


# ─────────────────────────────────────────────
# 🔁 LANGGRAPH WORKFLOW DEFINITION
# ─────────────────────────────────────────────

def build_agent() -> StateGraph:
    """Build and compile the LangGraph state machine"""

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("job_discovery", job_discovery_node)
    workflow.add_node("relevance_scoring", relevance_scoring_node)
    workflow.add_node("resume_optimization", resume_optimization_node)
    workflow.add_node("cover_letter_generation", cover_letter_node)
    workflow.add_node("application_tracker", application_tracker_node)
    workflow.add_node("telegram_notifications", telegram_notification_node)

    # Define edges (sequential pipeline)
    workflow.set_entry_point("job_discovery")
    workflow.add_edge("job_discovery", "relevance_scoring")
    workflow.add_edge("relevance_scoring", "resume_optimization")
    workflow.add_edge("resume_optimization", "cover_letter_generation")
    workflow.add_edge("cover_letter_generation", "application_tracker")
    workflow.add_edge("application_tracker", "telegram_notifications")
    workflow.add_edge("telegram_notifications", END)

    return workflow.compile()


# ─────────────────────────────────────────────
# 🖥️ RICH CONSOLE OUTPUT
# ─────────────────────────────────────────────

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🤖 Job Hunter AI Agent[/bold cyan]\n"
        "[dim]ML / DL / GenAI / Agentic AI Roles[/dim]\n"
        "[yellow]Powered by LangGraph + LangChain[/yellow]",
        border_style="cyan",
        box=box.DOUBLE,
    ))


def print_summary(state: AgentState):
    summary = state.get("run_summary", {})
    errors = state.get("errors", [])

    console.print("\n")
    console.print(Panel(
        f"[bold green]✅ Run Complete![/bold green]\n\n"
        f"🔍 Jobs Discovered: [cyan]{summary.get('total_discovered', 0)}[/cyan]\n"
        f"🎯 Qualifying Jobs (≥{MIN_RELEVANCE_SCORE}%): [green]{summary.get('qualifying_jobs', 0)}[/green]\n"
        f"📄 Resume Versions: [blue]{summary.get('resume_versions', 0)}[/blue]\n"
        f"✉️  Cover Letters: [blue]{summary.get('cover_letters', 0)}[/blue]\n"
        f"📊 CSV Tracker: [dim]{summary.get('csv_path', 'N/A')}[/dim]\n"
        f"📋 Full Report: [dim]{summary.get('report_path', 'N/A')}[/dim]"
        + (f"\n⚠️ Errors: {len(errors)}" if errors else ""),
        title="[bold]Run Summary[/bold]",
        border_style="green",
    ))

    # Print jobs table
    jobs = state.get("selected_jobs", [])
    if jobs:
        table = Table(title="🎯 Selected Jobs", box=box.ROUNDED)
        table.add_column("#", style="dim", width=3)
        table.add_column("Company", style="cyan")
        table.add_column("Role", style="white")
        table.add_column("Mode", style="yellow")
        table.add_column("Score", style="green")
        table.add_column("Source", style="dim")

        for i, job in enumerate(jobs, 1):
            table.add_row(
                str(i),
                job.company[:25],
                job.title[:35],
                job.work_mode,
                f"{job.relevance_score:.1f}%",
                job.source,
            )

        console.print(table)


# ─────────────────────────────────────────────
# 🚀 MAIN ENTRY POINT
# ─────────────────────────────────────────────

def run_agent(custom_queries: list = None) -> dict:
    """Run the complete job hunting agent pipeline"""
    print_banner()

    # Initialize state
    initial_state: AgentState = {
        "search_queries": custom_queries or SEARCH_QUERIES,
        "candidate_skills": ALL_SKILLS,
        "available_from": CANDIDATE["available_from"],
        "raw_jobs": [],
        "filtered_jobs": [],
        "scored_jobs": [],
        "selected_jobs": [],
        "resume_versions": [],
        "cover_letters": [],
        "application_records": [],
        "tracker_export_path": "",
        "current_job_index": 0,
        "errors": [],
        "run_summary": {},
    }

    # Build and run agent
    agent = build_agent()

    console.print("\n[bold yellow]🚀 Starting job hunt pipeline...[/bold yellow]\n")

    try:
        final_state = agent.invoke(initial_state)
        print_summary(final_state)
        return final_state.get("run_summary", {})

    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        console.print(f"[bold red]❌ Agent failed: {e}[/bold red]")
        raise


# ─────────────────────────────────────────────
# 🕐 SCHEDULER (run daily)
# ─────────────────────────────────────────────

def run_scheduled():
    """Run agent on a schedule (3x daily)"""
    import schedule
    import time
    from rich.console import Console
    console = Console()

    def job():
        logger.info("⏰ Scheduled run starting...")
        try:
            run_agent()
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")

    # Run 3 times daily
    schedule.every().day.at("08:00").do(job)   # 8 AM
    schedule.every().day.at("13:00").do(job)   # 1 PM
    schedule.every().day.at("18:00").do(job)   # 6 PM

    console.print("\n[bold green]⏰ Scheduler Active![/bold green]")
    console.print("[cyan]Runs at: 8:00 AM | 1:00 PM | 6:00 PM daily[/cyan]")
    console.print("[yellow]Minimum match score: 60%[/yellow]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    # Run once immediately on start
    console.print("[bold]▶ Running now for the first time...[/bold]")
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys

    if "--schedule" in sys.argv:
        run_scheduled()
    else:
        run_agent()
