"""CLI entry point for fitness-agent."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

app = typer.Typer(
    name="fitness-agent",
    help="AI-powered personalized fitness planning system (V1)",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers: Rich display
# ---------------------------------------------------------------------------

def _display_plan(plan) -> None:  # type: ignore[no-untyped-def]
    """Render a WeeklyPlan with Rich formatting."""
    from fitness_agent.planner.models import WeeklyPlan
    assert isinstance(plan, WeeklyPlan)

    console.print()
    console.print(Panel.fit(
        f"[bold green]🏋️  {plan.user_name} 的周训练计划[/bold green]\n"
        f"目标: [cyan]{plan.goal.value}[/cyan]  |  "
        f"经验: [cyan]{plan.experience_level}[/cyan]",
        border_style="green",
    ))

    # --- Nutrition summary ---
    nut = plan.daily_nutrition
    nut_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    nut_table.add_column("Label", style="bold")
    nut_table.add_column("Value")
    nut_table.add_row("热量目标", f"{nut.calorie_target:.0f} kcal/day")
    nut_table.add_row("蛋白质", f"{nut.protein_g:.0f} g")
    nut_table.add_row("碳水化合物", f"{nut.carbs_g:.0f} g")
    nut_table.add_row("脂肪", f"{nut.fat_g:.0f} g")
    console.print(Panel(nut_table, title="[bold]📊 每日营养目标[/bold]", border_style="blue"))

    if nut.meal_suggestions:
        console.print("  [bold]推荐餐食:[/bold]")
        for meal in nut.meal_suggestions:
            console.print(f"    • {meal}")

    # --- Training days ---
    for day in plan.training_days:
        if day.pre_workout_meal:
            console.print(f"  [bold green]🍽 训练前：[/bold green][dim]{day.pre_workout_meal}[/dim]")

        ex_table = Table(
            "动作", "起始重量", "组数", "次数", "休息",
            box=box.SIMPLE_HEAD, show_header=True,
            header_style="bold cyan",
        )
        for ex in day.exercises:
            ex_table.add_row(
                f"[bold]{ex.exercise_name_zh}[/bold] ({ex.exercise_name})",
                ex.weight_hint or "—",
                str(ex.sets),
                str(ex.reps),
                f"{ex.rest_seconds}s",
            )
        day_header = (
            f"[bold yellow]{day.day_label}[/bold yellow]: {day.focus}  "
            f"[dim](约 {day.estimated_duration_minutes} 分钟)[/dim]"
        )
        if day.warmup_notes:
            day_header += f"\n  [dim]热身: {day.warmup_notes}[/dim]"
        console.print(Panel(ex_table, title=day_header, border_style="yellow"))
        if day.cooldown_notes:
            console.print(f"  [dim]放松: {day.cooldown_notes}[/dim]")
        if day.post_workout_meal:
            console.print(f"  [bold green]🍽 训练后：[/bold green][dim]{day.post_workout_meal}[/dim]")

    # --- Rest days ---
    if plan.rest_days:
        console.print(f"\n  [bold]休息日:[/bold] {', '.join(plan.rest_days)}")

    # --- 4-week overview ---
    if plan.four_week_overview:
        console.print(Panel(
            plan.four_week_overview,
            title="[bold]📅 4周训练规划[/bold]",
            border_style="cyan",
        ))

    # --- Coach notes ---
    if plan.coach_notes:
        console.print(Panel(
            plan.coach_notes,
            title="[bold]💬 教练建议[/bold]",
            border_style="magenta",
        ))

    console.print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def plan(
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="LLM provider (anthropic/openai/deepseek/qwen/gemini). "
             "Defaults to LLM_PROVIDER in .env",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Model name override. Defaults to LLM_MODEL in .env",
    ),
    profile_path: Optional[Path] = typer.Option(
        None,
        "--profile",
        help="Path to an existing profile JSON (skips onboarding Q&A).",
        exists=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Save the generated plan JSON to this path.",
    ),
) -> None:
    """
    Run onboarding Q&A (or load an existing profile) then generate a
    personalised weekly training + nutrition plan.
    """
    from fitness_agent.knowledge_base.loader import KnowledgeBase
    from fitness_agent.planner.agent import PlannerAgent
    from fitness_agent.user.onboarding import load_profile, run_onboarding, save_profile
    from fitness_agent.utils.config import DATA_DIR
    from fitness_agent.utils.llm_client import build_client, build_client_from_config

    # --- Build LLM client (needed for both onboarding parsing and plan generation) ---
    console.print("\n[dim]Initialising LLM client…[/dim]")
    try:
        if provider:
            client = build_client(provider=provider, model=model)
        else:
            client = build_client_from_config()
        console.print(f"[dim]Using {client}[/dim]")
    except ValueError as exc:
        console.print(f"[red]LLM configuration error:[/red] {exc}")
        raise typer.Exit(code=1)

    # --- Load or collect profile ---
    if profile_path and profile_path.exists():
        console.print(f"[dim]Loading profile from {profile_path}…[/dim]")
        user_profile = load_profile(profile_path)
        console.print(f"  欢迎回来，[bold]{user_profile.name}[/bold]！")
    else:
        user_profile = run_onboarding(
            ask_fn=lambda prompt: typer.prompt(prompt, prompt_suffix=" "),
            print_fn=console.print,
            llm_client=client,
        )
        # Auto-save profile for future reuse
        default_profile_path = DATA_DIR / "processed" / "profile.json"
        save_profile(user_profile, default_profile_path)
        console.print(f"\n[dim]Profile saved to {default_profile_path}[/dim]")

    # --- Generate plan ---
    console.print("\n[bold]正在生成训练计划，请稍候…[/bold]")
    try:
        kb = KnowledgeBase()  # warmup_templates and injury_profiles loaded from default paths
        agent = PlannerAgent(client=client, kb=kb)
        fitness_plan = agent.generate_plan(user_profile)
    except Exception as exc:
        console.print(f"[red]Plan generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    # --- Display ---
    _display_plan(fitness_plan)

    # --- Optionally save ---
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            fitness_plan.model_dump_json(indent=2),
            encoding="utf-8",
        )
        console.print(f"[dim]Plan saved to {output}[/dim]")


@app.command()
def version() -> None:
    """Show version."""
    from fitness_agent import __version__
    console.print(f"fitness-agent v{__version__}")


# Keep the old 'chat' alias pointing to 'plan' for backward compatibility
@app.command(hidden=True)
def chat() -> None:
    """Alias for 'plan' (deprecated)."""
    plan()


if __name__ == "__main__":
    app()
