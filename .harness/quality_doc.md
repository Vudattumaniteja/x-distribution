# Quality Document

## Overall Health
Initial score: 6/10

The project has useful live automation and real data, but it needs stronger command centralization, schema validation, storage separation, and repeatable verification.

## Module Quality Scores

| Module | Verification | Understandability | Test Stability | Architecture | Conventions |
|---|---:|---:|---:|---:|---:|
| `scripts/source_*` | 8 | 8 | 7 | 8 | 8 |
| collectors | 5 | 6 | 4 | 6 | 6 |
| aggregation | 6 | 6 | 5 | 6 | 6 |
| data storage | 5 | 5 | 4 | 5 | 5 |
| docs/agents | 7 | 7 | 6 | 6 | 7 |

## Improvement Targets
1. One master CLI.
2. Schema validation gate.
3. Storage layout compatibility layer.
4. Script inventory and legacy cleanup policy.
5. End-to-end verification log.
