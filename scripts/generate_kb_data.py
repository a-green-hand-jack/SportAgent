"""
Generate initial knowledge base JSON data files using DeepSeek.

Usage:
    uv run python scripts/generate_kb_data.py [--what exercises|nutrition|rules|all]

This script calls DeepSeek (deepseek-chat) to generate structured JSON data
conforming to the KB Pydantic models. Output is written to data/raw/.

DeepSeek max_tokens is 8192, so large datasets (exercises, nutrition) are
generated in multiple batches and merged automatically.
"""
import argparse
import json
import sys
from pathlib import Path

from openai import OpenAI

# Ensure src/ is on path when running as script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fitness_agent.knowledge_base.models import (
    Exercise,
    FoodItem,
    TrainingRule,
)
from fitness_agent.utils.config import DEEPSEEK_API_KEY, DATA_DIR
from fitness_agent.utils.logging import get_logger

logger = get_logger("generate_kb_data")

RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "deepseek-chat"  # DeepSeek-V3.2, 128K context, max_tokens=8192

# ---------------------------------------------------------------------------
# Shared system prompts (schema definitions)
# ---------------------------------------------------------------------------

EXERCISE_SYSTEM = """你是一位专业的运动科学专家，负责为一个 AI 健身规划系统构建运动动作库。

你需要生成一个 JSON 对象，包含一个 "exercises" 键，其值为 JSON 数组。数组中每个元素是一个健身动作（exercise），严格符合以下 schema：

{
  "id": "snake_case唯一标识",
  "name": "英文名称",
  "name_zh": "中文名称",
  "category": "strength|cardio|flexibility|plyometric",
  "equipment": ["bodyweight|dumbbell|barbell|kettlebell|resistance_band|cable_machine|machine|pull_up_bar|bench|ez_bar"],
  "primary_muscles": ["chest|back|lats|traps|lower_back|shoulders|front_delt|side_delt|rear_delt|biceps|triceps|forearms|core|abs|obliques|quads|hamstrings|glutes|calves|hip_flexors|adductors|full_body"],
  "secondary_muscles": [...同上...],
  "difficulty": "beginner|intermediate|advanced",
  "movement_pattern": "push|pull|squat|hinge|carry|core|cardio|isolation",
  "contraindications": ["knee_injury|lower_back_pain|shoulder_injury|wrist_injury|neck_pain|hip_injury|ankle_injury|herniated_disc|hypertension|elbow_injury"],
  "cues": ["动作要领1（中文）", "动作要领2", ...],
  "met_value": null 或 数字（仅有氧动作填写）
}

要求：
- equipment 字段填写做这个动作所需的器材（可多种器材）
- contraindications 只填写真正有风险的禁忌，不要过度保守
- cues 提供 3-5 条关键动作要领（中文）
- 只输出纯 JSON 对象 {"exercises": [...]}
"""

NUTRITION_SYSTEM = """你是一位注册营养师，负责为一个 AI 健身规划系统构建食物营养数据库。

你需要生成一个 JSON 对象，包含一个 "foods" 键，其值为 JSON 数组。数组中每个元素是一种食物，严格符合以下 schema：

{
  "id": "snake_case唯一标识",
  "name": "英文名称",
  "name_zh": "中文名称",
  "category": "grain|meat|poultry|seafood|egg_dairy|vegetable|fruit|nut_seed|legume|oil_fat|condiment|supplement",
  "serving_size_g": 100,
  "calories": 数字（kcal/100g）,
  "protein_g": 数字,
  "carbs_g": 数字,
  "fat_g": 数字,
  "fiber_g": 数字
}

要求：
- serving_size_g 统一使用 100（即每100克的营养数据）
- 营养数据要准确（参考 USDA 或权威中文数据库）
- 只输出纯 JSON 对象 {"foods": [...]}
"""

