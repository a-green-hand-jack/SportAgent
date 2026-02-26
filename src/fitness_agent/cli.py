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
# Helpers: Rich display — Cooking Plan
# ---------------------------------------------------------------------------

def _display_cooking_plan(plan) -> None:  # type: ignore[no-untyped-def]
    """Render a WeeklyCookingPlan with Rich formatting."""
    from fitness_agent.cooking.models import WeeklyCookingPlan
    assert isinstance(plan, WeeklyCookingPlan)

    console.print()
    compliant = sum(1 for d in plan.daily_plans if abs(d.calorie_deviation_pct) <= 10.0)
    console.print(Panel.fit(
        f"[bold green]🍳 {plan.user_name} 的周饮食计划[/bold green]\n"
        f"热量达标: [cyan]{compliant}/7 天[/cyan]  |  "
        f"采购项: [cyan]{len(plan.shopping_list)}[/cyan]",
        border_style="green",
    ))

    # --- Daily meal plans ---
    for day in plan.daily_plans:
        day_type = "[bold red]训练日[/bold red]" if day.is_training_day else "[bold blue]休息日[/bold blue]"
        dev = day.calorie_deviation_pct
        dev_color = "green" if abs(dev) <= 10 else "red"
        dev_str = f"[{dev_color}]{dev:+.1f}%[/{dev_color}]"

        meal_table = Table(
            "餐食", "菜品", "热量", "蛋白质", "时间",
            box=box.SIMPLE_HEAD, show_header=True,
            header_style="bold cyan",
        )
        for recipe in day.meals:
            meal_table.add_row(
                recipe.meal_type,
                f"[bold]{recipe.name_zh}[/bold]",
                f"{recipe.per_serving_macros.calories:.0f} kcal",
                f"{recipe.per_serving_macros.protein_g:.0f} g",
                f"{recipe.prep_time_minutes}+{recipe.cook_time_minutes}min",
            )

        day_header = (
            f"[bold yellow]{day.day_label}[/bold yellow] {day_type}  "
            f"总热量: {day.day_total_macros.calories:.0f} kcal (偏差 {dev_str})"
        )
        console.print(Panel(meal_table, title=day_header, border_style="yellow"))

    # --- Shopping list ---
    if plan.shopping_list:
        shop_table = Table(
            "食材", "用量(g)", "分类",
            box=box.SIMPLE_HEAD, show_header=True,
            header_style="bold cyan",
        )
        for item in plan.shopping_list:
            shop_table.add_row(
                item.food_name_zh,
                f"{item.total_amount_g:.0f}",
                item.category,
            )
        console.print(Panel(shop_table, title="[bold]🛒 周采购清单[/bold]", border_style="blue"))

    # --- Meal prep suggestions ---
    if plan.meal_prep_suggestions:
        prep_lines = []
        for s in plan.meal_prep_suggestions:
            prep_lines.append(
                f"• **{s.recipe_name_zh}**：{s.prep_day}准备 → {', '.join(s.covers_days)}\n"
                f"  储存: {s.storage_zh} | 加热: {s.reheat_zh}"
            )
        console.print(Panel(
            "\n".join(prep_lines),
            title="[bold]📦 备餐建议[/bold]",
            border_style="cyan",
        ))

    # --- Cooking tips ---
    if plan.cooking_tips_zh:
        console.print(Panel(
            plan.cooking_tips_zh,
            title="[bold]💡 烹饪提示[/bold]",
            border_style="magenta",
        ))

    console.print()


# ---------------------------------------------------------------------------
# Helpers: Markdown export
# ---------------------------------------------------------------------------

