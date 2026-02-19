# cli.py
"""
Command-line interface for Job Hunter AI Agent
Usage:
  python cli.py run               # Full pipeline
  python cli.py search            # Discovery only
  python cli.py score             # Score cached jobs
  python cli.py status            # Show tracker
  python cli.py schedule          # Start scheduler
"""

import typer
from rich.console import Console
from loguru import logger

app = typer.Typer(help="🤖 Job Hunter AI Agent — ML/GenAI/Agentic AI roles")
console = Console()


@app.command()
def run(
    queries: list[str] = typer.Option(None, "--query", "-q", help="Custom search queries"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover jobs only, skip LLM steps"),
):
    """Run the full job hunting pipeline"""
    from agent import run_agent
    run_agent(custom_queries=queries if queries else None)


@app.command()
def status():
    """Show current application tracker status"""
    import pandas as pd
    from config.settings import TRACKER_CSV_PATH
    import os

    if not os.path.exists(TRACKER_CSV_PATH):
        console.print("[yellow]No tracker found. Run the agent first.[/yellow]")
        return

    df = pd.read_csv(TRACKER_CSV_PATH)
    console.print(f"\n[bold]📊 Application Tracker ({len(df)} entries)[/bold]\n")

    # Status breakdown
    status_counts = df["status"].value_counts()
    for status, count in status_counts.items():
        console.print(f"  {status}: [cyan]{count}[/cyan]")

    console.print(f"\n[dim]CSV: {TRACKER_CSV_PATH}[/dim]")


@app.command()
def schedule():
    """Start the scheduler (runs twice daily)"""
    from agent import run_scheduled
    run_scheduled()


@app.command()
def setup():
    """Interactive setup - configure .env file"""
    console.print("[bold cyan]🔧 Job Hunter AI Agent Setup[/bold cyan]\n")

    name = typer.prompt("Your full name")
    email = typer.prompt("Your email")
    phone = typer.prompt("Your phone number")
    linkedin = typer.prompt("LinkedIn URL")
    github = typer.prompt("GitHub URL")
    api_key = typer.prompt("OpenAI API Key (get at platform.openai.com/api-keys)")
    model = typer.prompt("OpenAI model", default="gpt-4o-mini")
    llm = "openai"

    env_content = f"""# Job Hunter AI Agent Configuration
CANDIDATE_NAME={name}
CANDIDATE_EMAIL={email}
CANDIDATE_PHONE={phone}
CANDIDATE_LINKEDIN={linkedin}
CANDIDATE_GITHUB={github}
CANDIDATE_LOCATION=India

# LLM Config
OPENAI_API_KEY={api_key}
OPENAI_MODEL={model}
LLM_PROVIDER={llm}
OLLAMA_MODEL=mistral

# Optional: Google Sheets
GOOGLE_SHEET_ID=
GOOGLE_SHEETS_CREDS_PATH=credentials.json

# Optional: Notion
NOTION_TOKEN=
NOTION_DATABASE_ID=
"""
    with open(".env", "w") as f:
        f.write(env_content)

    console.print("\n[green]✅ .env file created![/green]")
    console.print("[dim]Edit config/settings.py to customize your skills and preferences.[/dim]")
    console.print("\n[bold]Run the agent:[/bold] python cli.py run")


if __name__ == "__main__":
    app()
