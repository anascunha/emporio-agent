# Manual tests

Dialogs tested by hand in the Streamlit app before delivery, following the test script in the [User Guide](USER_GUIDE.md#5-how-to-test-mel). Each row records what Mel did and what was done about it.

Legend: ✅ correct · ⚠️ acceptable with a caveat · ❌ wrong

| # | Date | Channel / model | Customer message | What Mel did | Verdict | Follow-up |
|---|---|---|---|---|---|---|
| 1 | 2026-11-01 | Website · `ollama/qwen2.5:3b` | "Which acoustic guitars do you have under R$ 1,000?" | Called `search_products` with `min_price=1000` instead of `max_price`, then listed guitars from R$ 1.049 to R$ 1.349 as "under R$ 1,000". Reproduced 5/5 times. In Portuguese ("até R$ 1000") the same model filters correctly. | ❌ | Small-model limitation (decision #59). Tried clearer parameter descriptions plus echoing the applied filter (0/5) and renaming the parameters to `price_up_to`/`price_from` (0/5); kept the first, reverted the rename. Added evaluation case 17 so it is measured for every model, and documented it in the README limitations. Not reproducible with Claude right now (no API credits). |