def _plan_to_markdown(plan) -> str:  # type: ignore[no-untyped-def]
    """Convert a WeeklyPlan to a human-readable Markdown string."""
    lines: list[str] = []

    # --- Title ---
    lines.append(f"# 🏋️ {plan.user_name} 的周训练计划\n")
    lines.append(f"**目标**: {plan.goal.value}  |  **经验等级**: {plan.experience_level}\n")

    # --- Nutrition ---
    nut = plan.daily_nutrition
    lines.append("---\n")
    lines.append("## 📊 每日营养目标\n")
    lines.append(f"| 指标 | 目标 |")
    lines.append(f"|------|------|")
    lines.append(f"| 热量 | {nut.calorie_target:.0f} kcal |")
    lines.append(f"| 蛋白质 | {nut.protein_g:.0f} g |")
    lines.append(f"| 碳水化合物 | {nut.carbs_g:.0f} g |")
    lines.append(f"| 脂肪 | {nut.fat_g:.0f} g |")
    lines.append("")
    if nut.meal_suggestions:
        lines.append("**推荐餐食:**\n")
        for meal in nut.meal_suggestions:
            lines.append(f"- {meal}")
        lines.append("")
    if nut.supplements:
        lines.append("**补剂建议:**\n")
        for sup in nut.supplements:
            lines.append(f"- {sup}")
        lines.append("")

    # --- Training days ---
    lines.append("---\n")
    lines.append("## 🗓 训练安排\n")
    for day in plan.training_days:
        lines.append(f"### {day.day_label}：{day.focus}（约 {day.estimated_duration_minutes} 分钟）\n")
        if day.warmup_notes:
            lines.append(f"**热身:** {day.warmup_notes}\n")
        if day.pre_workout_meal:
            lines.append(f"**训练前饮食:** {day.pre_workout_meal}\n")
        lines.append("| 动作 | 起始重量 | 组数 | 次数 | 休息 |")
        lines.append("|------|---------|------|------|------|")
        for ex in day.exercises:
            name = f"{ex.exercise_name_zh}（{ex.exercise_name}）"
            weight = ex.weight_hint or "—"
            note = f" *{ex.notes}*" if ex.notes else ""
            lines.append(f"| {name}{note} | {weight} | {ex.sets} | {ex.reps} | {ex.rest_seconds}s |")
        lines.append("")
        if day.cooldown_notes:
            lines.append(f"**放松:** {day.cooldown_notes}\n")
        if day.post_workout_meal:
            lines.append(f"**训练后饮食:** {day.post_workout_meal}\n")

    # --- Rest days ---
    if plan.rest_days:
        lines.append(f"**休息日:** {', '.join(plan.rest_days)}\n")

    # --- 4-week overview ---
    if plan.four_week_overview:
        lines.append("---\n")
        lines.append("## 📅 4周训练规划\n")
        lines.append(plan.four_week_overview)
        lines.append("")

    # --- Coach notes ---
    if plan.coach_notes:
        lines.append("---\n")
        lines.append("## 💬 教练建议\n")
        lines.append(plan.coach_notes)
        lines.append("")

    return "\n".join(lines)


