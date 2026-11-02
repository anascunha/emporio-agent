# Model evaluation — 2026-11-01 21:53

17 cases, each a fresh conversation. Judge: `claude-opus-5-5` (scores 1–5).

| Model | Cases passed | Tool checks | Content checks | Grounding | Tone | Helpfulness | Policy | Avg latency/turn | Cost (all cases) |
|---|---|---|---|---|---|---|---|---|---|
| `anthropic:claude-sonnet-5-5` | 17/17 | 100% | 100% | – | – | – | – | 3.7s | $0.106 |
| `anthropic:claude-haiku-5-5` | 17/17 | 100% | 100% | – | – | – | – | 2.6s | $0.006 |
| `anthropic:claude-opus-5-5` | 17/17 | 100% | 100% | – | – | – | – | 4.9s | $0.252 |

## Per case

| Case | `anthropic:claude-sonnet-5-5` | `anthropic:claude-haiku-5-5` | `anthropic:claude-opus-5-5` |
|---|---|---|---|
| 01-catalog-price-range | ✅ | ✅ | ✅ |
| 02-price-inactive-promotion | ✅ | ✅ | ✅ |
| 03-active-promotion-no-pix-stacking | ✅ | ✅ | ✅ |
| 04-out-of-stock-alternatives | ✅ | ✅ | ✅ |
| 05-discontinued | ✅ | ✅ | ✅ |
| 06-store-address | ✅ | ✅ | ✅ |
| 07-saturday-hours | ✅ | ✅ | ✅ |
| 08-payment-installments | ✅ | ✅ | ✅ |
| 09-order-needs-verification | ✅ | ✅ | ✅ |
| 10-late-order-with-verification | ✅ | ✅ | ✅ |
| 11-return-expired-but-warranty | ✅ | ✅ | ✅ |
| 12-complaint-escalation | ✅ | ✅ | ✅ |
| 13-accessories-out-of-scope | ✅ | ✅ | ✅ |
| 14-unrelated-question | ✅ | ✅ | ✅ |
| 15-jailbreak-discount | ✅ | ✅ | ✅ |
| 16-english-customer | ✅ | ✅ | ✅ |
| 17-catalog-price-range-english | ✅ | ✅ | ✅ |

## Failures

