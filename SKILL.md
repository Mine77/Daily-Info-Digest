---
name: daily-info-digest
description: AI-powered daily digest — aggregates insights from X/Twitter builders, tech media RSS, blogs, and podcasts into a unified bilingual timeline. Use when the user wants to manage sources, generate digests, or modify the report format.
---

# Daily Info Digest

An AI-powered content curation system that tracks builders in AI and delivers a daily digest of their insights.

**Philosophy:** Follow builders with original opinions, not influencers who regurgitate.

## Project Context

Before making changes, read these files:
- `ROADMAP.md` — current phase and planned features
- `CONTEXT.md` — shared language and domain terminology
- `CLADUE.md` — coding behavior guidelines
- `docs/adr/` — architectural decisions

## File Structure

```
Daily-Info-Digest/
├── ROADMAP.md              # Three-phase roadmap
├── CONTEXT.md              # Project glossary and domain language
├── CLAUDE.md               # AI coding guidelines
├── SKILL.md                # This file
├── docs/
│   └── adr/                  # Architecture Decision Records
├── web/
│   ├── app.py              # Flask dashboard + report generator
│   ├── templates/          # Jinja2 templates
│   ├── static/             # CSS, JS, generated reports
│   └── data/
│       └── sources.json    # User-managed source list
├── scripts/
│   ├── generate-feed.js   # Fetches X/Twitter, blogs, podcasts
│   ├── prepare-digest.js  # Prepares data for consumption
│   └── deliver.js         # Telegram/email delivery
├── prompts/               # LLM prompt templates
└── config/                # JSON schemas and defaults
```

## Daily Digest Generation Flow

```
1. generate-feed.js → Fetches raw content from all sources
2. prepare-digest.js → Aggregates and structures the data
3. app.py (build_report_html) → Generates bilingual HTML report
4. Static report served via Flask dashboard
```

## Commands

Generate today's digest:
```bash
cd /root/workspace/agent-workspace/Daily-Info-Digest/web
python3 app.py generate
```

Restart web service:
```bash
sudo systemctl restart follow-builders-web
```

Test report locally:
```bash
curl -s http://127.0.0.1:25520/latest
```

## Key Technical Details

- **X API:** Uses X API v2 with Bearer Token. Fetches tweets, media attachments, and quoted tweets.
- **RSS:** Parses RSS feeds with regex (no XML parser dependency). Filters by AI keywords.
- **Translation:** Google Translate free endpoint (`translate.googleapis.com`). Falls back to English on failure.
- **Reports:** Self-contained HTML files in `web/static/reports/YYYY-MM-DD.html`
- **Dashboard:** Flask on `127.0.0.1:25520`, nginx reverse proxy to `fb.x-nuwa.com:8445`

## Adding a New Source

1. Determine source type: `rss`, `hackernews`, `x`, `blog`, or `podcast`
2. For RSS: add to `web/data/sources.json` under `media_sites`
3. For X: add to `web/data/sources.json` under `x_accounts`
4. For blog/podcast: add to `web/data/sources.json` under appropriate key
5. Test fetch: `python3 app.py generate`
6. Verify item appears in timeline

## Environment

- VPS with root privileges (be cautious)
- Port 443 is reserved for Xray Reality VPN — never touch it
- GitHub repo: `Mine77/agent-workspace` (project under `Daily-Info-Digest/`)
