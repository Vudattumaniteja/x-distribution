# Reference: Reply Generation (5 Angles)

> **Loaded by:** SKILL.md when generating reply drafts
> **Purpose:** Create 5 distinct reply drafts per opportunity
> **Output:** Updates `data/reply_opportunities.json` with drafts
> **Dependency:** `config/post_templates.json` (reply angles + rules)

---

## Pre-Generation: Strategy Query

If NotebookLM MCP is available:
```
"I'm replying to [author] about [topic]. Post has [engagement level], posted [time] ago.
I want to [specific angle]. What reply strategies get most engagement on X?"
```
If unavailable, consult `references/strategic-framework.md` for voice rules and engagement patterns.

---

## Angle 1: Add Insight

**Strategy:** Share a relevant data point, experience, or fact the original missed.

**Template:**
```
[Acknowledge original point — 1 line]
[Your specific insight/data/experience — 1-2 lines]
[Connect back to broader implication — 1 line]
```

**Rules:**
1. Start by acknowledging the original (show you read it)
2. Insight must be NEW — not restating the original
3. Include at least one specific number or fact
4. Under 280 characters, no hype words
5. Never just say "This!" or "Great point" — add value

**Risk Level:** LOW — safest angle, consistently effective
**Best when:** Original makes a claim you can strengthen, or misses an important point

**Example:**
```
This is accurate, and the data gets more interesting when you look at adoption.

Enterprise Claude usage grew 340% in 6 months while GPT-4 usage grew 89%.

The enterprise market is shifting faster than consumer.
```

---

## Angle 2: Respectful Counter

**Strategy:** Disagree with ONE specific point using evidence, remaining constructive.

**Template:**
```
[Acknowledge what's valid — 1 line]
[State specific disagreement — 1 line]
[Provide evidence — 1-2 lines]
[Offer constructive alternative or question — 1 line]
```

**Rules:**
1. ALWAYS acknowledge valid points first (non-negotiable)
2. Disagree with ONE specific point, not the entire post
3. Must cite evidence (data, source, experience)
4. Tone: respectful — no sarcasm, no condescension
5. End with question or constructive alternative, not mic drop
6. Under 280 characters

**Risk Level:** MEDIUM-HIGH — high reward if done well, ratio risk if done poorly
**Best when:** You have strong evidence contradicting a specific claim

**Example:**
```
The benchmark improvements are real. But I'd push back on "AGI imminent."

Benchmarks test narrow task performance, not general reasoning.

We're making incredible progress on specific tasks. General intelligence is a different problem entirely.
```

---

## Angle 3: Build On Idea

**Strategy:** Extend the original thought with a logical next step or implication.

**Template:**
```
[Validate the insight — 1 line]
[Add the next logical step or implication — 1-2 lines]
[Why this matters — 1 line]
```

**Rules:**
1. Genuine validation (not "This!")
2. Extension must be a logical consequence, not a tangent
3. Must add substantive value
4. Frame as "This also means..." or "The next question is..."
5. Under 280 characters

**Risk Level:** LOW — almost always well-received
**Best when:** Original identifies a trend but doesn't explore implications

**Example:**
```
Right framing. And the next question is: who builds the verification layer?

If AI agents write 73% of code, we need automated testing and security auditing that keeps pace.

That's a $50B market waiting to be built.
```

---

## Angle 4: Ask Clarifying

**Strategy:** Ask a specific, thought-provoking question that deepens the conversation.

**Template:**
```
[Show understanding — 1 line]
[Ask ONE specific question — 1-2 lines]
[Optional: why you're curious — 1 line]
```

**Rules:**
1. Question must be specific — not "What do you think?"
2. Must demonstrate understanding (reference specific part of post)
3. Question should genuinely deepen the conversation
4. Questions about implementation, edge cases, or implications work best
5. Under 280 characters

**Risk Level:** VERY LOW — worst case: no response
**Best when:** Original presents interesting claims that raise follow-up questions

**Example:**
```
Interesting data. The question I keep coming back to: at what point does accuracy plateau?

Every model release shows big benchmark jumps, but marginal gains are shrinking.

Are we approaching the ceiling, or will the next architecture paradigm break it open?
```

---

## Angle 5: Share Experience

**Strategy:** Relate with firsthand experience or case study.

**Template:**
```
[Reference original point — 1 line]
[Share specific experience — 2-3 lines]
[Extract lesson or parallel — 1 line]
```

**Rules:**
1. Experience MUST be real — never fabricate or exaggerate
2. Must be specific (numbers, timeframes, outcomes)
3. Include a nuance or lesson (not just "it worked")
4. Acknowledge if your experience differs from the original
5. Under 280 characters

**Risk Level:** LOW-MEDIUM — genuine experience is safe; contradicting popular opinion is riskier
**Best when:** You have direct personal experience with the topic

**Example:**
```
We tested exactly this with our 8-person team.

After switching to Claude for code review: bugs -34%, ship velocity +22%.

Catch: first 2 weeks were rough. The AI needed codebase context before it was useful.

Real ROI, but patience required.
```

---

## Reply Timing Rules

| Position | Risk | Notes |
|----------|------|-------|
| 1st reply | HIGH | Looks like bot/sycophant |
| 2nd reply | MEDIUM | Better, but still early |
| **3rd-10th reply** | **IDEAL** | Sweet spot — visible but not desperate |
| 11th-30th | OK | Less visible but still viable |
| 31st-50th | LOW | Risk of being buried |
| 50+ replies | VERY LOW | Only if thread is still actively growing |

**Time-based rules:**
- Reply within 30 minutes of original post for max visibility
- If post is 1-6h old: only reply if engagement still accelerating
- Do not reply to posts older than 6 hours

---

## Reply Quality Checklist

### Mandatory (fail = regenerate)
- [ ] Under 280 characters
- [ ] Acknowledges original post
- [ ] Adds net-new value
- [ ] No hype words
- [ ] No engagement bait
- [ ] Max 1 emoji, at end only
- [ ] No tagging unless genuinely relevant

### Quality (warn = flag)
- [ ] Would the original author appreciate this?
- [ ] Would their audience find this valuable?
- [ ] Positions you as knowledgeable?
- [ ] Something you'd be proud to have associated with your name?
- [ ] Could spark meaningful conversation?

---

## Edge Cases

### Original Post is Very Long (Thread)
- Don't try to reply to the entire thread — focus on ONE specific point
- Quote the specific tweet you're responding to (not the first tweet)
- Reference: "On point 7 in your thread..."

### Original Post is in a Language You Don't Fully Understand
- Do NOT use machine translation to reply — risk of embarrassing errors
- Skip the opportunity or use Angle 4 (ask a question) with a caveat

### You've Already Replied to This Author Recently
- Check `data/reply_opportunities.json` for recent interactions
- If you replied to them in the last 24h, skip (avoid looking like a stalker)
- Exception: if they directly engaged with your previous reply

### The Reply Would Be Better as an Original Post
- If your reply is > 200 chars and doesn't directly reference the original, consider making it an original post instead
- If your reply makes a standalone point that doesn't need the original context, it should be an original post

### Multiple Reply Opportunities from the Same Author
- Reply to at most 1 post per author per day
- Choose the highest-graded opportunity
- Exception: if they directly engage with your first reply, you can reply back

### The Original Post Gets Deleted While You're Drafting
- If you discover the post was deleted, discard your draft
- Log the event: "Original post deleted before reply sent"
- Do not post the reply as an original tweet (it won't make sense without context)