RULES_SYSTEM = """你是一位经验丰富的力量与体能教练，负责为 AI 健身规划系统编写训练规则集。

你需要生成一个 JSON 对象，包含一个 "rules" 键，其值为 JSON 数组。数组中每个规则严格符合以下 schema：

{
  "id": "rule_xxx",
  "category": "volume|frequency|intensity|nutrition|progression|safety|recovery|structure",
  "applies_to_goals": ["muscle_gain|fat_loss|body_recomposition|general_fitness"],
  "applies_to_levels": ["beginner|intermediate|advanced"],
  "rule_type": "constraint|recommendation",
  "description": "规则的自然语言描述（中文，清晰具体，直接可注入 LLM prompt）",
  "parameters": {"key": value} 或 null
}

说明：
- applies_to_goals 和 applies_to_levels 为空数组时表示适用所有目标/水平
- constraint（硬约束）：必须执行，违反会造成安全风险或严重效果损失
- recommendation（软建议）：最佳实践，在合理情况下可灵活调整
- description 要清晰可操作，能直接作为 LLM 的约束条件
- parameters 存放数值边界，供程序逻辑使用
- 只输出纯 JSON 对象 {"rules": [...]}
"""

# ---------------------------------------------------------------------------
# Batch prompts — split large datasets to fit within 8192 max_tokens
# ---------------------------------------------------------------------------

EXERCISE_PROMPTS = [
    # Batch 1: bodyweight + pull-up bar (~25 exercises)
    """请生成 25 个健身动作，仅覆盖以下器材类型：
- 徒手/自重（bodyweight）：约 20 个
- 单杠（pull_up_bar）：约 5 个

要求覆盖胸、背、肩、手臂、核心、腿部等主要肌群。
还需包含 3 个有氧类动作（如 Burpee、Mountain Climber 等，带 met_value）。
请直接输出 JSON 对象 {"exercises": [...]}。""",

    # Batch 2: dumbbell + kettlebell + resistance_band (~30 exercises)
    """请生成 30 个健身动作，仅覆盖以下器材类型：
- 哑铃（dumbbell）：约 20 个
- 壶铃（kettlebell）：约 5 个
- 弹力带（resistance_band）：约 5 个

要求覆盖胸、背、肩、手臂、核心、腿部等主要肌群。
还需包含 2 个有氧类动作（带 met_value）。
请直接输出 JSON 对象 {"exercises": [...]}。""",

    # Batch 3: barbell + cable_machine + machine (~30 exercises)
    """请生成 30 个健身动作，仅覆盖以下器材类型：
- 杠铃（barbell）：约 20 个
- 绳索器械（cable_machine）：约 5 个
- 固定器械（machine）：约 5 个

要求覆盖胸、背、肩、手臂、核心、腿部等主要肌群。
请直接输出 JSON 对象 {"exercises": [...]}。""",
]

NUTRITION_PROMPTS = [
    # Batch 1: protein-rich foods (~55 items)
    """请生成以下类别的食物营养数据（每 100g），共约 55 种：

- 主食/谷物（grain）：大米、糙米、燕麦、全麦面包、土豆、红薯等 15 种
- 畜肉（meat）：牛肉（各部位）、猪肉（各部位）、羊肉等 12 种
- 禽肉（poultry）：鸡胸肉、鸡腿、鸭肉等 8 种
- 海鲜（seafood）：三文鱼、金枪鱼、虾、鳕鱼等 10 种
- 蛋奶（egg_dairy）：鸡蛋、蛋白、牛奶、酸奶、希腊酸奶、奶酪等 10 种

请直接输出 JSON 对象 {"foods": [...]}。""",

    # Batch 2: plant-based + supplements (~65 items)
    """请生成以下类别的食物营养数据（每 100g），共约 65 种：

- 蔬菜（vegetable）：西兰花、菠菜、番茄、黄瓜、胡萝卜、芹菜等 20 种
- 水果（fruit）：香蕉、苹果、蓝莓、草莓、橙子等 12 种
- 坚果种子（nut_seed）：杏仁、花生、核桃、葵花籽等 8 种
- 豆类（legume）：鹰嘴豆、黑豆、豆腐、毛豆、红豆等 10 种
- 油脂（oil_fat）：橄榄油、花生油、椰子油、黄油等 5 种
- 运动补剂（supplement）：乳清蛋白粉、酪蛋白、肌酸、BCAA、谷氨酰胺等 5 种
- 调味品（condiment）：酱油、蚝油、醋、蜂蜜、花生酱等 5 种

请直接输出 JSON 对象 {"foods": [...]}。""",
]

