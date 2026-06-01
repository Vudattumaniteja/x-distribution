# Reference: Post Grading (100-Point System)

> **Loaded by:** SKILL.md when grading tweet variants
> **Purpose:** Score drafts against the X algorithm (0-100 points)
> **Output:** Updates `data/approved_posts.json` with scores and rankings
> **Dependency:** `config/grading_weights.json` (exact formulas)

---

## Scoring Dimensions (6 Dimensions, 100 Points + Penalties)

Before grading, if NotebookLM MCP is available, query for current engagement patterns. If not, use `references/algorithm-reference.md` for calibration.

---

## Dimension 1: Hook Strength (0-15 points)

### Pattern Interruption (0-5)
| Score | Criteria | Test |
|-------|----------|------|
| 0 | Generic hook ("Things are changing") | Would anyone stop scrolling? |
| 1 | Slightly specific but predictable | Might slow the scroll slightly |
| 2 | Has number/name but doesn't surprise | Could work for the right audience |
| 3 | Decent hook | Might slow the scroll |
| 4 | Strong hook | High chance of stopping scroll |
| 5 | Stop-the-scroll hook | Impossible to ignore |

### Specificity (0-5)
| Score | Criteria |
|-------|----------|
| 0 | No specifics, all vague |
| 1 | One semi-specific element |
| 2 | Name or number present but not surprising |
| 3 | Specific name + number |
| 4 | Highly specific with unexpected detail |
| 5 | Maximum specificity — number, name, and claim all precise |

### Curiosity Gap (0-5)
| Score | Criteria |
|-------|----------|
| 0 | Self-contained, nothing to wonder about |
| 1 | Mild interest, no tension |
| 2 | Some curiosity but can guess the answer |
| 3 | Genuine curiosity about what comes next |
| 4 | Strong gap — need to read the rest |
| 5 | Must-read — the gap is almost uncomfortable |

---

## Dimension 2: Algorithm Signal Potential (0-20 points)

### Bookmark-Worthiness (0-8)
| Score | Criteria | Indicators |
|-------|----------|-----------|
| 0 | Ephemeral, no reason to save | One-time news, no reference value |
| 2 | Might be useful to some | Useful for specific audience segment |
| 4 | Useful for broad audience | Framework, checklist, or reference |
| 6 | Useful for most people | Practical data or tool recommendation |
| 8 | "I need to remember this" | Insight that changes how you think/work |

### Repost-Worthiness (0-7)
| Score | Criteria |
|-------|----------|
| 0 | Too niche or generic to share |
| 2 | Might share with a specific person |
| 4 | Would share in relevant group chat |
| 5 | Would share as standalone post |
| 7 | "Saw this and thought of you" energy |

### Reply-Trigger (0-5)
| Score | Criteria |
|-------|----------|
| 0 | Closed statement, nothing to respond to |
| 1 | Might get low-effort replies ("great point") |
| 2 | Could generate substantive replies |
| 3 | Clear invitation for discussion |
| 4 | Will generate diverse perspectives |
| 5 | Conversation starter — people must add their take |

---

## Dimension 3: Phoenix Potential (0-15 points)

### Out-of-Network Appeal (0-8)
| Score | Criteria |
|-------|----------|
| 0 | Only makes sense to your existing followers |
| 2 | Could interest AI-curious non-followers |
| 4 | Broad AI community appeal |
| 6 | Cross-domain appeal (tech + business, etc.) |
| 8 | Mainstream tech appeal |

### Topic Alignment (0-7)
| Score | Criteria |
|-------|----------|
| 0 | Disconnected from current discourse |
| 2 | Loosely related to trending topics |
| 4 | Directly related to current AI conversations |
| 5 | Perfectly timed with a breaking topic |
| 7 | Early in trending conversation — first-mover advantage |

---

## Dimension 4: Voice Compliance (0-20 points)

