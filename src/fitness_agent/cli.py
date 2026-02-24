"""CLI entry point for fitness-agent."""
import typer
from rich.console import Console

app = typer.Typer(
    name="fitness-agent",
    help="AI-powered personalized fitness planning system (V1)",
    add_completion=False,
)
console = Console()


@app.command()
def chat() -> None:
    """Start an interactive onboarding session to generate a fitness plan."""
    console.print("[bold orange1]fitness-agent V1[/bold orange1] — Personalized Fitness Planning")
    console.print("(not yet implemented)")


@app.command()
def version() -> None:
    """Show version."""
    from fitness_agent import __version__
    console.print(f"fitness-agent v{__version__}")


if __name__ == "__main__":
    app()
