# Daily Info Digest — Context

An AI-powered content curation system that aggregates insights from AI builders, tech media, podcasts, and blogs into a unified daily digest.

## Language

**Digest**:
A curated daily summary of content from multiple sources, remixed into a unified timeline with bilingual (EN/CN) summaries.
_Avoid_: Newsletter, report, feed

**Builder**:
A person actively building in AI — researchers, founders, PMs, engineers — tracked via their X/Twitter accounts.
_Avoid_: Influencer, creator, thought leader

**Source**:
An information origin that the system fetches from. Types: X account, RSS feed, blog, podcast, YouTube channel.
_Avoid_: Channel, input

**Fetch**:
The process of retrieving raw content from a source via API, RSS, or scraping.
_Avoid_: Pull, sync, crawl

**Remix**:
The process of transforming raw fetched content into digestible summaries, including translation and formatting.
_Avoid_: Process, transform, render

**Item**:
A single unit of content in the digest (one tweet, one article, one podcast episode).
_Avoid_: Card, post, entry

**Timeline**:
The unified chronological feed that displays all digest items in a single column.
_Avoid_: Feed, stream, list

**Digest Report**:
The daily HTML output file containing all remixed content for a given date.
_Avoid_: Page, document, output

**Source Manager**:
The dashboard interface for adding, editing, enabling, or disabling information sources.
_Avoid_: Admin panel, config UI

## Relationships

- A **Digest** contains many **Items** from multiple **Sources**
- A **Source** can be an **X Account**, **RSS Feed**, **Blog**, or **Podcast**
- Each **Item** has one **Summary** (EN) and optionally one **Summary_ZH** (CN)
- The **Timeline** displays **Items** grouped by date
- The **Source Manager** controls which **Sources** are active for fetching

## Example Dialogue

> **Dev:** "When a new **Item** from TechCrunch is fetched, does it go straight to the **Timeline**?"
> **Domain Expert:** "No — first it passes through the AI keyword filter. Only AI/tech-related **Items** become part of the **Digest**."
>
> **Dev:** "What happens if the same news appears on both TechCrunch and The Verge?"
> **Domain Expert:** "That's a deduplication problem. The system should detect duplicate **Items** and only show the highest-quality one in the **Timeline**."

## Flagged Ambiguities

- "Feed" was used to mean both RSS feed (source) and the visual timeline (display) — resolved: "Feed" refers only to RSS source; "Timeline" refers to the display.
- "Report" was used to mean both the HTML output file and a general summary — resolved: "Digest Report" refers to the HTML file; "Digest" refers to the overall content.
- "Card" was used interchangeably with "Item" — resolved: "Item" is the content unit; visual representation is just styling.
