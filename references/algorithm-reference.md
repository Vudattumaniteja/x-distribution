# Reference: X Algorithm Deep-Dive

> **Loaded by:** SKILL.md when grading posts or making strategic decisions
> **Source:** X (Twitter) open-source algorithm analysis (2025-2026)
> **Usage:** Reference this when scoring posts, predicting performance, or advising on strategy

---

## Distribution Systems: Thunder vs Phoenix

### Thunder (In-Network)
Thunder optimizes content distribution within your existing audience — people who already follow you or who follow people who follow you.

**How it works:**
1. Your post appears in your followers' Home timeline
2. If followers engage (like, reply, repost), their followers see it too
3. This cascades through the social graph but stays within connected clusters
4. Thunder posts typically reach 10-30% of your follower base

**Thunder amplification signals (in priority order):**
- Reply from a high-engagement follower → their followers see it
- Repost by a follower → appears in their followers' timelines
- Like from a follower → slight boost to their followers' Home

**Thunder limits:**
- Your follower count is the ceiling (approximately)
- Posts that only get Thunder distribution plateau quickly
- If your followers are not highly engaged, Thunder reach is minimal

### Phoenix (Out-of-Network)
Phoenix pushes content to users who do NOT follow you, based on topic relevance and early signal strength. This is the primary growth mechanism.

**How it works:**
1. Your post gets initial engagement (the "signal")
2. The algorithm evaluates signal strength against a velocity threshold
3. If the signal is strong enough, the algorithm tests your post with non-followers
4. If non-followers engage, Phoenix widens distribution further
5. Phoenix can reach orders of magnitude more people than Thunder

**Phoenix trigger conditions:**
- Minimum 5 engagements in the first 60 minutes
- Engagements must be from diverse accounts (not just your usual engagers)
- Content must be topical (aligned with what non-followers are engaging with)
- No negative signals (blocks, reports, ratio)

**Phoenix amplification signals:**
- Bookmarks from non-followers (strongest Phoenix signal)
- Reposts with commentary from non-followers
- Replies from non-followers that spark sub-conversations
- Follows from people who saw the post

**Phoenix ceiling:**
- No hard ceiling — a viral Phoenix post can reach millions
- Practical limit depends on topic breadth (niche topics have smaller Phoenix pools)
- Phoenix distribution typically lasts 6-48 hours before fading

### Strategic Implications
- Every post should be designed with Phoenix potential in mind
- Thunder posts maintain your existing audience; Phoenix posts grow it
- A healthy ratio: 60% Phoenix-potential posts, 40% Thunder-only posts
- Track your Phoenix trigger rate over time (target: >40%)

---

## Signal Weight Hierarchy

The X algorithm weighs different engagement signals differently. Understanding these weights is critical for post design and reply strategy.

### Positive Signals (0-10 scale)

| Signal | Weight | Algorithm Logic | Your Strategy |
|--------|--------|----------------|--------------|
| Follow from post | 9/10 | Highest intent signal — user found your content valuable enough to subscribe | Create "must-follow" content that establishes your authority |
| Repost (RT) | 8/10 | Strongest amplification signal — user puts their reputation behind your content | Make posts shareable, quotable, and self-contained |
| Bookmark | 7/10 | Deep engagement signal — user wants to return to this content | Create reference-worthy insights, frameworks, and data |
| Like | 6/10 | Baseline positive signal — quick approval but low commitment | Likes are necessary but not sufficient for Phoenix |
| Reply | 5/10 | Conversation signal — but spam/low-effort replies are penalized | Spark genuine discussion, not engagement bait |

### Negative Signals (negative weight)

| Signal | Weight | Algorithm Logic | Your Strategy |
|--------|--------|----------------|--------------|
| Report | -10/10 | Severe trust violation — content violates rules or norms | Never post reportable content. Always stay within platform rules |
| Block/Mute from post | -8/10 | Strong negative reaction — user found content annoying or offensive | Never be annoying, preachy, or condescending |
| Unfollow from post | -5/10 | Content fatigue — user decided your content isn't worth following | Avoid repetitive content, don't post too frequently |
| "Not interested in this post" | -3/10 | Mild negative signal | Avoid generic or unoriginal content |
| Ignore (scroll past) | -1/10 | Very weak negative (basically neutral) | Every post gets ignored by most people — not a concern |