def _display_gym_plan(plan) -> None:  # type: ignore[no-untyped-def]
    """Render a WeeklyGymPlan with Rich formatting."""
    from fitness_agent.gym.models import WeeklyGymPlan
    assert isinstance(plan, WeeklyGymPlan)

    console.print()
    console.print(Panel.fit(
        f"[bold green]💪 {plan.user_name} 的训练执行指导[/bold green]\n"
        f"训练日: [cyan]{len(plan.sessions)}[/cyan]  |  "
        f"总动作: [cyan]{sum(len(s.exercises) for s in plan.sessions)}[/cyan]  |  "
        f"器材: [cyan]{len(plan.equipment_checklist)}[/cyan]",
        border_style="green",
    ))

    # --- Sessions ---
    for session in plan.sessions:
        # Exercise table
        ex_table = Table(
            "动作", "组×次", "休息", "起始重量", "节奏",
            box=box.SIMPLE_HEAD, show_header=True,
            header_style="bold cyan",
        )
        for ex in session.exercises:
            tempo = ex.tempo_zh or "—"
            ex_table.add_row(
                f"[bold]{ex.exercise_name_zh}[/bold]",
                f"{ex.sets}×{ex.reps}",
                f"{ex.rest_seconds}s",
                ex.starting_weight_zh,
                tempo,
            )

        day_header = (
            f"[bold yellow]{session.day_label}[/bold yellow]: {session.focus}  "
            f"[dim](约 {session.estimated_duration_minutes} 分钟)[/dim]"
        )
        console.print(Panel(ex_table, title=day_header, border_style="yellow"))

        # Warmup
        if session.warmup_sequence:
            warmup_text = "\n".join(session.warmup_sequence)
            console.print(f"  [bold green]🔥 热身:[/bold green]")
            for step in session.warmup_sequence:
                console.print(f"    {step}")
            if session.warmup_injury_modifications:
                for tag, mod in session.warmup_injury_modifications.items():
                    console.print(f"    [red]⚠ {tag}:[/red] {mod}")

        # Exercise details
        for ex in session.exercises:
            console.print(f"\n  [bold]{ex.exercise_name_zh}[/bold] ({ex.exercise_id})")
            if ex.kb_cues:
                console.print(f"    [dim]KB Cues: {' | '.join(ex.kb_cues)}[/dim]")
            for tip in ex.coaching_tips_zh:
                console.print(f"    [cyan]💡 {tip}[/cyan]")
            console.print(f"    [blue]🫁 呼吸: {ex.breathing_zh}[/blue]")
            for mistake in ex.common_mistakes_zh:
                console.print(f"    [red]❌ {mistake}[/red]")
            if ex.injury_adaptations_zh:
                console.print(f"    [yellow]⚠ 伤病适配: {ex.injury_adaptations_zh}[/yellow]")

        # Cooldown
        if session.cooldown_sequence:
            console.print(f"\n  [bold blue]🧊 拉伸:[/bold blue]")
            for step in session.cooldown_sequence:
                console.print(f"    {step}")

        # Session flow notes
        if session.session_flow_notes_zh:
            console.print(f"\n  [dim]📋 {session.session_flow_notes_zh}[/dim]")

    # --- 4-week progression ---
    prog_table = Table(
        "周", "主题", "训练量", "强度", "RPE",
        box=box.SIMPLE_HEAD, show_header=True,
        header_style="bold cyan",
    )
    for pw in plan.four_week_progression:
        prog_table.add_row(
            f"第{pw.week_number}周",
            pw.theme_zh,
            pw.volume_change_zh,
            pw.intensity_change_zh,
            pw.rpe_target,
        )
    console.print(Panel(prog_table, title="[bold]📅 4周渐进计划[/bold]", border_style="cyan"))

    # --- Equipment checklist ---
    if plan.equipment_checklist:
        equip_str = "、".join(plan.equipment_checklist)
        console.print(f"\n  [bold]🏗 所需器材:[/bold] {equip_str}")

    # --- General tips ---
    if plan.general_tips_zh:
        console.print(Panel(
            plan.general_tips_zh,
            title="[bold]💬 通用训练建议[/bold]",
            border_style="magenta",
        ))

    console.print()


