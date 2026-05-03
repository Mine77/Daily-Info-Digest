# Daily Info Digest - Roadmap

An AI-powered daily digest that aggregates, summarizes, and distributes industry insights from curated sources.

---

## Philosophy

**Follow builders, not influencers.** Track the people actually building products, running companies, and doing research — deliver their insights in the most consumable format for the audience.

---

## Phase 1: Robust Source Fetching (Current Focus)

**Goal:** Ensure all target information sources are fetched completely, accurately, and deduplicated.

### Completed
- [x] X/Twitter API v2 integration (tweets, media attachments, quoted tweets)
- [x] RSS feed parsing (8 media sites)
- [x] Blog scraping (Anthropic Engineering, Claude Blog)
- [x] Podcast RSS feeds (6 podcasts)
- [x] Hacker News API integration
- [x] AI keyword filtering for media sources
- [x] Bilingual summary generation (EN/CN via Google Translate)

### In Progress
- [ ] YouTube channel video fetching (podcasts publish on YouTube first)
- [ ] Content deduplication (same news appears on multiple sources)
- [ ] Content quality scoring (engagement metrics weighting)

### Planned
- [ ] Add more builder X accounts (expand from 25)
- [ ] Add more RSS media sources (The Information, IEEE Spectrum, etc.)
- [ ] Add Substack newsletter RSS feeds
- [ ] Smart source health monitoring (detect broken feeds, rate limits)

### Key Decisions
- Use Google Translate free endpoint (no API key needed) for CN summaries
- Filter media articles by AI/tech keywords to keep digest focused
- Store fetched data as JSON intermediates before HTML generation

---

## Phase 2: Multi-Format Presentation

**Goal:** Transform raw content into visually compelling, multi-format outputs.

### 2a. Web Dashboard (Enhanced)
- [x] Basic Flask dashboard with source management
- [x] Unified timeline feed (Twitter-style cards)
- [ ] Dark/light theme toggle
- [ ] Search and filter by source/type/date
- [ ] Reader mode (distraction-free reading)
- [ ] Mobile-responsive PWA

### 2b. Image Cards (Shareable)
- [ ] Generate static image cards for each digest item
- [ ] Brand-consistent templates (source avatar, summary, QR code to original)
- [ ] Batch generate "Today's Top 5" carousel images
- [ ] Support both 1:1 (Instagram) and 9:16 (Stories/Reels) aspect ratios

### 2c. Video Digest (Experimental)
- [ ] Research TTS + screenshot video feasibility
- [ ] Auto-generate voiceover script from digest highlights
- [ ] Synthesize speech (Edge TTS / OpenAI TTS)
- [ ] Sync audio with scrolling feed animation or static slides
- [ ] Export as MP4 for YouTube/抖音/视频号

**Decision:** Video generation is a stretch goal. Start with images (2b) before tackling video (2c).

---

## Phase 3: Automated Distribution

**Goal:** Push digest content to all major social platforms automatically.

### Priority Order (Easiest to Hardest)

1. **Twitter/X** — API v2 already integrated, easiest to implement
2. **Telegram Channel** — Bot API, user already on Telegram
3. **微信公众号** — Requires enterprise qualification + WeChat verification
4. **YouTube** — Requires OAuth + video file upload (depends on 2c)
5. **抖音 / 视频号** — No official API; requires simulated upload or third-party service

### Implementation Plan
- [ ] Twitter auto-post with image cards
- [ ] Telegram channel push
- [ ] WeChat Official Account integration (evaluate feasibility)
- [ ] YouTube auto-upload (if video generation succeeds)
- [ ] 抖音/视频号 (research workaround solutions)

### Account Strategy
- Create dedicated brand accounts for each platform
- Unified visual identity across all channels
- Cross-post with platform-optimized formatting

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 1 | Source coverage | 15+ sources, 50+ builders |
| Phase 1 | Fetch success rate | >95% daily |
| Phase 2 | Web engagement | Time on site >3 min |
| Phase 2 | Image generation | <30s per card |
| Phase 3 | Distribution reach | 5+ platforms synced |
| Phase 3 | Post automation | 100% hands-off |

---

## Current Status

**Phase:** 1 (In Progress)
**Last Updated:** 2025-01-10
**Next Milestone:** Complete YouTube fetching + deduplication