### Signal Combinations That Trigger Phoenix
The algorithm doesn't just count signals — it looks for PATTERNS:

**Strong Phoenix pattern:**
- Bookmarks from 3+ non-followers
- At least 1 repost with commentary from a non-follower
- Replies that form a conversation chain (reply → reply to reply)
- All within the first 60 minutes

**Weak signal pattern (Thunder only):**
- Mostly likes from existing followers
- No bookmarks
- No reposts
- One or two low-effort replies ("Great!", "This!")

**Anti-pattern (distribution killed):**
- Report filed (even one)
- Multiple blocks/mutes
- Many "Not interested in this post" clicks
- Engagement then sudden drop-off (suggests ratio risk)

---

## Velocity Threshold (First 60 Minutes)

The first hour of a post's life determines its fate. This is the most critical window.

### The 60-Minute Test

| First-Hour Engagements | Distribution Outcome | Post Fate |
|----------------------|---------------------|-----------|
| 0-2 | No signal | Post dies in Thunder-only, reaches ~5% of followers |
| 3-4 | Weak signal | May get minor Thunder boost, unlikely Phoenix |
| 5-9 | Moderate signal | Likely Phoenix test with small non-follower audience |
| 10-14 | Strong signal | Phoenix triggered, reaching significant non-followers |
| 15-30 | Very strong signal | Wide Phoenix distribution, potential viral trajectory |
| 30+ | Exceptional signal | Maximum Phoenix, potential mass viral |

### Velocity Curve Types

**Type A — Steady Climber:**
- 2 engagements in first 15 min → 5 at 30 min → 10 at 45 min → 18 at 60 min
- This is the ideal pattern — accelerating engagement
- Algorithm reads this as "growing interest" → strong Phoenix

**Type B — Front-Loaded Spike:**
- 12 engagements in first 10 min → 14 at 30 min → 15 at 60 min
- Big initial burst then flatline
- Algorithm may trigger Phoenix but it fades quickly
- Common when large account engages early then audience loses interest

**Type C — Slow Burn:**
- 0 in first 30 min → 2 at 45 min → 7 at 60 min
- Late starter but accelerating
- May trigger Phoenix if the acceleration continues past 60 min
- Don't give up on a post at 30 min if you see this pattern

**Type D — Dead on Arrival:**
- 0-1 engagements in first 30 min, flat at 60 min
- No Phoenix trigger
- Either the content missed or the timing was wrong
- Learn from it and move on

### Practical Implications
- Post when your audience is most active (check your analytics)
- Engage with replies in the first 30 min to boost velocity
- If possible, have 2-3 people ready to engage right after posting
- Never delete and repost — the algorithm penalizes this
- If a post is underperforming at 30 min, a single high-authority engagement can save it

---

## Author Diversity Penalty

The algorithm actively reduces distribution if a user's audience sees too many posts from the same source in a short window.

### How It Works
- If your followers see your post alongside 3+ other posts from you in their feed, your reach drops
- This applies to both original posts and replies
- The penalty is cumulative — more posts = more penalty per post

### Safe Posting Frequencies
| Post Type | Max Frequency | Notes |
|-----------|--------------|-------|
| Original tweets | 3-4 per day | Space them 3+ hours apart |
| Replies | 10-15 per day | Mix targets, don't reply to same thread 5 times |
| Quote tweets | 2-3 per day | Each counts as a separate post for diversity |
| Threads | 1 per day | Each tweet in thread counts separately |
| Reposts | 5-10 per day | Low penalty but adds to volume |

### Diversity Mix Recommendations
To avoid the penalty, maintain a content mix:
- 40% original posts (your thoughts, analysis, news)
- 30% replies (engaging with others)
- 20% quote tweets with commentary
- 10% reposts/shares

If you post 5 original tweets in 2 hours, the 5th will get significantly less reach than the 1st.

---

