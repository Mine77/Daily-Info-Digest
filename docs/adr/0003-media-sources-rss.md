# Media Sources via RSS + AI Filtering

Media sites are fetched via RSS feeds (not APIs) and filtered by AI/tech keywords before inclusion in the digest. Only articles whose title + description match at least one keyword from the AI_KEYWORDS list are included.

**Why:** RSS is universally supported, requires no API keys, and is simpler than managing per-site API integrations. AI keyword filtering keeps the digest focused on relevant content without manual curation.

**Trade-off:** Some edge-case AI content may be filtered out if keywords don't match. We accept false negatives over false positives to maintain digest quality. Keywords can be expanded as needed.
