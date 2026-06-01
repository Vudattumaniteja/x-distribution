# Reference: Post Generation (5 Tweet Variants)

> **Loaded by:** SKILL.md when generating post variants
> **Purpose:** Transform verified news into 5 distinct tweet formats
> **Output:** `data/approved_posts.json` — tweet drafts
> **Dependency:** `config/post_templates.json` (templates + hard rules)

---

## Pre-Generation: NotebookLM / Strategy Query

If NotebookLM MCP is available, query before generating:
```
"I'm writing an X post about [specific topic]. The variant is [variant name].
The source is [source name] with [key data point].
What hook patterns and engagement strategies work best for this content type?"
```

If MCP is unavailable, consult `references/strategic-framework.md` for:
- Pattern interruption techniques
- Dark social optimization
- Content pillar alignment
- Voice rules

---

## Variant 1: Hook-Accuracy

**Strategy:** Pattern-interruption hook → precise factual claim → implication → source

**Template:**
```
[HOOK — under 80 chars, no hype, creates urgency/curiosity]
[PRECISE CLAIM with specific number, name, or fact]
[WHY IT MATTERS — one line of implication]
[SOURCE — attribution]
```

**Rules:**
1. Hook MUST be under 80 characters
2. Claim MUST contain at least one specific number
3. Source MUST be a real URL or clear attribution
4. Total tweet under 280 characters
5. No forbidden words or openers (see SKILL.md)
6. Max 1 emoji at end

**Best for:** Announcements, fundraising, product launches, breaking news
**Avoid for:** Opinion pieces, complex tutorials, nuanced analysis

**Example:**
```
$47M for a 2-person AI startup.

Anthropic led a Series B for a tool that writes 73% of its own features.

The age of 500-person dev teams building simple apps is ending.

Source: TechCrunch
```

---

## Variant 2: Value-Driven

**Strategy:** Lead with what the reader gains — a framework, insight, or actionable takeaway

**Template:**
```
[VALUE PROPOSITION — what the reader gains, 1 line]
[CONTEXT — the news supporting this value, 1-2 lines]
[SPECIFIC TAKEAWAY — something the reader can use]
[OPTIONAL SOURCE]
```

**Rules:**
1. Open with "X things..." or "Here's what..." or outcome frame
2. Must include at least one actionable insight
3. Context: 1-2 lines maximum
4. Takeaway must be specific (not "stay informed")
5. Under 280 characters

**Best for:** Tool updates, research papers, trend analysis, how-to content
**Avoid for:** Breaking news, controversial topics

**Example:**
```
3 things GPT-5's benchmark reveals for your workflow:

1. Multimodal reasoning is production-ready
2. 1M token context changes how we build RAG
3. Code generation = mid-level engineer quality

Adapt now or spend Q4 catching up.
```

---

## Variant 3: Data Bomb

**Strategy:** Standalone surprising number → context → implication → source

**Template:**
```
[SURPRISING NUMBER — standalone, no other text on this line]
[CONTEXT — what this number means, 1-2 lines]
[IMPLICATION — what it enables or changes]
[SOURCE]
```

**Rules:**
1. Number MUST be completely standalone on first line
2. Include %, $, or unit for specificity
3. Context must explain WHY this number is surprising
4. Must include a comparison or frame of reference
5. Source required
6. Under 280 characters

**Best for:** Benchmark results, research findings, market data, statistics
**Avoid for:** Qualitative news, opinion pieces, narrative content

**Example:**
```
89.7%.

That's GPT-5's accuracy on medical diagnosis questions — outperforming the average doctor.

We're not replacing doctors. We're giving every clinic a second opinion that never sleeps.

Source: OpenAI technical report
```

---

## Variant 4: Founder-Focused

**Strategy:** Center narrative on a founder/company and their decision or journey

**Template:**
```
[FOUNDER/COMPANY + BOLD ACTION — 1 line]
[WHAT THEY DID — specifics, 1-2 lines]
[WHAT THIS SIGNALS — industry implication]
[OPTIONAL: YOUR TAKE — 1 line]
```

**Rules:**
1. First line MUST include a person's name or company name
2. Must describe a specific action, decision, or bet
3. Signal line must connect to a broader trend
4. Can include mild opinion in final line
5. Under 280 characters

**Best for:** Company news, strategy shifts, founder statements, M&A
**Avoid for:** Technical deep-dives, pure data posts, tool reviews

**Example:**
```
Dario Amodei bet Anthropic's future on AI safety as a moat.

Claude self-corrects harmful outputs 94% of the time without human oversight.

If safety becomes a competitive advantage, the careful companies win.
```

---

## Variant 5: Technical Deep

**Strategy:** ONE specific technical detail that most coverage misses → plain language explanation → implication → source

**Template:**
```
[ONE SPECIFIC TECHNICAL DETAIL — precise, technical]
[WHY IT MATTERS — in plain language, 1 line]
[WHAT IT ENABLES — what this makes possible]
[SOURCE OR PAPER LINK]
```

**Rules:**
1. Must include a specific technical term or architecture detail
2. "Why it matters" MUST be accessible (explain to a non-expert)
3. Should teach something the reader didn't know
4. Must link to source paper, docs, or blog
5. Under 280 characters

**Best for:** Research papers, architecture releases, technical blog posts, benchmarks
**Avoid for:** Mainstream news, non-technical audiences, general commentary

**Example:**
```
GPT-5 uses mixture-of-experts with 128 experts, activates only 12 per token.

Result: 10x cheaper to run than a dense model of equivalent capability.

A router network learned which expert handles which concept type.

Paper: arxiv.org/xxxx
```

---

## Post-Generation Quality Checklist

### Mandatory Checks (fail = regenerate)
- [ ] Under 280 characters
- [ ] At least one specific number
- [ ] Source attribution present
- [ ] No forbidden words (insane, mind-blowing, game-changing, etc.)
- [ ] No forbidden openers (Thread 🧵, Hot take:, etc.)
- [ ] Max 1 emoji, at end only
- [ ] No engagement bait patterns
- [ ] All claims factually accurate (from verified news item)

### Quality Checks (warn = flag for review)
- [ ] First line creates genuine curiosity
- [ ] Post adds value beyond just sharing news
- [ ] Understandable without thread context
- [ ] Clear takeaway or point of view
- [ ] Not a verbatim copy of source headline

---

## Edge Cases

### News Item Doesn't Fit Any Variant Well
- If the news is purely opinion with no data → lean toward Founder-Focused or use as reply opportunity instead
- If the news is very technical → Technical Deep is the only option; if it's too complex for 280 chars, create a thread
- If the news is multiple related items → pick the most impactful one; don't try to cram everything in

### Source Attribution is Complicated
- If there are 3+ sources: "Multiple sources report" + name the primary one
- If the source is a paywalled article: cite it but add "Source: [Outlet] (paywalled)" so readers know
- If the source is a social media post with no article: cite the handle and date
- If the source is an anonymous leak: "According to a leaked document obtained by [Outlet]"

### Character Count is Over 280
- Don't just trim — restructure. The most important content should fit naturally
- Try: remove one line from the template (usually the "why it matters" line can be folded into the claim)
- If truly essential content exceeds 280 chars: convert to a thread (first tweet = hook, second tweet = details)
- NEVER just cut mid-sentence

### Multiple News Items About the Same Event
- Generate variants for the STRONGEST version of the story (most sources, best data)
- Note in the output: "Also covered by [other sources] with similar details"
- Don't generate 5 variants × 3 sources = 15 variants. 5 variants × 1 best source = 5 variants.
