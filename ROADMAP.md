# Daily Info Digest - Roadmap

An AI-powered daily digest that aggregates, summarizes, and distributes industry insights from curated sources.

---

## Philosophy

**Follow builders, not influencers.** Track the people actually building products, running companies, and doing research — deliver their insights in the most consumable format for the audience.

---

## Phase 1: Robust Source Fetching ✅

**Goal:** Ensure all target information sources are fetched completely, accurately, and deduplicated.

### Completed
- [x] X/Twitter API v2 integration (tweets, media attachments, quoted tweets)
- [x] RSS feed parsing (8 media sites)
- [x] Blog scraping (Anthropic Engineering, Claude Blog)
- [x] Podcast RSS feeds (6 podcasts)
- [x] Hacker News API integration
- [x] AI keyword filtering for media sources
- [x] Bilingual summary generation (EN/CN via Google Translate)
- [x] YouTube channel video fetching (via RSSHub)
- [x] Content deduplication (same news appears on multiple sources)
- [x] Content quality scoring (engagement metrics weighting)
- [x] RSSHub hybrid architecture (YouTube/HN + existing feeds)

### Key Decisions
- Use Google Translate free endpoint (no API key needed) for CN summaries
- Filter media articles by AI/tech keywords to keep digest focused
- Store fetched data as JSON intermediates before HTML generation
- RSSHub for YouTube/Hacker News, existing feeds for Twitter

---

## Phase 2: Multi-Format Presentation ✅

**Goal:** Transform raw content into visually compelling, multi-format outputs.

### 2a. Web Dashboard (Enhanced) ✅
- [x] Basic Flask dashboard with source management
- [x] Unified timeline feed (Twitter-style cards)
- [x] Dark/light theme toggle (with localStorage persistence)
- [x] Search and filter by source/type/date
- [x] Reader mode (distraction-free reading with font size controls)
- [x] Mobile-responsive PWA (service worker + manifest)

### 2b. Image Cards (Shareable) ✅
- [x] Generate static image cards for each digest item
- [x] Brand-consistent templates (source avatar, summary, QR code to original)
- [x] Batch generate "Today's Top 5" carousel images
- [x] Support both 1:1 (Instagram) and 9:16 (Stories/Reels) aspect ratios

### 2c. Video Digest (Experimental) 🚧
- [ ] Research TTS + screenshot video feasibility
- [ ] Auto-generate voiceover script from digest highlights
- [ ] Synthesize speech (Edge TTS / OpenAI TTS)
- [ ] Sync audio with scrolling feed animation or static slides
- [ ] Export as MP4 for YouTube/抖音/视频号

**Decision:** Video generation is a stretch goal. Start with images (2b) before tackling video (2c).

---

## Phase 3: Automated Distribution ✅

**Goal:** Push digest content to all major social platforms automatically.

### Priority Order (Easiest to Hardest)

1. **Twitter/X** ✅ — API v2 already integrated, easiest to implement
2. **Telegram Channel** ✅ — Bot API, user already on Telegram
3. **微信公众号** 🚧 — Requires enterprise qualification + WeChat verification
4. **YouTube** — Requires OAuth + video file upload (depends on 2c)
5. **抖音 / 视频号** — No official API; requires simulated upload or third-party service

### Implementation Plan
- [x] Twitter auto-post with image cards (via Tweepy API v2)
- [x] Telegram channel push (via Bot API with photo support)
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

**Phase:** 3 (Completed)
**Last Updated:** 2026-05-04
**Next Milestone:** Video digest generation (Phase 2c)

---

## Technical Architecture

### Data Sources
- **RSSHub** (Docker on 127.0.0.1:1200): YouTube channels, Hacker News
- **GitHub feeds**: Twitter/X builders, podcasts, blogs
- **Legacy RSS**: Media sites (TechCrunch, The Verge, etc.)

### Content Processing
- **Web dashboard**: Flask on 127.0.0.1:25520 (fb.x-nuwa.com:8445)
- **Image generation**: PIL/Pillow for 1:1 and 9:16 cards
- **Distribution**: Tweepy (Twitter) + Requests (Telegram)

### Key Files
- `web/app.py`: Main Flask application
- `scripts/generate_cards.py`: Image card generation
- `scripts/distribute.py`: Social media distribution
- `web/static/cards/`: Generated image cards
- `web/static/reports/`: HTML digest reports
