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
