# Decision log

Chronological record of the project's decisions. It backs the "Use of AI coding assistants" section of the README: it shows what I decided, what Claude (Claude Code) proposed, and why.

Legend: **Ana** = my decision · **Claude → Ana** = option proposed by Claude and chosen by me · **Claude** = implementation detail proposed by Claude and accepted.

## 2026-10-31 — Starting point

| # | Decision | Who | Why |
|---|---|---|---|
| 1 | Discard an automatically generated first version and **start from scratch**, building in steps | Ana | That version contained decisions I had not made, and a commit history where every commit had the same timestamp. The challenge asks for a history showing real progress, and I want to be able to defend every choice. |
| 2 | **Pluggable LLM: Claude (Anthropic API) by default + local Ollama** as an alternative | Claude → Ana | Claude is more reliable at function calling; Ollama lets the project run with no API key and no cost. My GPU (GTX 1650, 4 GB) only runs ~3B models well, and those make more tool-selection mistakes. |
| 3 | **Function calling with deterministic tools**, no RAG and no SQL agent | Claude → Ana | Price, promotions, stock, installments and deadlines live in testable code. The LLM decides *when* to look something up and *how* to explain it; code decides *what is true*. The manual says wrong information may count as false advertising (7.1). |
| 4 | **Policies through a `get_policy(topic)` tool** that returns the whole manual section | Claude → Ana | The manual is 8 pages long: embeddings would be overkill, and chunks can split a rule from its exception. Putting the whole manual in the prompt would work, but the agent would not demonstrate deciding *when* to check a policy, which is a challenge criterion. |
| 5 | **Plain SDKs** (hand-written function-calling loop), no LangChain/LangGraph | Claude → Ana | Short, transparent loop that is easy to explain; few dependencies. |
| 6 | **Interface: CLI + Streamlit** on top of the same agent core | Ana | CLI so reviewers can run it quickly; Streamlit for the interview demo. |
| 7 | Python ≥ 3.10, environment managed with `uv` | Claude | Python 3.9 is past end of life. |
| 8 | **Repository in English** (code, docs, commits); **the agent answers in the customer's language** (Portuguese or English) | Ana | The deliverable is reviewed in English; the store's customers and its manual are Brazilian. |

## 2026-10-31 — Data handling

| # | Decision | Who | Why |
|---|---|---|---|
| 9 | **"Today" is fixed at 2026-03-23** (configurable via `EMPORIO_TODAY`) | Claude → Ana | The latest order is from 2026-03-22. Using the real date would make every pending order seven months old and every 7/30-day deadline expired. |
| 10 | Order lookups require **order number + registered e-mail or phone**, checked in code | Claude → Ana | LGPD (manual section 9). Order IDs are 1–20, so anyone could read someone else's order by guessing. Verification in code means the LLM cannot skip it. |
| 11 | Installments follow **item 3.1 tiers** (up to 3x: ≥ R$ 50 per installment; 4–6x: ≥ R$ 80; 7–12x: ≥ R$ 100), not the "R$ 100 minimum" in the summary table | Claude → Ana | The manual contradicts itself; the more specific rule wins over the summary. |
| 12 | Return and warranty windows count from **`estimated_delivery`** (there is no actual delivery date); the agent says it is an estimate | Claude → Ana | Closest to the manual and the consumer-protection code ("after receipt"). |
| 13 | Only promotions with `is_active = 1` count; if a product had two active ones, the larger discount wins. Price filters use the final (promotional) price | Claude | 21 of 25 promotion rows are inactive (e.g. Takamine GD20). Manual 7.3: never promise an expired discount. |
| 14 | Product descriptions that mention a brand missing from the product name are **dropped**; the agent relies on name + specs | Claude | Several rows describe another instrument (e.g. "Music Man Bass 1X" described as a Fender Jazz Bass, a "61-key" synth described as 88-key Roland). Repeating them would mislead customers. |
| 15 | The same answer for "order not found" and "contact does not match" | Claude | Does not reveal which order numbers exist. |
| 16 | The policy PDF is **transcribed by hand to Markdown** (`data/politicas_da_loja.md`, kept in Portuguese) instead of parsed at runtime | Claude | Automatic extraction outputs one word per line and loses every table (payment, hours, shipping). The source text is unchanged. |
| 17 | Manual contradictions get a fixed **clarification note** appended to the topic: both phone numbers given with their purpose; e-mail without the accent; item 3.1 prevails for installments; wind/orchestral instruments are mentioned but not in the catalog | Claude | The agent must apply the same interpretation every time instead of picking one at random. |

## 2026-10-31 — Tools

