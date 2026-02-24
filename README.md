# 🏋️ Fitness Agent — AI 个性化健身规划助手

> 通过一次简单的问答，由 AI 为你生成量身定制的**周训练计划 + 每日营养方案**。
> 支持 Anthropic Claude、OpenAI、DeepSeek、Qwen、Google Gemini 等多家 LLM 提供商。

---

## ✨ 核心功能

| 功能                  | 说明                                                  |
| --------------------- | ----------------------------------------------------- |
| 🎯 **个性化训练计划** | AI 根据你的目标、经验、可用器材生成每周训练安排       |
| 🥗 **每日营养方案**   | 自动计算 BMR / TDEE，给出热量、蛋白质、碳水、脂肪目标 |
| 🛡️ **伤病安全过滤**   | 支持自由文本描述伤病，AI 自动识别并规避高风险动作     |
| 📦 **结构化知识库**   | 动作库、营养数据、训练规则全部本地化存储，不依赖网络  |
| 💾 **档案复用**       | 首次问答后自动保存用户画像，下次可直接加载跳过问答    |
| 🔄 **多 LLM 支持**    | 一行命令切换 Claude / GPT / DeepSeek / Gemini         |

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
# 选择你拥有 API Key 的提供商（至少填一个）
ANTHROPIC_API_KEY=sk-ant-...      # Claude（默认）
OPENAI_API_KEY=sk-...             # GPT-4o
DEEPSEEK_API_KEY=sk-...           # DeepSeek（较经济）
QWEN_API_KEY=sk-...               # 通义千问
GOOGLE_API_KEY=AIza...            # Gemini

# 指定默认使用的提供商和模型
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-4-6
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

### `fitness-agent plan` — 生成训练计划

```
Options:
  -p, --provider TEXT   LLM 提供商 (anthropic/openai/deepseek/qwen/gemini)
  -m, --model TEXT      模型名称，覆盖 .env 中的默认值
  --profile PATH        加载已有用户档案 JSON（跳过问答）
  -o, --output PATH     将生成的计划保存为 JSON 文件
  --help                显示帮助
```

**示例：**

```bash
# 使用默认（.env 中配置）的 LLM 提供商
uv run fitness-agent plan

# 指定使用 DeepSeek（更经济实惠）
uv run fitness-agent plan --provider deepseek --model deepseek-chat

# 指定使用 GPT-4o
uv run fitness-agent plan --provider openai --model gpt-4o

# 使用 Gemini Flash（速度快、免费额度充足）
uv run fitness-agent plan --provider gemini --model gemini-2.0-flash

# 加载已有档案，跳过问答直接生成计划
uv run fitness-agent plan --profile data/processed/profile.json

# 生成计划并保存到文件
uv run fitness-agent plan --output outputs/my_plan.json
```

### `fitness-agent version` — 查看版本

```bash
uv run fitness-agent version
```

---

## 🔑 支持的 LLM 提供商

| 提供商            | 环境变量            | 推荐模型           | 特点                   |
| ----------------- | ------------------- | ------------------ | ---------------------- |
| **Anthropic**     | `ANTHROPIC_API_KEY` | `claude-opus-4-6`  | 中文理解优秀，推荐首选 |
| **OpenAI**        | `OPENAI_API_KEY`    | `gpt-4o`           | 通用能力强             |
| **DeepSeek**      | `DEEPSEEK_API_KEY`  | `deepseek-chat`    | 价格低廉，中文支持好   |
| **通义千问**      | `QWEN_API_KEY`      | `qwen-plus`        | 国内访问友好           |
| **Google Gemini** | `GOOGLE_API_KEY`    | `gemini-2.0-flash` | 速度快，有免费额度     |

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
│   ├── knowledge_base/   # 动作库 · 营养数据 · 训练规则（本地 KB）
│   ├── planner/          # 规划 Agent：核心 AI 交互与计划生成逻辑
│   ├── user/             # 用户模型：问答流程 · 画像 · BMR/TDEE 计算
│   ├── utils/            # LLM 客户端封装 · 日志 · 配置
│   └── cli.py            # 命令行入口
├── data/
│   └── raw/
│       ├── exercises.json          # 动作库（100+ 动作）
│       ├── nutrition.json          # 食物数据库
│       ├── nutrition_principles.json # 营养原则与时机规则
│       ├── rules.json              # 训练规则集（容量/频率/安全）
│       └── anatomy.json            # 肌群解剖与训练量参考
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
