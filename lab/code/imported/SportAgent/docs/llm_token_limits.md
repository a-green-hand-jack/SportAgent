# LLM Token Limits Reference

> **核心结论**：上下文窗口（输入）很大 ≠ 输出上限也大。
> 7天饮食计划 JSON 约需 **12,000–15,000 输出 tokens**。
> 输出上限 < 15k 的模型需要分批生成。

---

## 分批阈值

`CookingAgent._compute_batches()` 逻辑：

| 条件                                        | 策略                         | 说明              |
| ------------------------------------------- | ---------------------------- | ----------------- |
| provider 不在 `_MAX_TOKENS_CAP`             | **单批**（1次调用，7天）     | 输出上限足够      |
| provider 在 `_MAX_TOKENS_CAP`（cap ≤ 8192） | **三批**（2+2+3天，3次调用） | 每批 ~4000 tokens |

将 provider 加入 `_MAX_TOKENS_CAP`（见 `llm_client.py`）即可启用分批。

---

## Qwen（阿里云 DashScope）

API base: `https://dashscope.aliyuncs.com/compatible-mode/v1`

| 模型 ID              | 最大输入        | **最大输出**                | 备注                             |
| -------------------- | --------------- | --------------------------- | -------------------------------- |
| `qwen-turbo` ✅ 推荐 | 1M tokens       | **16,384**                  | 速度最快，成本最低，足够单批生成 |
| `qwen-plus` ⚠️       | 1M tokens       | **8,192**                   | 旧默认，不够，需分批             |
| `qwen-max` ⚠️        | 32,768          | **8,192**                   | 质量最高但输出上限和 plus 一样   |
| `qwen-long` ⚠️       | 10M tokens      | **8,192**                   | 超长输入场景，输出同样受限       |
| `qwen3.5-plus` ⚠️    | 991K (1M上下文) | 理论 **64K**，实测 API ~10k | 新模型，DashScope 实际 cap 未知  |

> ⚠️ `qwen-max` 输入上下文只有 32,768 tokens（不是 1M），加上本项目 prompt 约 15k 输入，剩余空间有限。
> ⚠️ `qwen3.5-plus` 官方页面标注输出 64K，但实测 API 在 ~9900 tokens 处截断，疑似 DashScope 对新模型有隐式 cap。

**当前项目默认**：`qwen-turbo`（16k 输出，单批无障碍）

---

## DeepSeek

API base: `https://api.deepseek.com/v1`

| 模型 ID                     | 最大输入 | **最大输出**                  | 备注                  |
| --------------------------- | -------- | ----------------------------- | --------------------- |
| `deepseek-chat` ⚠️          | 128K     | **8,000**（默认 4k，最大 8k） | 不够，需分批          |
| `deepseek-reasoner` ✅ 推荐 | 128K     | **32,000–64,000**             | R1 推理模型，单批足够 |

**当前项目默认**：`deepseek-reasoner`（32k 输出，单批无障碍）

如需切换回 `deepseek-chat`（成本更低），在 `llm_client.py` 的 `_MAX_TOKENS_CAP` 取消注释 `"deepseek": 8192`。

---

## OpenAI

API base: `https://api.openai.com/v1`

| 模型 ID               | 最大输入 | **最大输出** | 备注                           |
| --------------------- | -------- | ------------ | ------------------------------ |
| `gpt-4o` ✅           | 128K     | **16,384**   | 旗舰模型，单批无障碍           |
| `gpt-4o-mini` ✅ 推荐 | 128K     | **16,384**   | 当前默认，性价比高，单批无障碍 |
| `o1` / `o3`           | 200K     | **100,000**  | 推理模型，远超需求             |

**当前项目默认**：`gpt-4o-mini`（16k 输出，单批无障碍）

---

## Anthropic Claude

使用原生 Anthropic SDK（非 OpenAI 兼容接口），`_MAX_TOKENS_CAP` 对其**无效**。

| 模型 ID                         | 最大输入 | **最大输出**                | 备注                             |
| ------------------------------- | -------- | --------------------------- | -------------------------------- |
| `claude-3-haiku-20240307` ⚠️    | 200K     | **4,096**                   | 太低，需分批（SDK 层需单独处理） |
| `claude-3-5-haiku-20241022` ⚠️  | 200K     | **8,192**                   | 需分批                           |
| `claude-3-5-sonnet-20241022` ⚠️ | 200K     | **8,192**（需 beta header） | 需分批                           |
| `claude-haiku-4-5` ✅           | 200K     | **64,000**                  | 当前默认，新一代，单批足够       |
| `claude-opus-4-5` ✅            | 200K     | **32,000+**                 | 最强，单批足够                   |

> ⚠️ Anthropic SDK 中如需分批，需在 `AnthropicClient.chat()` 方法内单独实现（不走 `_MAX_TOKENS_CAP`）。
> **当前项目默认**：`claude-haiku-4-6`（若指 haiku 4.5，64k 输出，单批无障碍）

---

## Google Gemini

使用原生 Gemini SDK，`_MAX_TOKENS_CAP` 对其**无效**。

| 模型 ID               | 最大输入 | **最大输出** | 备注                       |
| --------------------- | -------- | ------------ | -------------------------- |
| `gemini-2.0-flash` ⚠️ | 1M       | **8,192**    | 当前默认，需分批（SDK 层） |
| `gemini-1.5-flash` ⚠️ | 1M       | **8,192**    | 同上                       |
| `gemini-1.5-pro` ⚠️   | 2M       | **8,192**    | 同上                       |
| `gemini-2.5-flash` ✅ | 1M       | **65,536**   | 推荐，单批足够             |
| `gemini-2.5-pro` ✅   | 2M       | **65,536**   | 质量最高，单批足够         |

> ⚠️ Gemini SDK 中如需分批，需在 `GeminiClient.chat()` 方法内单独实现。
> **当前项目默认**：`gemini-2.0-flash`（输出 8k，7 天计划会截断，建议改用 `gemini-2.5-flash`）

---

## 快速参考：哪些需要分批？

| Provider    | 默认模型            | 输出上限 | 需要分批？                    |
| ----------- | ------------------- | -------- | ----------------------------- |
| `deepseek`  | `deepseek-reasoner` | 32k–64k  | ❌ 否                         |
| `qwen`      | `qwen-turbo`        | 16,384   | ❌ 否                         |
| `openai`    | `gpt-4o-mini`       | 16,384   | ❌ 否                         |
| `anthropic` | `claude-haiku-4-6`  | 64,000   | ❌ 否                         |
| `gemini`    | `gemini-2.0-flash`  | 8,192    | ⚠️ 会截断（SDK 层未实现分批） |

---

## 如何切换模型

```bash
# 使用默认模型
uv run fitness-agent cook --plan ... --provider qwen

# 指定更强的模型
uv run fitness-agent cook --plan ... --provider qwen --model qwen-turbo
uv run fitness-agent cook --plan ... --provider deepseek --model deepseek-reasoner
uv run fitness-agent cook --plan ... --provider gemini --model gemini-2.5-flash
```

## 如何启用分批（低 cap 模型）

在 `src/fitness_agent/utils/llm_client.py` 的 `_MAX_TOKENS_CAP` 字典中添加：

```python
_MAX_TOKENS_CAP: dict[str, int] = {
    "deepseek": 8192,  # 若使用 deepseek-chat
    "qwen": 8192,      # 若使用 qwen-plus 或 qwen-max
}
```

---

_最后更新：2026-02-25。模型更新频繁，请定期核对官方文档。_