RULES_PROMPT = """请生成一套完整的健身训练规则集，涵盖以下方面，共约 40 条规则：

1. 训练容量规则（volume）：每肌群每周最少/最多组数，新手/中级/高级的差异
2. 训练频率规则（frequency）：每周训练天数限制，同一肌群的训练间隔
3. 训练强度规则（intensity）：RM 范围与目标的对应，RPE 建议
4. 营养规则（nutrition）：热量缺口/盈余范围、蛋白质摄入标准、三大宏量比例
5. 渐进超负荷（progression）：每周增重幅度，新手线性进阶规则
6. 安全规则（safety）：新手前几周的限制，禁止动作，高风险动作的前提条件
7. 恢复规则（recovery）：最低睡眠、训练后休息时间
8. 训练结构（structure）：分化方式（全身/上下分/推拉腿）与训练天数的对应

请直接输出 JSON 对象 {"rules": [...]}。"""

# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------

_CLIENT: OpenAI | None = None


def _get_client() -> OpenAI:
    """Lazy-init the OpenAI client for DeepSeek."""
    global _CLIENT
    if _CLIENT is None:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY not set. Please add it to .env")
        _CLIENT = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _CLIENT


def _call_deepseek(system: str, prompt: str) -> dict:
    """Single DeepSeek API call, returns parsed JSON dict."""
    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content
    if not raw_text:
        raise RuntimeError(
            "DeepSeek returned empty content. Try adjusting the prompt."
        )
    return json.loads(raw_text.strip())


def _extract_list(result: dict, key: str) -> list:
    """Extract the list from a JSON response, with fallbacks."""
    if isinstance(result, dict) and key in result:
        return result[key]
    if isinstance(result, list):
        return result
    # Fallback: grab the first list value
    for v in result.values():
        if isinstance(v, list):
            return v
    raise ValueError(
        f"Unexpected JSON structure from DeepSeek: {list(result.keys())}"
    )


def generate_batched(
    system: str,
    prompts: list[str],
    response_key: str,
    label: str,
) -> list:
    """Generate data in multiple batches and merge results."""
    all_data: list = []
    for i, prompt in enumerate(prompts, 1):
        logger.info(
            f"Calling DeepSeek ({MODEL}) to generate {label} "
            f"[batch {i}/{len(prompts)}]..."
        )
        result = _call_deepseek(system, prompt)
        batch = _extract_list(result, response_key)
        logger.info(f"  Batch {i}: got {len(batch)} entries")
        all_data.extend(batch)

    logger.info(f"Generated {len(all_data)} {label} entries total")
    return all_data


def validate_and_save(
    data: list,
    model_cls: type,
    output_path: Path,
    label: str,
) -> None:
    """Validate each entry against the Pydantic model, then save."""
    valid = []
    skipped = 0

    for entry in data:
        try:
            model_cls.model_validate(entry)
            valid.append(entry)
        except Exception as e:
            logger.warning(f"Invalid {label} entry (skipped): {e}\n  Entry: {entry}")
            skipped += 1

    output_path.write_text(
        json.dumps(valid, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        f"Saved {len(valid)} valid {label} entries to {output_path} "
        f"({skipped} skipped)"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate KB data using DeepSeek")
    parser.add_argument(
        "--what",
        choices=["exercises", "nutrition", "rules", "all"],
        default="all",
        help="Which dataset to generate",
    )
    args = parser.parse_args()

    # Each task: (system_prompt, list_of_user_prompts, response_key, model_cls, output_path)
    tasks = {
        "exercises": (
            EXERCISE_SYSTEM, EXERCISE_PROMPTS, "exercises",
            Exercise, RAW_DIR / "exercises.json",
        ),
        "nutrition": (
            NUTRITION_SYSTEM, NUTRITION_PROMPTS, "foods",
            FoodItem, RAW_DIR / "nutrition.json",
        ),
        "rules": (
            RULES_SYSTEM, [RULES_PROMPT], "rules",
            TrainingRule, RAW_DIR / "rules.json",
        ),
    }

    targets = list(tasks.keys()) if args.what == "all" else [args.what]

    for target in targets:
        system, prompts, resp_key, model_cls, output_path = tasks[target]
        try:
            data = generate_batched(system, prompts, resp_key, target)
            validate_and_save(data, model_cls, output_path, target)
        except Exception as e:
            logger.error(f"Failed to generate {target}: {e}")
            raise

    logger.info("Done. KB data files written to data/raw/")


if __name__ == "__main__":
    main()
