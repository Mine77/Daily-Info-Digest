# Google Translate Free Endpoint

We use `https://translate.googleapis.com/translate_a/single?client=gtx` — Google's unofficial free translation endpoint — rather than a paid translation API.

**Why:** Zero cost, no API key management, sufficient quality for one-line summaries. The project has no budget for paid translation services at this stage.

**Trade-off:** This endpoint is unofficial and may break or rate-limit without notice. If it fails, translations fall back to English. We'll monitor and can switch to a paid API if reliability becomes an issue.
