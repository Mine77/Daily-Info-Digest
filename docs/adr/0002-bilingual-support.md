# Bilingual EN/CN Support

All digest summaries are generated in English first, then translated to Chinese via Google Translate's free endpoint (`translate.googleapis.com`). Users can toggle between EN/CN via a language switcher in the header.

**Why:** The target audience includes both English-speaking and Chinese-speaking users. Rather than maintaining separate digests, we generate both languages from the same source content.

**Trade-off:** Machine translation quality varies. For nuanced technical content, CN summaries may lose precision. We accept this in exchange for zero translation API cost and automatic coverage of all content.