### Scoring Method (start at max, subtract for violations)
- **Calm Authority (max 5):** -1 per hype word found (check forbidden words list)
- **Concrete-First (max 5):** -1 per vague opener, -2 if first line has zero concrete elements
- **Numbers Everywhere (max 5):** 0=no numbers, 2=one vague number, 3=one specific, 4=two specific, 5=three+
- **Anti-Fluff (max 5):** -1 per filler phrase (in order to, it's important to note, at the end of the day)

---

## Dimension 5: Dark Social Potential (0-15 points)

### Screenshot-Worthiness (0-5)
| Score | Criteria |
|-------|----------|
| 0 | Standard text, nothing special |
| 1 | Clean formatting, maybe screenshot-worthy |
| 3 | Strong one-liner or data point |
| 5 | Highly visual data or quotable line |

### DM-Shareability (0-5)
| Score | Criteria |
|-------|----------|
| 0 | Too niche or generic |
| 2 | Might share in specific group chat |
| 3 | Work-related chat share |
| 4 | Multiple group chats |
| 5 | "Sending this to the group" instant forward |

### Self-Contained (0-5)
| Score | Criteria |
|-------|----------|
| 0 | Requires thread or link to understand |
| 2 | Mostly standalone, better with context |
| 3 | Understandable without context |
| 5 | Perfectly self-contained |

---

## Dimension 6: Risk Penalties (0 to -15 points)

### Ratio Risk (0 to -5)
| Score | Criteria | Check |
|-------|----------|-------|
| 0 | No ratio risk | No reasonable counterargument |
| -2 | Mild risk | Could get pushback |
| -3 | Moderate risk | Controversial claim |
| -5 | High risk | Likely significant pushback |

### Engagement Bait (0 to -5)
| Score | Criteria |
|-------|----------|
| 0 | Genuine content |
| -2 | Slightly bait-y |
| -3 | Noticeably bait-y |
| -5 | Obvious engagement bait |

### Saturation Check (0 to -5)
If NotebookLM MCP is available, query: "Has [topic] been heavily covered on X in the last 48 hours?"
| Score | Criteria |
|-------|----------|
| 0 | Fresh angle |
| -2 | Trending but somewhat unique |
| -3 | Trending, similar to others |
| -5 | Completely saturated |

---

## Score Interpretation

| Score | Rating | Action |
|-------|--------|--------|
| 85-100 | Excellent | Post immediately |
| 70-84 | Good | Post with confidence |
| 55-69 | Acceptable | Post if timing is right |
| 40-54 | Needs Work | Consider revising |
| 25-39 | Weak | Significant revision needed |
| Below 25 | Skip | Do not post |

---

## Edge Cases

### User Disagrees with Grade
- Ask what they think the score should be and why
- If systematic pattern (user consistently disagrees with one dimension), suggest recalibrating grading_weights.json
- Single disagreement: note it, don't auto-adjust

### Grade is Borderline (e.g., 54 vs 55)
- Always round in favor of the user — if it's close to the next tier, present both options
- Show the breakdown so the user can see which dimension is holding it back

### Two Variants Have the Same Score
- Use the "dark_social_potential" as tiebreaker — higher dark social wins
- If still tied: use "hook_strength" as second tiebreaker
- Present both with notes on their different strengths

### All Variants Score Below 55
- This means the news item may not be strong enough for a standalone post
- Suggest repurposing as a reply instead
- Or suggest combining with another news item
- Don't force a low-quality post

### Post Would Score High But Has Risk Penalties
- Present the trade-off clearly: "This variant scores 78 raw but -6 in risk penalties = 72. The ratio risk is moderate because [reason]."
- Let the user decide whether to accept the risk

---

## Grade Output Format
```json
{
  "variant_id": 1,
  "variant_name": "Hook-Accuracy",
  "total_score": 78,
  "raw_score": 78,
  "risk_adjusted_score": 72,
  "rating": "Good",
  "breakdown": {
    "hook_strength": {"score": 12, "max": 15},
    "algorithm_signal_potential": {"score": 15, "max": 20},
    "phoenix_potential": {"score": 10, "max": 15},
    "voice_compliance": {"score": 18, "max": 20},
    "dark_social_potential": {"score": 11, "max": 15},
    "risk_penalties": {"score": -2, "max": 0, "min": -15}
  },
  "top_2_strengths": ["string", "string"],
  "top_2_weaknesses": ["string", "string"],
  "suggested_improvement": "string"
}
```
