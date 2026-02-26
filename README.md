# 🏋️ Fitness Agent — AI 个性化健身规划助手

> 通过一次简单的问答，由 AI 为你生成量身定制的**周训练计划 + 每日营养方案**。
> 支持通义千问（Qwen）、Anthropic Claude、OpenAI、DeepSeek 等多家大模型，**推荐 Qwen 作为最佳服务商**。

---

## ✨ 核心功能

我们采用了 **多 Agent 架构**，各个智能体各司其职，为您全方位打造专业计划：

| 功能                  | 说明                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| 🎯 **个性化训练大纲** | **Planner Agent** 综合分析目标与经验，为你量身定做每周训练与宏观营养框架 |
| 🍳 **智能餐饮规划**   | **Cooking Agent** 提供带动态热量缩放的逐日餐食、食谱组合与量化采购清单   |
| 💪 **单次执行指导**   | **Gym Agent** 下发包含热身、呼吸调整及动作细节（KB Cues）的实操课表      |
| 🛡️ **伤病安全过滤**   | 支持自由输入伤病描述，自动调取知识库识别并修改高风险动作                 |
| 📦 **全景静态知识库** | 动作库、食谱数据、营养/训练规则完全本地化存储，严格控制大模型幻觉        |
| 💾 **档案复用**       | 首次问答后自动保存体测档案，支持各级 Agent 增量调用与按需组合运行        |
| 🔄 **多模型适配**     | 一行配置灵活无缝切换 Qwen / Claude / DeepSeek / GPT                      |

---

## 🚀 快速开始

### 1. 环境要求

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** 包管理器（推荐）

安装 uv（如果还没有）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆并安装

```bash
git clone <repo-url> SportAgent
cd SportAgent

# 安装项目及全部依赖（自动创建虚拟环境）
uv sync
```

### 3. 配置 API Key

复制示例配置文件并填入你的 API Key：

```bash
cp .env.example .env
```

用文本编辑器打开 `.env`，至少填写一个 LLM 提供商的 Key：

```env
# 选择你拥有 API Key 的提供商（推荐填入通义千问）
QWEN_API_KEY=sk-...               # 通义千问（推荐）
ANTHROPIC_API_KEY=sk-ant-...      # Claude
OPENAI_API_KEY=sk-...             # GPT-4o
DEEPSEEK_API_KEY=sk-...           # DeepSeek
GOOGLE_API_KEY=AIza...            # Gemini

# 指定默认使用的大模型提供商
LLM_PROVIDER=qwen
LLM_MODEL=qwen3.5-plus
```

### 4. 生成你的第一个训练计划

```bash
uv run fitness-agent plan
```

程序会引导你完成一系列问答，大约需要 **2–3 分钟**，然后 AI 将输出你的专属训练计划。

---

## 📖 使用说明

### 问答流程

启动后程序会依次询问：

1. **基本信息** — 姓名、年龄、性别、身高、体重
2. **训练目标** — 减脂 / 增肌 / 增肌减脂 / 提升体能
3. **训练经验** — 新手（<1年）/ 中级（1–3年）/ 高级（3年+）
4. **日常活动水平** — 久坐 / 轻度活跃 / 中度活跃 / 高度活跃
5. **训练安排** — 每周训练天数（1–6天）、每次时长（20–180分钟）
6. **力量水平自评** — 用于估算动作起始重量
7. **训练时间偏好** — 清晨 / 上午 / 下午 / 傍晚 / 不固定
8. **可用器材** — 多选：哑铃、杠铃、壶铃、弹力带、绳索器械等
9. **伤病情况** _(可选)_ — 自由文本输入，AI 自动识别
10. **饮食限制** _(可选)_ — 如素食、乳糖不耐等

### 计划输出内容

问答结束后，AI 将生成包含以下内容的完整方案：

- **📊 每日营养目标** — 热量（kcal）、蛋白质、碳水、脂肪目标
- **🍽 推荐餐食** — 具体食物搭配建议，含训练前后餐
- **💪 每日训练安排** — 按天列出动作、组数、次数、休息时间、起始重量建议
- **🔥 热身 / 冷却方案** — 每个训练日的准备与放松建议
- **📅 4周训练进阶规划** — 周期化视角，指导如何系统推进
- **💬 教练提示** — AI 针对你个人情况的专项建议

---

## ⚙️ 命令行选项

### `fitness-agent plan` — 生成周计划与日常营养大纲

```
Options:
  -p, --provider TEXT   LLM 提供商 (qwen/anthropic/openai/deepseek/gemini)
  -m, --model TEXT      模型名称，覆盖 .env 中的默认值
  --profile PATH        加载已有用户档案 JSON（跳过问答）
  -o, --output PATH     将生成的计划保存为 JSON 文件
  --cook                生成计划后，继续调用 Cooking Agent 生成详细食谱与购物清单
  --gym                 生成计划后，继续调用 Gym Agent 生成实操训练指导
  --help                显示帮助
```

**示例：**

```bash
# 使用默认的 LLM 提供商（推荐使用 Qwen）
uv run fitness-agent plan

# 一键生成完整总方案（包含周计划长流程、详细逐日食谱安排与具体训练日动作指导）
uv run fitness-agent plan --cook --gym

# 临时指定使用 DeepSeek / GPT 等
uv run fitness-agent plan --provider deepseek --model deepseek-chat

# 加载已有档案，跳过问答直接生成计划
uv run fitness-agent plan --profile data/processed/profile.json

# 生成计划并指定保存到某文件
uv run fitness-agent plan --output outputs/my_plan.json
```