| # | Decision | Who | Why |
|---|---|---|---|
| 18 | **Six tools**: `search_products`, `get_product_details`, `get_order_status`, `check_return_options`, `get_policy`, `escalate_to_human` | Claude → Ana | One tool per kind of question in the challenge; few enough for a small local model to choose correctly. |
| 19 | Tool results carry **prices already formatted** (`R$ 1.967,18`) and installment options precomputed | Claude | The LLM only explains numbers, never calculates them. |
| 20 | Tool errors are **returned to the model** as JSON instead of raised | Claude | The model can recover (e.g. ask the customer for the missing e-mail) instead of the conversation crashing. |
| 21 | Defect exchanges count **30 days from purchase** (4.2); the legal warranty counts **90 days from receipt** (8.1) | Claude | That is literally what each section says; it creates the non-trivial case where a store exchange has expired but the legal warranty still applies. |
| 22 | Failed order verifications are **locked after 5 attempts** per conversation | Claude | Prevents enumerating orders by trying e-mails/phones. |
| 23 | Escalations are appended to `data/runtime/escalations.jsonl` (git-ignored) with a protocol number | Claude | Simulates handing the case to the team (manual 7.3: complaints get a reply within 24 business hours). |

## 2026-10-31 — Agent, prompt and LLM backends

| # | Decision | Who | Why |
|---|---|---|---|
| 24 | Persona **"Mel"** (from *melodia*), informal but professional, answering in the customer's language | Ana | Short, friendly name for a WhatsApp-like channel; tone required by manual 7.1. |
| 25 | **Claude Sonnet 5.5** as the default model, to be confirmed by a model-comparison **evaluation** | Ana | Good balance of tool-use quality, speed and cost for customer service; the evaluation should back the choice with data instead of intuition. |
| 26 | Reasoning effort **`low`** by default (configurable) | Claude | Chat answers should be fast; the hard rules live in the tools, not in long reasoning. |
| 27 | Each backend keeps the history in its **native format** behind a 4-method `ChatSession` interface | Claude | Anthropic replies carry thinking blocks that must be sent back unchanged; Ollama uses `tool` messages. A common format would lose information. |
| 28 | **Prompt caching** of system prompt, tools and history on Anthropic | Claude | They are resent every turn; caching cuts cost and latency. |
| 29 | At most **6 tool rounds** per customer message, then a polite fallback | Claude | A confused model cannot loop forever. |
| 30 | Ollama: recover tool calls that a small model writes as JSON in the text | Claude | Common failure of 3B models; only accepted when the name matches a real tool. |

First local run (qwen2.5:3b on a GTX 1650): price question answered correctly via `search_products`, but the opening-hours question was answered **without calling `get_policy`** (evasive answer), ~1 min per reply. Evidence for #2 and input for the evaluation.
| 31 | Streamlit app in `streamlit_app.py` with provider/model selector and an optional **tool-call viewer** | Claude | Shows the agent's reasoning path (which tool, which arguments, what came back) during the interview demo. |

## 2026-10-31 — Model evaluation

| # | Decision | Who | Why |
|---|---|---|---|
| 32 | Build an **evaluation to choose the model** instead of picking by intuition | Ana | The model choice must be justified in the README with evidence. |
| 33 | 16 cases (`evals/cases.json`) covering every challenge criterion: catalog, prices, promotions, stock, store info, orders with/without verification, the non-trivial return case, complaint, accessories, unrelated questions, prompt injection, English | Claude → Ana | One case per behavior the challenge asks for, plus the traps found in the data. |
| 34 | Grading = **deterministic checks** (right tool, expected facts present, forbidden facts absent, answer language) **+ LLM-as-judge** (Claude Opus 5.5 scoring grounding, tone, helpfulness and policy adherence, 1–5) | Ana | Code checks are reproducible and free but blind to tone and hallucinations; the judge sees the tool results, so it can flag invented facts. |
| 35 | The judge is skipped automatically when no API key is set; Claude models are skipped too | Claude | The evaluation still runs fully offline with Ollama models. |
| 36 | Evaluation run 1 (baseline, `evals/results/run1-baseline.md`): Sonnet 15/16, Opus 15/16, Haiku 14/16, qwen2.5:3b 8/16, llama3.2 6/16. Reviewing every failure by hand found **three kinds of problems** | Ana + Claude | Raw scores alone would have been misleading. |
| 37 | **Judge bias fixed:** the judge now receives Mel's system prompt. It was grading rules Mel legitimately knew ("team replies within 24 business hours", "PIX does not stack with promotions") as invented, which penalized the most thorough model (Sonnet) | Claude → Ana | The judge must know what the agent was told, or grounding scores are unfair. |
| 38 | **Check too strict fixed:** case 05 now also accepts "saiu de linha" / "não está mais no nosso catálogo" | Claude | Opus answered correctly and was marked as failed. |
| 39 | **Prompt tightened for real failures:** register complaints right away without asking permission (manual 7.3 says "register and forward"; Sonnet and Haiku asked "do you want me to register it?"), and report deadlines exactly as tools return them (Sonnet said a warranty with 56 of 90 days left was "almost over") | Claude → Ana | Both are genuine behavior gaps found by the evaluation, fixed at the prompt level. |
