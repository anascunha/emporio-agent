# Language drift experiment — 2026-10-31

`python -m evals.language_probe --model claude-haiku-5-5 --runs 5`

**Question:** evaluation case 16 failed because Claude Haiku 5.5 answered an English-speaking
customer in Portuguese. Is that caused by the Portuguese data the tools return?

**Finding:** yes, but not only the long manual sections. Even a one-line catalog result
(Portuguese product name, R$ prices) is enough for Haiku to switch to Portuguese.
Reinforcing the rule at the end of the system prompt helped little; a short
per-message system instruction, added in code after each customer message with the
detected language, removed the drift entirely.

| Question type | Variant | Answered in Portuguese | Called get_policy |
|---|---|---|---|
| catalog (short PT product data) | prompt rule only | 5/5 | 0/5 |
| policy (long PT manual text) | prompt rule only | 4/5 | 5/5 |
| catalog + policy | prompt rule only | 4/5 | 5/5 |
| catalog (short PT product data) | per-message language hint | **0/5** | 0/5 |
| policy (long PT manual text) | per-message language hint | **0/5** | 5/5 |
| catalog + policy | per-message language hint | **0/5** | 5/5 |

Earlier run with an extra reminder at the end of the system prompt instead of the
per-message hint: 9/15 answers still in Portuguese (vs. 13/15 without it).

## Follow-up: local model (qwen2.5:3b via Ollama), customer switches language mid-conversation

Reported by Ana while testing the UI: after a Portuguese message, an English message was still
answered in Portuguese. Scenario: "Oi! Vocês abrem no sábado?" then "Ok, and how much is the
Yamaha F310? Can I pay in installments?" (the second message is detected as English).

| Where the language hint goes | Answered in English | Notes |
|---|---|---|
| System message after the customer message (what works for Claude) | 0/3 | |
| System message **and** inside the customer message | 0/5 | qwen stopped calling tools and **invented prices** (R$ 2.995, R$ 949,50…) |
| Inside the customer message only | **4/5** (earlier spot check: 2/3) | tools called every time; one wrong "unavailable" answer |

Conclusion: the hint placement is provider-specific. Claude follows a mid-conversation system
message; qwen2.5:3b's chat template handles it badly, so for Ollama the hint is appended to the
customer's message.

## Follow-up 2 (2026-11-01): the inline hint broke tool use

A scripted pass of the test checklist showed qwen inventing store facts. A/B test, 3 runs each:

| Hint placement (qwen2.5:3b) | Store info (address) | Portuguese price question | English price question | PT→EN switch |
|---|---|---|---|---|
| Inside every customer message (decision #53) | 0/3 | 0/3 | 3/3 | 4/5 |
| No hint | 3/3 | 2/3 | 3/3 | fails (original report) |
| Leading system message, every turn | address right, hours missing | 0/3 | 3/3 | 3/3 |
| **Leading system message, only after a language switch** (decision #64) | **3/3** | **2/3** | **3/3** | **3/3** |

Lesson: #53 was validated on one question (price) that happened to keep working; a full run would have caught the regression. Claude is unaffected (its hint stays a mid-conversation system message, 0/15 wrong-language answers).
