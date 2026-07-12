"""Knowledge base loader: reads JSON data files and provides query methods."""
import json
from pathlib import Path
from functools import cached_property

from fitness_agent.knowledge_base.models import (
    ContraindicationTag,
    Equipment,
    Exercise,
    ExperienceLevel,
    FoodItem,
    GoalType,
    InjuryProfile,
    MuscleGroup,
    MuscleGroupInfo,
    MovementPattern,
    NutritionPrinciples,
    RecipeTemplate,
    TrainingRule,
    WarmupTemplate,
)
from fitness_agent.utils.config import DATA_DIR
from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

# Default paths
_KB_DIR = DATA_DIR / "raw"
EXERCISES_PATH = _KB_DIR / "exercises.json"
NUTRITION_PATH = _KB_DIR / "nutrition.json"
RULES_PATH = _KB_DIR / "rules.json"
ANATOMY_PATH = _KB_DIR / "anatomy.json"
NUTRITION_PRINCIPLES_PATH = _KB_DIR / "nutrition_principles.json"
WARMUP_TEMPLATES_PATH = _KB_DIR / "warmup_templates.json"
INJURY_PROFILES_PATH = _KB_DIR / "injury_profiles.json"
RECIPES_PATH = _KB_DIR / "recipes.json"


class KnowledgeBase:
    """
    Loads and indexes the fitness knowledge base from JSON files.

    This is the deterministic layer: filtering, constraint checking, and
    calculation happen here — not inside the LLM.
    """

    def __init__(
        self,
        exercises_path: Path = EXERCISES_PATH,
        nutrition_path: Path = NUTRITION_PATH,
        rules_path: Path = RULES_PATH,
        anatomy_path: Path = ANATOMY_PATH,
        nutrition_principles_path: Path = NUTRITION_PRINCIPLES_PATH,
        warmup_templates_path: Path | None = WARMUP_TEMPLATES_PATH,
        injury_profiles_path: Path | None = INJURY_PROFILES_PATH,
        recipes_path: Path | None = RECIPES_PATH,
    ) -> None:
        self._exercises_path = exercises_path
        self._nutrition_path = nutrition_path
        self._rules_path = rules_path
        self._anatomy_path = anatomy_path
        self._nutrition_principles_path = nutrition_principles_path
        self._warmup_templates_path = warmup_templates_path
        self._injury_profiles_path = injury_profiles_path
        self._recipes_path = recipes_path

    # ------------------------------------------------------------------
    # Raw data (loaded lazily and cached)
    # ------------------------------------------------------------------

    @cached_property
    def exercises(self) -> list[Exercise]:
        return self._load_list(self._exercises_path, Exercise)

    @cached_property
    def foods(self) -> list[FoodItem]:
        return self._load_list(self._nutrition_path, FoodItem)

    @cached_property
    def rules(self) -> list[TrainingRule]:
        return self._load_list(self._rules_path, TrainingRule)

    @cached_property
    def muscle_groups(self) -> list[MuscleGroupInfo]:
        return self._load_list(self._anatomy_path, MuscleGroupInfo)

    @cached_property
    def nutrition_principles(self) -> NutritionPrinciples | None:
        return self._load_single(self._nutrition_principles_path, NutritionPrinciples)

    @cached_property
    def warmup_templates(self) -> list[WarmupTemplate]:
        if self._warmup_templates_path is None:
            return []
        return self._load_list(self._warmup_templates_path, WarmupTemplate)

    @cached_property
    def injury_profiles(self) -> list[InjuryProfile]:
        if self._injury_profiles_path is None:
            return []
        return self._load_list(self._injury_profiles_path, InjuryProfile)

    @cached_property
    def recipes(self) -> list[RecipeTemplate]:
        if self._recipes_path is None:
            return []
        return self._load_list(self._recipes_path, RecipeTemplate)

    # ------------------------------------------------------------------
    # Exercise queries
    # ------------------------------------------------------------------

    def get_safe_exercises(
        self,
        contraindications: list[ContraindicationTag],
        available_equipment: list[Equipment],
    ) -> list[Exercise]:
        """
        Return exercises that are safe and feasible for a given user.

        Safety rule: exclude exercises whose contraindications overlap
        with the user's injuries.
        Feasibility rule: at least one of the exercise's equipment options
        must be available to the user.
        """
        user_contra_set = set(contraindications)
        equipment_set = set(available_equipment)

        return [
            ex for ex in self.exercises
            if not set(ex.contraindications) & user_contra_set
            and set(ex.equipment) & equipment_set
        ]

    def filter_exercises(
        self,
        exercises: list[Exercise],
        *,
        muscle_groups: list[MuscleGroup] | None = None,
        movement_patterns: list[MovementPattern] | None = None,
        difficulty: list[str] | None = None,
        equipment: list[Equipment] | None = None,
    ) -> list[Exercise]:
        """Further filter an exercise list by optional criteria."""
        result = exercises

        if muscle_groups:
            muscle_set = set(muscle_groups)
            result = [
                ex for ex in result
                if set(ex.primary_muscles) & muscle_set
                or set(ex.secondary_muscles) & muscle_set
            ]

        if movement_patterns:
            pattern_set = set(movement_patterns)
            result = [ex for ex in result if ex.movement_pattern in pattern_set]

        if difficulty:
            diff_set = set(difficulty)
            result = [ex for ex in result if ex.difficulty in diff_set]

        if equipment:
            eq_set = set(equipment)
            result = [ex for ex in result if set(ex.equipment) & eq_set]

        return result

    def get_exercise_by_id(self, exercise_id: str) -> Exercise | None:
        for ex in self.exercises:
            if ex.id == exercise_id:
                return ex
        return None

    # ------------------------------------------------------------------
    # Nutrition queries
    # ------------------------------------------------------------------

    def get_food_by_name(self, name: str) -> FoodItem | None:
        """Case-insensitive lookup by English or Chinese name."""
        name_lower = name.lower()
        for food in self.foods:
            if food.name.lower() == name_lower or food.name_zh == name:
                return food
        return None

    def search_foods(self, query: str) -> list[FoodItem]:
        """Simple substring search across both name fields."""
        q = query.lower()
        return [
            f for f in self.foods
            if q in f.name.lower() or q in f.name_zh.lower()
        ]

    @property
    def all_food_ids(self) -> set[str]:
        """Return the set of all valid food IDs in the nutrition database."""
        return {f.id for f in self.foods}

    def get_food_by_id(self, food_id: str) -> FoodItem | None:
        """Lookup a food item by its ID (exact match)."""
        for food in self.foods:
            if food.id == food_id:
                return food
        return None

    # ------------------------------------------------------------------
    # Recipe queries
    # ------------------------------------------------------------------

    def get_recipes_by_meal_type(self, meal_type: str) -> list[RecipeTemplate]:
        """Filter recipes by meal_type."""
        return [r for r in self.recipes if r.meal_type == meal_type]

    def get_compatible_recipes(self, dietary_restrictions: list[str]) -> list[RecipeTemplate]:
        """Return recipes compatible with ALL given dietary restrictions.

        A recipe is compatible if for each *known* restriction it either:
        (a) natively satisfies it (restriction in dietary_flags), or
        (b) has substitution entries for it (restriction in substitution_groups).

        Restrictions that do not match any known KB key are silently skipped
        here and left to the LLM to handle via the prompt (e.g. free-text
        Chinese input such as '不能吃油腻食物').
        """
        if not dietary_restrictions:
            return list(self.recipes)

        # Collect all known restriction keys across the recipe pool
        known_keys: set[str] = set()
        for r in self.recipes:
            known_keys.update(r.dietary_flags)
            known_keys.update(r.substitution_groups.keys())

        # Only keep restrictions that are recognised KB keys
        known_restrictions = [rest for rest in dietary_restrictions if rest in known_keys]

        # If none of the user restrictions match KB keys, return everything –
        # the LLM will apply the constraints via the prompt.
        if not known_restrictions:
            return list(self.recipes)

        return [
            r for r in self.recipes
            if all(
                rest in r.dietary_flags or rest in r.substitution_groups
                for rest in known_restrictions
            )
        ]

    def get_banned_food_ids(self, dietary_restrictions: list[str]) -> set[str]:
        """Return the set of food IDs banned by the given dietary restrictions.

        Logic:
        1. Find matching DietarySubstitution entries in nutrition_principles.
        2. Collect their ``banned_food_tags``.
        3. For every FoodItem whose ``dietary_tags`` intersect the banned set,
           add the food ID to the result.
        """
        if not dietary_restrictions:
            return set()

        np = self.nutrition_principles
        if np is None:
            return set()

        # Collect all banned tags from matched substitutions
        banned_tags: set[str] = set()
        for restriction in dietary_restrictions:
            sub = np.get_substitution(restriction)
            if sub is not None:
                banned_tags.update(sub.banned_food_tags)

        if not banned_tags:
            return set()

        # Scan all foods for tag intersection
        banned_ids: set[str] = set()
        for food in self.foods:
            if set(food.dietary_tags) & banned_tags:
                banned_ids.add(food.id)

        return banned_ids

    def compute_ingredients_macros(
        self,
        ingredients: list[tuple[str, float]],
    ) -> dict[str, float]:
        """Deterministically compute total macros from a list of (food_id, amount_g).

        Unknown food_ids are skipped with a warning.  Returns rounded values.
        """
        totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for food_id, amount_g in ingredients:
            food = self.get_food_by_id(food_id)
            if food is None:
                logger.warning(f"Unknown food_id: {food_id}")
                continue
            scale = amount_g / food.serving_size_g
            totals["calories"] += food.calories * scale
            totals["protein_g"] += food.protein_g * scale
            totals["carbs_g"] += food.carbs_g * scale
            totals["fat_g"] += food.fat_g * scale
        return {k: round(v, 1) for k, v in totals.items()}

    def compute_recipe_macros(self, recipe: RecipeTemplate) -> dict[str, float]:
        """Deterministically compute macros from ingredient food_ids × amounts.

        Uses nutrition.json data. Unknown food_ids are skipped with a warning.
        """
        totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for ing in recipe.ingredients:
            food = self.get_food_by_id(ing.food_id)
            if food is None:
                logger.warning(f"Unknown food_id in recipe {recipe.id}: {ing.food_id}")
                continue
            scale = ing.amount_g / food.serving_size_g
            totals["calories"] += food.calories * scale
            totals["protein_g"] += food.protein_g * scale
            totals["carbs_g"] += food.carbs_g * scale
            totals["fat_g"] += food.fat_g * scale
        return {k: round(v, 1) for k, v in totals.items()}

    def format_recipes_for_prompt(
        self,
        recipes: list[RecipeTemplate] | None = None,
    ) -> str:
        """Format recipe templates as a compact reference for the LLM prompt.

        Returns an empty string if no recipes are available.
        """
        pool = recipes if recipes is not None else self.recipes
        if not pool:
            return ""

        lines = ["## 食谱参考库", ""]
        lines.append(
            "以下食谱可直接引用或作为组合参考。food_id 对应食材数据库中的 ID，"
            "你可以调整用量来匹配热量目标。"
        )
        lines.append("")

        for r in pool:
            macros = r.per_serving_macros
            cal = macros.get("calories", 0)
            pro = macros.get("protein_g", 0)
            batch_label = " | 可批量备餐" if r.batch_friendly else ""
            lines.append(
                f"**{r.name_zh}** ({r.id}) | {r.meal_type} | "
                f"{cal:.0f}kcal / {pro:.0f}g蛋白 | "
                f"准备{r.prep_time_minutes}+烹饪{r.cook_time_minutes}分钟{batch_label}"
            )
            ings = ", ".join(f"{i.food_id}({i.amount_g}g)" for i in r.ingredients)
            lines.append(f"  食材: {ings}")
            steps = " → ".join(r.steps_zh)
            lines.append(f"  步骤: {steps}")
            if r.dietary_flags:
                lines.append(f"  原生适用: {', '.join(r.dietary_flags)}")
            if r.scaling_notes:
                lines.append(f"  调整: {r.scaling_notes}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def format_foods_compact_for_prompt(self) -> str:
        """Format all food items as a compact reference table for the LLM.

        Lists id, name_zh, category, and per-100g calories/protein for quick lookup.
        """
        if not self.foods:
            return ""

        lines = ["## 食材数据库（每100g营养数据）", ""]
        lines.append("| ID | 名称 | 分类 | 热量(kcal) | 蛋白质(g) | 碳水(g) | 脂肪(g) |")
        lines.append("|----|----|----|----|----|----|")

        for f in self.foods:
            lines.append(
                f"| {f.id} | {f.name_zh} | {f.category.value} | "
                f"{f.calories:.0f} | {f.protein_g:.1f} | {f.carbs_g:.1f} | {f.fat_g:.1f} |"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rules queries
    # ------------------------------------------------------------------

    def get_rules_for_context(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> list[TrainingRule]:
        """Return all rules that apply to the given goal and experience level."""
        return [
            rule for rule in self.rules
            if (not rule.applies_to_goals or goal in rule.applies_to_goals)
            and (not rule.applies_to_levels or level in rule.applies_to_levels)
        ]

    def get_constraint_rules(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> list[TrainingRule]:
        """Return only hard-constraint rules (rule_type == constraint)."""
        from fitness_agent.knowledge_base.models import RuleType
        return [
            r for r in self.get_rules_for_context(goal, level)
            if r.rule_type == RuleType.constraint
        ]

    def format_rules_for_prompt(
        self,
        goal: GoalType,
        level: ExperienceLevel,
    ) -> str:
        """
        Return a formatted string of applicable rules for LLM prompt injection.
        """
        rules = self.get_rules_for_context(goal, level)
        if not rules:
            return "（无特定规则约束）"

        lines = []
        for rule in rules:
            tag = "[硬约束]" if rule.rule_type.value == "constraint" else "[建议]"
            lines.append(f"- {tag} {rule.description}")
            if rule.parameters:
                param_str = ", ".join(f"{k}={v}" for k, v in rule.parameters.items())
                lines.append(f"  参数: {param_str}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Anatomy queries
    # ------------------------------------------------------------------

    def get_volume_targets(self, level: ExperienceLevel) -> dict[str, tuple[int, int]]:
        """
        Return {muscle_id: (min_sets_per_week, max_sets_per_week)} for the given level.

        Uses the ``weekly_volume_{level}_min/max`` fields from anatomy.json.
        Only muscles that have the relevant level-specific fields are included.
        """
        level_key = level.value  # "beginner" / "intermediate" / "advanced"
        result: dict[str, tuple[int, int]] = {}
        for mg in self.muscle_groups:
            min_attr = f"weekly_volume_{level_key}_min"
            max_attr = f"weekly_volume_{level_key}_max"
            min_val = getattr(mg, min_attr, None)
            max_val = getattr(mg, max_attr, None)
            if min_val is not None and max_val is not None:
                result[mg.id] = (min_val, max_val)
        return result

    def format_anatomy_for_prompt(self, level: ExperienceLevel) -> str:
        """
        Return a concise muscle-group reference table for the given experience level.
        Used to help the LLM schedule training days with proper muscle balance and recovery.
        """
        if not self.muscle_groups:
            return ""

        level_v = level.value
        lines = [
            "## 肌群解剖参考（用于排课与容量分配）",
            "",
            "| 肌群 | 分类 | 恢复时长 | 动作模式 | 每周组数参考 |",
            "|------|------|---------|---------|------------|",
        ]

        for mg in self.muscle_groups:
            size_label = "大肌群" if mg.is_large_muscle else "小肌群"
            recovery = (
                f"≥{mg.recovery_hours_min}h"
                if mg.recovery_hours_min == mg.recovery_hours_max
                else f"{mg.recovery_hours_min}-{mg.recovery_hours_max}h"
            )
            patterns = "/".join(mg.primary_movement_patterns)

            if level_v == "beginner":
                vol = f"{mg.weekly_volume_beginner_min}-{mg.weekly_volume_beginner_max}组"
            elif level_v == "intermediate":
                vol = f"{mg.weekly_volume_intermediate_min}-{mg.weekly_volume_intermediate_max}组"
            else:
                vol = f"{mg.weekly_volume_advanced_min}-{mg.weekly_volume_advanced_max}组"

            lines.append(
                f"| {mg.name_zh} | {size_label} | {recovery} | {patterns} | {vol} |"
            )

        lines += [
            "",
            "**排课核心原则：**",
            "- 同一大肌群（胸/背/腿）相邻训练间隔 ≥48 小时（即不得连续两天训练同一肌群）",
            "- 下背部恢复最慢（≥72h），高强度硬拉类动作后需更长恢复",
            "- 推（胸/肩/三头）与拉（背/二头）的训练量比例应接近 1:1",
            "- 髋主导（硬拉系列）与膝主导（深蹲系列）比例应接近 1:1",
            "- 每次训练建议包含至少 1 个核心稳定动作",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Nutrition principles queries
    # ------------------------------------------------------------------

    def format_nutrition_principles_for_prompt(
        self,
        dietary_restrictions: list[str],
        goal: GoalType | None = None,
    ) -> str:
        """
        Format meal timing, training/rest day guidelines, dietary substitutions,
        and supplement recommendations for the given user context.
        """
        np = self.nutrition_principles
        if np is None:
            return ""

        sections: list[str] = ["## 营养执行指南"]

        # --- Meal timing ---
        sections.append("\n**餐食时机：**")
        timing_map = {
            "pre_workout": ("训练前 ~90 分钟", np.meal_timing.get("pre_workout")),
            "post_workout": ("训练后 60 分钟内（黄金窗口）", np.meal_timing.get("post_workout")),
            "pre_sleep": ("睡前 30 分钟", np.meal_timing.get("pre_sleep")),
        }
        for label, entry in timing_map.values():
            if entry:
                examples_str = "、".join(entry.examples[:3]) if entry.examples else ""
                sections.append(f"- **{label}**：{entry.focus}。示例：{examples_str}")

        # --- Training vs rest day ---
        train_day = np.training_vs_rest_day.get("training_day")
        rest_day = np.training_vs_rest_day.get("rest_day")
        if train_day and rest_day:
            sections.append("\n**训练日 vs 休息日营养差异：**")
            sections.append(f"- 训练日：碳水 {train_day.carb_adjustment}，{train_day.note}")
            sections.append(f"- 休息日：碳水 {rest_day.carb_adjustment}，{rest_day.note}")

        # --- Hydration ---
        if np.hydration:
            note = np.hydration.get("note", "")
            if note:
                sections.append(f"\n**水分补充：** {note}")

        # --- Dietary substitutions ---
        matched_subs = []
        for restriction in dietary_restrictions:
            sub = np.get_substitution(restriction)
            if sub:
                matched_subs.append(sub)

        if matched_subs:
            sections.append("\n**饮食限制处理：**")
            for sub in matched_subs:
                sections.append(f"- **{sub.restriction_zh}**：")
                if sub.avoid:
                    sections.append(f"  - 避免：{', '.join(sub.avoid[:5])}")
                if sub.protein_alternatives:
                    sections.append(f"  - 蛋白质来源：{', '.join(sub.protein_alternatives[:5])}")
                if sub.dairy_alternatives:
                    sections.append(f"  - 乳制品替代：{', '.join(sub.dairy_alternatives[:4])}")
                if sub.must_supplement:
                    sections.append(f"  - **必须补充**：{', '.join(sub.must_supplement)}")
                if sub.notes:
                    sections.append(f"  - 备注：{sub.notes}")

        # --- Supplement recommendations ---
        goal_value = goal.value if goal else None
        relevant_supps = [
            s for s in np.supplements
            if not s.suitable_for or not goal_value or goal_value in s.suitable_for
        ][:4]  # cap at 4

        if relevant_supps:
            sections.append("\n**补剂参考（按证据级别）：**")
            for supp in relevant_supps:
                sections.append(
                    f"- **{supp.name_zh}**（{supp.evidence_level}）："
                    f"{supp.benefit}。用法：{supp.dosage}"
                )

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Warmup template queries
    # ------------------------------------------------------------------

    def get_warmup_template(self, movement_patterns: list[str]) -> WarmupTemplate | None:
        """
        Return the best-matching warmup template based on movement pattern overlap.

        Scoring: count how many of the given patterns appear in each template's
        applicable_movement_patterns.  The template with the highest overlap wins.
        Ties are broken by list order.  Returns None if no templates are loaded.
        """
        if not self.warmup_templates:
            return None
        pattern_set = set(movement_patterns)
        best: WarmupTemplate | None = None
        best_score = -1
        for tmpl in self.warmup_templates:
            score = len(pattern_set & set(tmpl.applicable_movement_patterns))
            if score > best_score:
                best_score = score
                best = tmpl
        return best

    def format_warmup_templates_for_prompt(self) -> str:
        """
        Return a formatted reference block of all warmup templates for LLM consumption.

        Returns an empty string if no templates are loaded.
        """
        if not self.warmup_templates:
            return ""

        lines = ["## 热身/拉伸参考模板", ""]
        lines.append(
            "以下模板按训练日类型提供标准化热身和拉伸序列，请根据当天训练重点选择最合适的模板，"
            "并在 warmup_notes / cooldown_notes 中使用这些序列（可适当调整）。"
        )
        lines.append("")

        for tmpl in self.warmup_templates:
            patterns_str = "、".join(tmpl.applicable_movement_patterns)
            lines.append(f"**{tmpl.name_zh} ({tmpl.id})**")
            lines.append(f"适用动作模式：{patterns_str}")
            lines.append("热身序列：")
            for step in tmpl.warmup_sequence:
                lines.append(f"  {step}")
            lines.append("拉伸序列：")
            for step in tmpl.cooldown_sequence:
                lines.append(f"  {step}")
            if tmpl.injury_modifications:
                lines.append("伤病调整：")
                for tag, note in tmpl.injury_modifications.items():
                    lines.append(f"  - {tag}：{note}")
            lines.append("")

        return "\n".join(lines).rstrip()

    # ------------------------------------------------------------------
    # Injury profile queries
    # ------------------------------------------------------------------

    def get_injury_profile(self, tag: ContraindicationTag) -> InjuryProfile | None:
        """Return the InjuryProfile for a given contraindication tag, or None."""
        for profile in self.injury_profiles:
            if profile.tag == tag:
                return profile
        return None

    def format_injury_guidance_for_prompt(
        self, injuries: list[ContraindicationTag]
    ) -> str:
        """
        Return a formatted guidance block for all of the user's injuries.

        Returns an empty string if injuries list is empty or no profiles are loaded.
        """
        if not injuries or not self.injury_profiles:
            return ""

        lines = ["## 伤病修改指导", ""]
        lines.append(
            "⚠️ 该用户存在以下伤病/禁忌，制定计划时必须严格遵守对应调整规则："
        )
        lines.append("")

        found_any = False
        for tag in injuries:
            profile = self.get_injury_profile(tag)
            if profile is None:
                continue
            found_any = True
            lines.append(f"**{profile.name_zh} ({tag.value})**")
            if profile.avoid_movement_patterns:
                avoid_str = "、".join(profile.avoid_movement_patterns)
                lines.append(f"- 应完全避免的动作模式：{avoid_str}")
            for pattern, note in profile.modify_movement_patterns.items():
                lines.append(f"- {pattern} 模式修改：{note}")
            lines.append(f"- 热身重点：{profile.warmup_focus_zh}")
            lines.append(f"- 整体注意：{profile.general_guidance_zh}")
            lines.append("")

        if not found_any:
            return ""

        return "\n".join(lines).rstrip()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        return {
            "exercises": len(self.exercises),
            "foods": len(self.foods),
            "rules": len(self.rules),
            "muscle_groups": len(self.muscle_groups),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_single(self, path: Path, model_cls: type):
        """Load a single JSON object (not a list) from a file."""
        if not path.exists():
            logger.warning(f"KB data file not found: {path}. Returning None.")
            return None
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        try:
            result = model_cls.model_validate(raw)
            logger.info(f"Loaded {model_cls.__name__} from {path.name}")
            return result
        except Exception as e:
            logger.warning(f"Failed to load {path.name}: {e}")
            return None

    def _load_list(self, path: Path, model_cls: type) -> list:
        if not path.exists():
            logger.warning(f"KB data file not found: {path}. Returning empty list.")
            return []

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        items = []
        for entry in raw:
            try:
                items.append(model_cls.model_validate(entry))
            except Exception as e:
                logger.warning(f"Skipping invalid entry in {path.name}: {e}")

        logger.info(f"Loaded {len(items)} items from {path.name}")
        return items