### 多 Agent 独立执行

如果你已经获得一份周计划（默认存为 `plan.json`），你可以挂载个人状态单独按需调用专项 Agent：

```bash
# 执行 Cooking Agent 并生成后续餐饮采购需求
uv run fitness-agent cook --plan data/processed/plan.json --profile data/processed/profile.json

# 执行 Gym Agent 对周计划进行解包，生成可供健身房直接翻阅的单次课详细指引
uv run fitness-agent gym --plan data/processed/plan.json --profile data/processed/profile.json
```

### `fitness-agent version` — 查看版本

```bash
uv run fitness-agent version
```

---

## 🔑 支持的 LLM 提供商

我们强烈推荐采用 **通义千问（Qwen）** 作为主力驱动的大模型供应商，并首选使用 **`qwen3.5-plus`** 模型，能够提供绝佳的指令遵循、生成稳定性及性价比。

| 提供商            | 环境变量            | 推荐模型           | 特点                                 |
| ----------------- | ------------------- | ------------------ | ------------------------------------ |
| **通义千问**      | `QWEN_API_KEY`      | `qwen3.5-plus`     | 国内访问极速，逻辑稳定，**首选推荐** |
| **Anthropic**     | `ANTHROPIC_API_KEY` | `claude-opus-4-6`  | 中文理解极佳，规划能力强             |
| **OpenAI**        | `OPENAI_API_KEY`    | `gpt-4o`           | 通用推理能力强                       |
| **DeepSeek**      | `DEEPSEEK_API_KEY`  | `deepseek-chat`    | 极其经济实惠，中文支持好             |
| **Google Gemini** | `GOOGLE_API_KEY`    | `gemini-2.0-flash` | 速度极快，免费额度充沛               |

---

## 🩺 伤病输入说明

伤病字段支持**中英文自由输入**，AI 会自动识别并映射到安全规则。例如：

```
"手腕疼、膝盖不好，有腰椎间盘突出"
"wrist pain, bad knees"
"左肩受伤，不能做过头推举"
```

识别确认后，系统将自动从你的动作池中过滤掉下列对应的高风险动作：

| 伤病类型      | 规避动作示例             |
| ------------- | ------------------------ |
| 膝关节损伤    | 深蹲、弓步、腿举         |
| 腰痛 / 下背痛 | 硬拉、杠铃弯举（站姿）   |
| 肩关节损伤    | 过头推举、卧推（高角度） |
| 手腕损伤      | 俯卧撑、腕弯举           |
| 椎间盘突出    | 大重量硬拉、压迫性屈伸   |
| 高血压        | 高强度屏气动作           |

---

## 💾 用户档案复用

首次运行后，你的个人信息会自动保存至：

```
data/processed/profile.json
```

下次运行时可用 `--profile` 选项直接跳过问答：

```bash
uv run fitness-agent plan --profile data/processed/profile.json
```

也可以手动编辑该 JSON 文件来更新个人信息（如体重变化、更换器材等）。

---

## 📁 项目结构

```
SportAgent/
├── src/fitness_agent/
│   ├── knowledge_base/   # 各类知识库加载与校验模块（独立管理）
│   ├── planner/          # Planner Agent：规划每周健身与宏观营养大纲
│   ├── cooking/          # Cooking Agent：结合约束与食谱生成逐日带缩放详细配餐
│   ├── gym/              # Gym Agent：生成单次课具体执行细节及针对性建议
│   ├── user/             # 用户档案与 BMR/TDEE 模型系统
│   ├── utils/            # LLM 客户端封装 · 日志 · 配置等公共设施
│   └── cli.py            # 命令行入口，统筹多 Agent 调度
├── data/
│   └── raw/              # 本地静态 JSON 知识库资源
│       ├── exercises.json          # 动作库（详尽的解剖、纠错、提示信息）
│       ├── recipes.json            # 本地食谱库（供 Cooking Agent 使用）
│       ├── nutrition.json          # 食材基础信息库
│       ├── nutrition_principles.json # 营养与加餐分配原则
│       ├── rules.json              # 训练规则集（容量/频率/安全）
│       ├── anatomy.json            # 肌群解剖参考
│       ├── injury_profiles.json    # 伤病类型分析与动作规避方案
│       └── warmup_templates.json   # 专项热身与拉伸模块
├── .env.example          # 环境变量配置模板
└── pyproject.toml        # 项目配置与依赖声明
```

---

## ❓ 常见问题

**Q: 运行时报 `LLM configuration error`？**

A: 检查 `.env` 文件中对应提供商的 API Key 是否正确填写，且 `LLM_PROVIDER` 与 Key 匹配。

**Q: 报 `LLM response is not valid JSON`？**

A: 部分模型输出不稳定，建议更换为更强的模型（如 `claude-opus-4-6` 或 `gpt-4o`），或重试一次。

**Q: 生成的训练天数与我填写的不一致？**

A: 这是已知的 LLM 合规性问题，程序会在日志中记录警告。可重新运行生成，或接受当前结果后手动调整。

**Q: 如何更新我的个人信息（如减重后体重变化）？**

A: 直接编辑 `data/processed/profile.json`，修改 `weight_kg` 等字段，然后重新运行 `fitness-agent plan --profile data/processed/profile.json`。

**Q: 可以不联网使用吗？**

A: 知识库（动作、营养、规则）完全本地化，但生成计划需要调用 LLM API，因此需要网络连接。

---

## 📝 许可证

本项目仅供个人学习与研究使用。