def _gym_plan_to_markdown(plan) -> str:  # type: ignore[no-untyped-def]
    """Convert a WeeklyGymPlan to a human-readable Markdown string."""
    lines: list[str] = []

    lines.append(f"# 💪 {plan.user_name} 的训练执行指导\n")
    lines.append(
        f"**训练日**: {len(plan.sessions)}  |  "
        f"**总动作**: {sum(len(s.exercises) for s in plan.sessions)}  |  "
        f"**器材**: {', '.join(plan.equipment_checklist) if plan.equipment_checklist else '无'}\n"
    )

    # --- Sessions ---
    for session in plan.sessions:
        lines.append("---\n")
        lines.append(
            f"## {session.day_label}：{session.focus}"
            f"（约 {session.estimated_duration_minutes} 分钟）\n"
        )

        # Warmup
        if session.warmup_sequence:
            lines.append("### 🔥 热身\n")
            for step in session.warmup_sequence:
                lines.append(f"- {step}")
            if session.warmup_injury_modifications:
                lines.append("\n**伤病调整:**\n")
                for tag, mod in session.warmup_injury_modifications.items():
                    lines.append(f"- ⚠ {tag}: {mod}")
            lines.append("")

        # Exercise table
        lines.append("### 训练动作\n")
        lines.append("| 动作 | 组×次 | 休息 | 起始重量 | 节奏 |")
        lines.append("|------|-------|------|---------|------|")
        for ex in session.exercises:
            tempo = ex.tempo_zh or "—"
            lines.append(
                f"| {ex.exercise_name_zh} | {ex.sets}×{ex.reps} | "
                f"{ex.rest_seconds}s | {ex.starting_weight_zh} | {tempo} |"
            )
        lines.append("")

        # Exercise details
        for ex in session.exercises:
            lines.append(f"#### {ex.exercise_name_zh}（{ex.exercise_name}）\n")
            if ex.primary_muscles:
                lines.append(f"- **主要肌群**: {', '.join(ex.primary_muscles)}")
            if ex.kb_cues:
                lines.append(f"- **KB Cues**: {' | '.join(ex.kb_cues)}")
            lines.append(f"- **呼吸**: {ex.breathing_zh}")
            lines.append("- **教练提示**:")
            for tip in ex.coaching_tips_zh:
                lines.append(f"  - 💡 {tip}")
            lines.append("- **常见错误**:")
            for mistake in ex.common_mistakes_zh:
                lines.append(f"  - ❌ {mistake}")
            if ex.injury_adaptations_zh:
                lines.append(f"- **⚠ 伤病适配**: {ex.injury_adaptations_zh}")
            if ex.video_url:
                lines.append(f"- **教学视频**: [{ex.video_url}]({ex.video_url})")
            lines.append("")

        # Cooldown
        if session.cooldown_sequence:
            lines.append("### 🧊 拉伸\n")
            for step in session.cooldown_sequence:
                lines.append(f"- {step}")
            lines.append("")

        # Session notes
        if session.session_flow_notes_zh:
            lines.append(f"> 📋 {session.session_flow_notes_zh}\n")

    # --- 4-week progression ---
    lines.append("---\n")
    lines.append("## 📅 4周渐进计划\n")
    lines.append("| 周 | 主题 | 训练量 | 强度 | RPE | 备注 |")
    lines.append("|---|----|-------|------|-----|------|")
    for pw in plan.four_week_progression:
        lines.append(
            f"| 第{pw.week_number}周 | {pw.theme_zh} | {pw.volume_change_zh} | "
            f"{pw.intensity_change_zh} | {pw.rpe_target} | {pw.notes_zh} |"
        )
    lines.append("")

    # --- General tips ---
    if plan.general_tips_zh:
        lines.append("---\n")
        lines.append("## 💬 通用训练建议\n")
        lines.append(plan.general_tips_zh)
        lines.append("")

    return "\n".join(lines)