## Tweepcred (Author Credibility Score)

Tweepcred is an internal (not publicly visible) score that represents an account's overall credibility and trustworthiness. Higher Tweepcred = more algorithmic distribution.

### What Increases Tweepcred
| Action | Impact | Notes |
|--------|--------|-------|
| Replies from high-Tweepcred accounts | + | Being validated by credible accounts boosts yours |
| High bookmark rate | + | Signals your content has lasting value |
| Long thread engagement | + | When your threads spark deep conversations |
| Being bookmarked by diverse accounts | ++ | Non-follower bookmarks are extra valuable |
| Consistent posting frequency | + | Regular, quality posting builds trust over time |
| Low report/block rate | + | Clean behavioral record |

### What Decreases Tweepcred
| Action | Impact | Notes |
|--------|--------|-------|
| Posts getting ratioed | -- | Being publicly disagreed with damages credibility |
| Deleted posts after criticism | --- | Deleting looks like covering up — worse than leaving it |
| Mass blocking | -- | Algorithm reads this as inability to handle disagreement |
| Engagement bait patterns | -- | Consistently using "Like if you agree" type content |
| Report accumulation | --- | Even reports that don't result in suspension damage Tweepcred |
| Inconsistent posting | - | Long gaps followed by bursts look like spam |

### Tweepcred Recovery
If your Tweepcred drops:
1. Stop the behavior that caused the drop immediately
2. Post high-quality, factual content for 2-4 weeks
3. Engage authentically (no automation, no engagement bait)
4. Avoid controversial topics until score recovers
5. Recovery typically takes 2-6 weeks of consistent good behavior

---

## Content Type Algorithm Preferences

The algorithm treats different content types differently:

| Content Type | Initial Reach | Phoenix Potential | Notes |
|-------------|--------------|-------------------|-------|
| Text-only tweet | Medium | Medium | Baseline. Good if the text is strong. |
| Tweet with image | High | High | Images boost initial engagement by ~30% |
| Tweet with video | High | Very High | Video has the highest Phoenix potential |
| Thread (3+ tweets) | Medium-High | Medium | First tweet determines if people click "Show this thread" |
| Poll | High | Low | Good for engagement but low Phoenix (not shareable) |
| Quote tweet | Medium | Medium | Depends on the commentary quality |
| Long-form article | Low initially | Medium | Slow burn — can gain traction over 24-48h |

### Image Best Practices
- Screenshots of data/charts perform better than generic stock photos
- Text-heavy images (quote cards, data tables) get more bookmarks
- Memes get likes but fewer bookmarks (lower quality engagement)
- Original images/diagrams outperform stock images

### Thread Strategy
- First tweet is EVERYTHING — it determines if anyone reads the rest
- Optimal thread length: 5-10 tweets (shorter = higher completion rate)
- Number your tweets for readability
- End with a summary tweet and a call-to-action (follow, bookmark, etc.)

---

## Timing Optimization

### Best Posting Times (General AI Audience)
| Day | Best Window (UTC) | Notes |
|-----|-------------------|-------|
| Monday | 14:00-16:00 | Start of work week, people catching up |
| Tuesday | 13:00-15:00 | Peak productivity day |
| Wednesday | 14:00-16:00 | Mid-week consistency |
| Thursday | 13:00-15:00 | Pre-weekend planning |
| Friday | 12:00-14:00 | Early finish — catch people before they check out |
| Saturday | 10:00-12:00 | Casual browsing time |
| Sunday | 15:00-18:00 | Evening wind-down, more reading time |

**Note:** These are general guidelines. Your specific audience may have different patterns. Track your own analytics to find your optimal window.

### Worst Posting Times
- Late night (23:00-06:00 UTC) — lowest engagement across all audiences
- During major events (World Cup, elections, Apple keynote) — your content gets buried
- First 30 min after a major news break — algorithm is flooded

### Reply Timing
- Best: 30-120 minutes after original post
- Acceptable: 2-6 hours after (if post is still getting engagement)
- Avoid: First reply (looks like a bot), after 6 hours (buried)
- Sweet spot: 3rd-10th reply in a thread
