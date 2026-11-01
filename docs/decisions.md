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
| 40 | **Search fixed for Portuguese morphology and English vocabulary:** plurals folded to singular (`violões`/`violão`/`violao` all match), English synonyms per category (acoustic guitar → Violões, bass → Baixos, drums → Baterias…), stricter prefix matching, and results far below the best match dropped | Ana → Claude | Ana pointed out that a Portuguese-only base breaks queries. Testing confirmed it: accents were already fine, but `violão` (singular) returned **0 products**, and "acoustic guitar" returned electric guitars. |
| 41 | **Per-message language hint:** the customer's language is detected in code (stopword count, ignoring e-mails/URLs; messages without a signal keep the conversation's language) and a one-line system message ("reply in English") is added right after each customer message | Ana → Claude | Ana asked whether the Portuguese base caused the English failure. Experiment (`evals/results/language-probe.md`): Haiku answered English speakers in Portuguese 13/15 times — even after a one-line catalog result; a system-prompt reminder only brought it to 9/15; the per-message hint brought it to **0/15**. |
| 42 | **uv as the project manager**: dependency groups (`ui`, `dev`) installed by default, `uv.lock` committed, commands run with `uv run` | Ana | Faster installs and, above all, reproducibility: reviewers get exactly the versions that were tested, with one command (`uv sync`). pytest stays as the test runner (uv manages environments, it does not run tests). |
| 43 | Evaluation run 3 (final code) **stopped mid-run: the API account ran out of credits** during the judge. The console log kept the code-check results: **Sonnet, Haiku and Opus 16/16** (Haiku's English case now passes); judge scores, latency and cost were lost. The runner now **saves after every model** and **continues without the judge** if it fails | Claude | A long paid run must not lose its results to one failure. |

## 2026-10-31 — Web interface

| # | Decision | Who | Why |
|---|---|---|---|
| 44 | **Python ≥ 3.11 / Streamlit ≥ 1.66** | Claude → Ana | Python 3.10 reached end of life in October 2026 (same reasoning as #7), and with 3.10 the lock resolved Streamlit 1.65, which lacks APIs the new chat UI uses. |
| 45 | **Two channel skins** — "Mobile messenger" (phone frame, ticks, typing indicator; the customer starts) and "Website chat" (store-branded widget, proactive greeting, quick-reply buttons) — on the same `create_agent`/`Reply` API; presentation only | Ana | The manual names WhatsApp as the main remote channel and the website is the other natural one; the demo should feel like a real customer conversation. Planned by a sub-agent, reviewed before implementation. |
| 46 | **"Inspired by" styling only**: no WhatsApp name, logo or assets in the UI (tested) | Claude → Ana | Public deliverable; avoids trademarked material. |
| 47 | **Pure Streamlit + CSS** (keyed containers styled through `st-key-*` classes), no chat component library; model text only through `st.markdown`, with `$` escaped | Claude → Ana | No new dependency; safe rendering. Without escaping, "R$ 1.000 … R$ 2.000" would render the text between the two `$` as LaTeX. |
| 48 | **One conversation per channel**, agent created on the first message; the tool-call viewer is **off by default** and shows a collapsed developer note under each reply | Claude → Ana (default off: Ana) | Separate sessions as in real life; the demo starts as the customer sees it and the reasoning path is revealed live. |
| 49 | UI tested with Streamlit's AppTest and a **fake agent** (8 tests: load, send, channel switch, quick reply, separate histories, tool toggle, error notice, no trademark) | Claude | The interface is verified without network or API cost. |
| 50 | **User guide for the store team** (`docs/USER_GUIDE.md`, English, non-technical): what Mel does, how to run it, a hands-on test checklist with real test orders, troubleshooting, FAQ and a glossary | Ana | The README is for reviewers; a client handover needs a plain-language guide. Written by a sub-agent from the code and data; every value checked against the data before committing. |
| 51 | **UI redesign in the store's colors**: dark navy base + orange accent, navy-biased neutrals, Bricolage Grotesque (display) + DM Sans (body). Messenger: navy header, orange avatar/ticks, soft-orange customer bubbles, **music-staff wallpaper**. Website: store page with real facts from the manual (address, hours, PIX, shipping) + widget with orange header, navy customer bubbles, quick-reply pills | Ana (colors) + Claude (design) | Ana asked for orange and dark blue; the staff wallpaper and the manual facts make the page specific to this store. Checked with headless-Chrome screenshots. |
| 52 | **Light / Dark / Auto selector** in the sidebar driving our own palette (page, sidebar, chat); `?channel=` and `?theme=` URL parameters; brand orange as Streamlit's primary color (`.streamlit/config.toml`) | Ana (toggle) + Claude | Streamlit's own theme cannot be switched at runtime, so the app paints page and sidebar from the same tokens; URL parameters give direct demo links. |
| 53 | **Language-hint placement per provider**: Claude keeps the mid-conversation system message; **Ollama gets the hint inside the customer's message** | Ana → Claude | Ana noticed that with Ollama, switching from Portuguese to English mid-conversation still got Portuguese answers. Experiment: system-message hint 0/3 English; system + inline 0/5 and qwen started inventing prices without calling tools; inline only 4/5 with tools always called. The language is per message, not per session. |
| 54 | **Example conversations exported from evaluation run 2** (`scripts/export_examples.py`, no API calls): 5 Sonnet conversations in `examples/` plus `examples/model-comparison.md` with the same 3 questions answered by all 5 models tested (Sonnet, Haiku, Opus, qwen2.5:3b, llama3.2) | Claude → Ana (comparison file: Ana) | The API credits ran out; these are real conversations of the default model, labeled with their source. Ana asked to keep the Haiku and Opus results in the project too. `scripts/generate_examples.py` regenerates fresh ones with the final code when credits are available. |
| 55 | **Interface text in English by default, Portuguese optional** (sidebar selector or `?lang=pt`); texts live in `chat_ui/i18n.py`. Mel still answers in each customer's language | Ana | The deliverable is reviewed in English ("all responses must be in English" refers to the deliverable); the Portuguese option fits a Brazilian store's real customers. |

## 2026-11-01 — Language consistency before delivery

| # | Decision | Who | Why |
|---|---|---|---|
| 56 | **Example 05 is now the English-speaking customer** (real Sonnet conversation, case 16 of run 2); the prompt-injection case moved to `model-comparison.md`; the README explains why the other four examples are in Portuguese | Claude → Ana | The deliverable is read in English and all five examples were in Portuguese; this keeps the store's real (Brazilian) conversations while showing Mel in English, without spending API credits. |
| 57 | **User Guide test messages in English**, store data kept as-is (product names, address, R$ format), plus **one deliberate Portuguese test** | Claude → Ana | Consistent English deliverable; the single Portuguese test demonstrates the bilingual behavior instead of mixing languages throughout. |
| 58 | **Fallback reply follows the conversation's language** (English or Portuguese); the rare refusal message is bilingual | Claude | Found while reviewing for English consistency: an English-speaking customer would have received the error fallback in Portuguese. |
| 59 | **qwen2.5:3b reading "under R$ 1,000" as a minimum price is documented, not patched in code**; the search tool keeps clearer parameter descriptions, echoes the price filter it applied, and rejects impossible ranges; evaluation case 17 measures it | Ana | Found in manual testing. Two tool-side fixes failed on qwen (0/5 each). A code guard that rewrites the model's arguments from the customer's words was considered and rejected: it would only patch a small-model weakness, while the default model is Claude. |
| 60 | **Price values in tool results carry their meaning** ("paid at once via PIX, 5% off"; "credit card, interest-free, no PIX discount") | Ana → Claude | Manual test 2: qwen mixed PIX with card installments. With self-explaining values it kept them apart in 4/4 runs. Unlike #59 this helps every model at no cost. |
| 61 | **Recoverable error when a product name is passed as `product_id`** (instead of a raw Python error) | Claude | Manual test 3. Consistent with #20 (errors the model can act on). It did not rescue llama3.2 (0/5), which fits its place as the weakest model in the evaluation. |
| 62 | **llama3.2 removed from the web chat's model list and from the default evaluation models**; its results stay in the reports | Claude → Ana | Weakest model in every run (6–8/16, ~15 s per reply) and failed basic lookups in manual testing (#61). Fewer weak options in the UI; the comparison evidence is kept. qwen2.5:3b remains the free, offline option. |