def _cooking_plan_to_markdown(plan) -> str:  # type: ignore[no-untyped-def]
    """Convert a WeeklyCookingPlan to a human-readable Markdown string."""
    lines: list[str] = []

    lines.append(f"# 🍳 {plan.user_name} 的周饮食计划\n")
    compliant = sum(1 for d in plan.daily_plans if abs(d.calorie_deviation_pct) <= 10.0)
    lines.append(f"**热量达标**: {compliant}/7 天  |  **采购项**: {len(plan.shopping_list)}\n")

    # --- Daily plans ---
    for day in plan.daily_plans:
        day_type = "训练日" if day.is_training_day else "休息日"
        dev = day.calorie_deviation_pct
        lines.append(f"---\n")
        lines.append(
            f"## {day.day_label}（{day_type}）— "
            f"{day.day_total_macros.calories:.0f} kcal（偏差 {dev:+.1f}%）\n"
        )
        lines.append("| 餐食 | 菜品 | 热量 | 蛋白质 | 准备时间 |")
        lines.append("|------|------|------|--------|---------|")
        for recipe in day.meals:
            lines.append(
                f"| {recipe.meal_type} | {recipe.name_zh} | "
                f"{recipe.per_serving_macros.calories:.0f} kcal | "
                f"{recipe.per_serving_macros.protein_g:.0f} g | "
                f"{recipe.prep_time_minutes}+{recipe.cook_time_minutes}min |"
            )
        lines.append("")

        # Detailed recipes
        for recipe in day.meals:
            lines.append(f"### {recipe.name_zh}\n")
            lines.append("**食材:**\n")
            for ing in recipe.ingredients:
                note = f" ({ing.note})" if ing.note else ""
                lines.append(f"- {ing.food_name_zh} {ing.amount_g:.0f}g{note}")
            lines.append("")
            lines.append("**步骤:**\n")
            for i, step in enumerate(recipe.steps_zh, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

    # --- Shopping list ---
    if plan.shopping_list:
        lines.append("---\n")
        lines.append("## 🛒 周采购清单\n")
        lines.append("| 食材 | 用量(g) | 分类 |")
        lines.append("|------|---------|------|")
        for item in plan.shopping_list:
            lines.append(f"| {item.food_name_zh} | {item.total_amount_g:.0f} | {item.category} |")
        lines.append("")

    # --- Meal prep ---
    if plan.meal_prep_suggestions:
        lines.append("---\n")
        lines.append("## 📦 备餐建议\n")
        for s in plan.meal_prep_suggestions:
            lines.append(
                f"- **{s.recipe_name_zh}**：{s.prep_day}准备 → "
                f"{', '.join(s.covers_days)}（储存: {s.storage_zh}，加热: {s.reheat_zh}）"
            )
        lines.append("")

    # --- Tips ---
    if plan.cooking_tips_zh:
        lines.append("---\n")
        lines.append("## 💡 烹饪提示\n")
        lines.append(plan.cooking_tips_zh)
        lines.append("")

    return "\n".join(lines)


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
        help="Save the generated plan JSON to this path (default: data/processed/plan.json).",
    ),
    cook_flag: bool = typer.Option(
        False,
        "--cook",
        help="Also generate a detailed weekly cooking plan after the training plan.",
    ),
    gym_flag: bool = typer.Option(
        False,
        "--gym",
        help="Also generate detailed gym exercise guidance after the training plan.",
    ),
) -> None:
    """
    Run onboarding Q&A (or load an existing profile) then generate a
    personalised weekly training + nutrition plan.
    """
    from fitness_agent.user.onboarding import load_profile, save_profile
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
        from fitness_agent.entrance.agent import EntranceAgent

        entrance_agent = EntranceAgent(client=client)
        user_profile = entrance_agent.run(
            ask_fn=lambda _: typer.prompt("", prompt_suffix=""),
            print_fn=console.print,
            should_cook=cook_flag,
            should_gym=gym_flag,
        )
        # Auto-save profile for future reuse
        default_profile_path = DATA_DIR / "processed" / "profile.json"
        save_profile(user_profile, default_profile_path)
        console.print(f"\n[dim]Profile saved to {default_profile_path}[/dim]")

    # --- Generate plan via LangGraph ---
    console.print("\n[bold]正在生成训练计划，请稍候…[/bold]")
    try:
        from fitness_agent.graph import build_fitness_graph, FitnessAgentState

        graph = build_fitness_graph()
        initial_state: FitnessAgentState = {
            "user_profile": user_profile.model_dump(),
            "provider": client.provider,
            "model": client.model,
            "should_cook": cook_flag,
            "should_gym": gym_flag,
            "errors": [],
        }
        result = graph.invoke(initial_state)
    except Exception as exc:
        console.print(f"[red]Plan generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    # --- Extract results from graph state ---
    from fitness_agent.planner.models import WeeklyPlan
    if "weekly_plan" not in result:
        console.print("[red]Plan generation failed: no weekly_plan in graph state.[/red]")
        raise typer.Exit(code=1)

    fitness_plan = WeeklyPlan.model_validate(result["weekly_plan"])

    # --- Display ---
    _display_plan(fitness_plan)

    # --- Save plan (JSON + Markdown) ---
    save_path = output if output else DATA_DIR / "processed" / "plan.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(
        fitness_plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path = save_path.with_suffix(".md")
    md_path.write_text(_plan_to_markdown(fitness_plan), encoding="utf-8")
    console.print(f"[dim]Plan saved to {save_path} and {md_path}[/dim]")

    # --- Display cooking plan if generated ---
    if cook_flag and "cooking_plan" in result:
        from fitness_agent.cooking.models import WeeklyCookingPlan
        cooking_plan = WeeklyCookingPlan.model_validate(result["cooking_plan"])
        _display_cooking_plan(cooking_plan)
        cook_path = save_path.with_name("cooking_plan.json")
        cook_path.parent.mkdir(parents=True, exist_ok=True)
        cook_path.write_text(cooking_plan.model_dump_json(indent=2), encoding="utf-8")
        cook_md_path = cook_path.with_suffix(".md")
        cook_md_path.write_text(_cooking_plan_to_markdown(cooking_plan), encoding="utf-8")
        console.print(f"[dim]Cooking plan saved to {cook_path} and {cook_md_path}[/dim]")

    # --- Display gym plan if generated ---
    if gym_flag and "gym_plan" in result:
        from fitness_agent.gym.models import WeeklyGymPlan
        gym_plan = WeeklyGymPlan.model_validate(result["gym_plan"])
        _display_gym_plan(gym_plan)
        gym_path = save_path.with_name("gym_plan.json")
        gym_path.parent.mkdir(parents=True, exist_ok=True)
        gym_path.write_text(gym_plan.model_dump_json(indent=2), encoding="utf-8")
        gym_md_path = gym_path.with_suffix(".md")
        gym_md_path.write_text(_gym_plan_to_markdown(gym_plan), encoding="utf-8")
        console.print(f"[dim]Gym plan saved to {gym_path} and {gym_md_path}[/dim]")


def _run_cooking_plan(
    client: object,
    fitness_plan: object,
    user_profile: object,
    save_path: Path,
) -> None:
    """Shared cooking plan generation logic used by both `plan --cook` and `cook`."""
    from fitness_agent.cooking.agent import CookingAgent
    from fitness_agent.knowledge_base.loader import KnowledgeBase

    console.print("\n[bold]正在生成详细饮食计划，请稍候…[/bold]")
    try:
        kb = KnowledgeBase()
        cooking_agent = CookingAgent(client=client, kb=kb)  # type: ignore[arg-type]
        cooking_plan = cooking_agent.generate_cooking_plan(
            fitness_plan, user_profile  # type: ignore[arg-type]
        )
    except Exception as exc:
        console.print(f"[red]Cooking plan generation failed:[/red] {exc}")
        return

    _display_cooking_plan(cooking_plan)

    cook_path = save_path.with_name("cooking_plan.json")
    cook_path.parent.mkdir(parents=True, exist_ok=True)
    cook_path.write_text(
        cooking_plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    cook_md_path = cook_path.with_suffix(".md")
    cook_md_path.write_text(
        _cooking_plan_to_markdown(cooking_plan),
        encoding="utf-8",
    )
    console.print(f"[dim]Cooking plan saved to {cook_path} and {cook_md_path}[/dim]")


def _run_gym_plan(
    client: object,
    fitness_plan: object,
    user_profile: object,
    save_path: Path,
) -> None:
    """Shared gym plan generation logic used by both `plan --gym` and `gym`."""
    from fitness_agent.gym.agent import GYMAgent
    from fitness_agent.knowledge_base.loader import KnowledgeBase

    console.print("\n[bold]正在生成训练执行指导，请稍候…[/bold]")
    try:
        kb = KnowledgeBase()
        gym_agent = GYMAgent(client=client, kb=kb)  # type: ignore[arg-type]
        gym_plan = gym_agent.generate_gym_plan(
            fitness_plan, user_profile  # type: ignore[arg-type]
        )
    except Exception as exc:
        console.print(f"[red]Gym plan generation failed:[/red] {exc}")
        return

    _display_gym_plan(gym_plan)

    gym_path = save_path.with_name("gym_plan.json")
    gym_path.parent.mkdir(parents=True, exist_ok=True)
    gym_path.write_text(
        gym_plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    gym_md_path = gym_path.with_suffix(".md")
    gym_md_path.write_text(
        _gym_plan_to_markdown(gym_plan),
        encoding="utf-8",
    )
    console.print(f"[dim]Gym plan saved to {gym_path} and {gym_md_path}[/dim]")


@app.command()
def gym(
    plan_path: Path = typer.Option(
        ...,
        "--plan",
        help="Path to an existing training plan JSON.",
        exists=True,
    ),
    profile_path: Path = typer.Option(
        ...,
        "--profile",
        help="Path to an existing user profile JSON.",
        exists=True,
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="LLM provider (anthropic/openai/deepseek/qwen/gemini).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Model name override.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Save the gym plan JSON to this path.",
    ),
) -> None:
    """
    Generate detailed gym exercise guidance from an existing training plan
    and user profile.
    """
    import json as _json

    from fitness_agent.planner.models import WeeklyPlan
    from fitness_agent.user.onboarding import load_profile
    from fitness_agent.utils.config import DATA_DIR
    from fitness_agent.utils.llm_client import build_client, build_client_from_config

    # --- Build LLM client ---
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

    # --- Load profile and plan ---
    user_profile = load_profile(profile_path)
    console.print(f"  已加载用户档案: [bold]{user_profile.name}[/bold]")

    raw_plan = _json.loads(plan_path.read_text(encoding="utf-8"))
    fitness_plan = WeeklyPlan.model_validate(raw_plan)
    console.print(f"  已加载训练计划: {len(fitness_plan.training_days)} 训练日")

    # --- Generate gym plan via graph ---
    from fitness_agent.graph.agents.gym import gym_node
    from fitness_agent.gym.models import WeeklyGymPlan

    save_path = output if output else DATA_DIR / "processed" / "gym_plan.json"
    try:
        state_result = gym_node({  # type: ignore[arg-type]
            "user_profile": user_profile.model_dump(),
            "weekly_plan": fitness_plan.model_dump(),
            "provider": client.provider,
            "model": client.model,
            "should_cook": False,
            "should_gym": True,
            "errors": [],
        })
    except Exception as exc:
        console.print(f"[red]Gym plan generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    gym_plan = WeeklyGymPlan.model_validate(state_result["gym_plan"])
    _display_gym_plan(gym_plan)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(gym_plan.model_dump_json(indent=2), encoding="utf-8")
    gym_md_path = save_path.with_suffix(".md")
    gym_md_path.write_text(_gym_plan_to_markdown(gym_plan), encoding="utf-8")
    console.print(f"[dim]Gym plan saved to {save_path} and {gym_md_path}[/dim]")


@app.command()
def cook(
    plan_path: Path = typer.Option(
        ...,
        "--plan",
        help="Path to an existing training plan JSON.",
        exists=True,
    ),
    profile_path: Path = typer.Option(
        ...,
        "--profile",
        help="Path to an existing user profile JSON.",
        exists=True,
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="LLM provider (anthropic/openai/deepseek/qwen/gemini).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Model name override.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Save the cooking plan JSON to this path.",
    ),
) -> None:
    """
    Generate a detailed weekly cooking plan from an existing training plan
    and user profile.
    """
    import json as _json

    from fitness_agent.planner.models import WeeklyPlan
    from fitness_agent.user.onboarding import load_profile
    from fitness_agent.utils.config import DATA_DIR
    from fitness_agent.utils.llm_client import build_client, build_client_from_config

    # --- Build LLM client ---
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

    # --- Load profile and plan ---
    user_profile = load_profile(profile_path)
    console.print(f"  已加载用户档案: [bold]{user_profile.name}[/bold]")

    raw_plan = _json.loads(plan_path.read_text(encoding="utf-8"))
    fitness_plan = WeeklyPlan.model_validate(raw_plan)
    console.print(f"  已加载训练计划: {len(fitness_plan.training_days)} 训练日")

    # --- Generate cooking plan via graph ---
    from fitness_agent.graph.agents.cooking import cook_node
    from fitness_agent.cooking.models import WeeklyCookingPlan

    save_path = output if output else DATA_DIR / "processed" / "cooking_plan.json"
    try:
        state_result = cook_node({  # type: ignore[arg-type]
            "user_profile": user_profile.model_dump(),
            "weekly_plan": fitness_plan.model_dump(),
            "provider": client.provider,
            "model": client.model,
            "should_cook": True,
            "should_gym": False,
            "errors": [],
        })
    except Exception as exc:
        console.print(f"[red]Cooking plan generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    cooking_plan = WeeklyCookingPlan.model_validate(state_result["cooking_plan"])
    _display_cooking_plan(cooking_plan)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(cooking_plan.model_dump_json(indent=2), encoding="utf-8")
    cook_md_path = save_path.with_suffix(".md")
    cook_md_path.write_text(_cooking_plan_to_markdown(cooking_plan), encoding="utf-8")
    console.print(f"[dim]Cooking plan saved to {save_path} and {cook_md_path}[/dim]")


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
