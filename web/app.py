#!/usr/bin/env python3
"""
Follow Builders - Direct Report View
Opening the site shows the latest report directly, full screen.
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, jsonify, request, abort, Response

# Import funding fetcher
from funding_fetcher import fetch_all_funding_news

app = Flask(__name__, template_folder=str(Path(__file__).parent / 'templates'), static_folder=str(Path(__file__).parent / 'static'))

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'static' / 'reports'
SKILL_DIR = Path.home() / '.hermes' / 'skills' / 'follow-builders'
SOURCES_FILE = DATA_DIR / 'sources.json'

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

RSSHUB_BASE = os.environ.get('RSSHUB_BASE', 'http://127.0.0.1:1200')

# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def translate(text, target='zh-CN', max_chars=4000):
    if not text or len(text) < 3:
        return text
    if len(text) > max_chars:
        text = text[:max_chars] + '...'
    try:
        url = ('https://translate.googleapis.com/translate_a/single'
               '?client=gtx&sl=en&tl=' + target + '&dt=t&q=' + urllib.parse.quote(text))
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return ''.join([s[0] for s in data[0] if s[0]])
    except Exception:
        return text

# ---------------------------------------------------------------------------
# RSSHub & RSS Fetching
# ---------------------------------------------------------------------------

def fetch_rsshub_feed(route, max_items=10):
    url = f"{RSSHUB_BASE}{route}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_content = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"RSSHub fetch error for {route}: {e}")
        return []

    try:
        root = ET.fromstring(xml_content)
        channel = root.find('channel')
        if channel is None:
            return []

        articles = []
        for item in channel.findall('item')[:max_items]:
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            description = item.findtext('description', '').strip()
            description = re.sub(r'<[^>]+>', ' ', description).replace('&nbsp;', ' ').strip()
            if len(description) > 300:
                description = description[:297] + '...'

            if title and link:
                articles.append({'title': title, 'url': link, 'description': description})
        return articles
    except Exception as e:
        print(f"RSSHub XML parse error for {route}: {e}")
        return []

def fetch_hackernews_rsshub(max_items=5):
    return fetch_rsshub_feed('/hackernews/best', max_items)

DEFAULT_MEDIA_SITES = [
    {"name": "TechCrunch", "rssUrl": "https://techcrunch.com/feed/", "type": "rss", "enabled": True},
    {"name": "The Verge", "rssUrl": "https://www.theverge.com/rss/index.xml", "type": "rss", "enabled": True},
    {"name": "Ars Technica", "rssUrl": "http://feeds.arstechnica.com/arstechnica/index", "type": "rss", "enabled": True},
    {"name": "Wired", "rssUrl": "https://www.wired.com/feed/rss", "type": "rss", "enabled": True},
    {"name": "MIT Technology Review", "rssUrl": "https://www.technologyreview.com/feed/", "type": "rss", "enabled": True},
    {"name": "VentureBeat", "rssUrl": "https://venturebeat.com/feed/", "type": "rss", "enabled": True},
    {"name": "Engadget", "rssUrl": "https://www.engadget.com/rss.xml", "type": "rss", "enabled": True},
    {"name": "Hacker News", "type": "hackernews", "enabled": True},
]

AI_KEYWORDS = ['ai', 'artificial intelligence', 'llm', 'machine learning', 'deep learning', 'neural',
               'openai', 'anthropic', 'google', 'gpt', 'claude', 'gemini', 'model', 'agent',
               'chatbot', 'generative', 'transformer', 'nvidia', 'chip', 'compute', 'gpu',
               'startup', 'venture', 'funding', 'robot', 'autonomous', 'code', 'developer',
               'chatgpt', 'copilot', 'mcp', 'rag', 'fine-tune', 'inference', 'token',
               'humanoid', 'figure', 'tesla', 'xai', 'meta', 'microsoft', 'apple', 'amazon']

def is_ai_related(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in AI_KEYWORDS)

def fetch_rss_feed(rss_url, max_items=5):
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return []

    articles = []
    item_pattern = re.compile(r'<item>([\s\S]*?)</item>', re.IGNORECASE)
    title_pattern = re.compile(r'<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</title>', re.IGNORECASE)
    link_pattern = re.compile(r'<link>([^<]+)</link>', re.IGNORECASE)
    desc_pattern = re.compile(r'<description>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</description>', re.IGNORECASE)

    for match in item_pattern.finditer(xml):
        block = match.group(1)
        title_m = title_pattern.search(block)
        link_m = link_pattern.search(block)
        desc_m = desc_pattern.search(block)

        if not title_m or not link_m:
            continue

        title = title_m.group(1).strip()
        link = link_m.group(1).strip()
        desc = desc_m.group(1).strip() if desc_m else ''
        desc = re.sub(r'<[^>]+>', ' ', desc).replace('&nbsp;', ' ').strip()
        if len(desc) > 300:
            desc = desc[:297] + '...'

        combined = title + ' ' + desc
        if not is_ai_related(combined):
            continue

        articles.append({'title': title, 'url': link, 'description': desc})
        if len(articles) >= max_items:
            break
    return articles

def fetch_hackernews_legacy(max_items=5):
    try:
        req = urllib.request.Request(
            'https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=30',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return []

    articles = []
    cutoff = datetime.now() - timedelta(hours=48)
    for hit in data.get('hits', []):
        created = datetime.fromtimestamp(hit.get('created_at_i', 0))
        if created < cutoff:
            continue
        title = hit.get('title', '')
        url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if title and is_ai_related(title):
            articles.append({
                'title': title,
                'url': url,
                'description': f"{hit.get('points', 0)} points · {hit.get('num_comments', 0)} comments"
            })
        if len(articles) >= max_items:
            break
    return articles

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_sources():
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'media_sites' not in data:
            data['media_sites'] = DEFAULT_MEDIA_SITES
        return data
    return {"podcasts": [], "blogs": [], "x_accounts": [], "media_sites": DEFAULT_MEDIA_SITES}

def get_reports():
    reports = []
    for p in sorted(REPORTS_DIR.glob('*.html'), reverse=True):
        date_str = p.stem
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            reports.append({
                'date': date_str,
                'display': dt.strftime('%B %d, %Y'),
                'url': f'/report/{date_str}'
            })
        except ValueError:
            continue
    return reports

def get_latest_report():
    reports = get_reports()
    return reports[0] if reports else None

# ---------------------------------------------------------------------------
# Routes - Direct Report View
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Show latest report directly"""
    latest = get_latest_report()
    if not latest:
        # No reports yet, show a simple page
        return '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>AI Builders Digest</title>
<style>body{font-family:-apple-system,sans-serif;background:#000;color:#e7e9ea;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
h1{font-size:2rem;background:linear-gradient(135deg,#1d9bf0,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}</style>
</head><body><h1>No reports yet. Run: python3 app.py generate</h1></body></html>'''
    
    report_path = REPORTS_DIR / f'{latest["date"]}.html'
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            return Response(f.read(), content_type='text/html')
    abort(404)

@app.route('/report/<date>')
def report_by_date(date):
    """Show specific date report"""
    report_path = REPORTS_DIR / f'{date}.html'
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            return Response(f.read(), content_type='text/html')
    abort(404)

@app.route('/api/sources', methods=['GET'])
def api_sources_get():
    return jsonify(load_sources())

@app.route('/api/sources', methods=['POST'])
def api_sources_post():
    data = request.get_json(force=True)
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({'status': 'ok'})

@app.route('/api/reports', methods=['GET'])
def api_reports():
    return jsonify(get_reports())

# ---------------------------------------------------------------------------
# Tweet Media Enrichment
# ---------------------------------------------------------------------------

CACHE_FILE = DATA_DIR / 'tweet_media_cache.json'

def _load_media_cache():
    """Load cached tweet media data."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_media_cache(cache):
    """Save tweet media cache to disk."""
    try:
        CACHE_FILE.write_text(json.dumps(cache))
    except Exception:
        pass

def _fetch_single_tweet(tweet_id):
    """Fetch a single tweet's media and quote data via twitter-cli."""
    try:
        env = os.environ.copy()
        # Source Twitter cookies from bashrc if not already set
        if 'TWITTER_AUTH_TOKEN' not in env:
            env['TWITTER_AUTH_TOKEN'] = '5e62794f5acdda65d2d78dbf9b883663862cad99'
        if 'TWITTER_CT0' not in env:
            env['TWITTER_CT0'] = 'e0aaa53ea99b61bcc15ca972bdb26824e6fd8e23e0ad4a653687ce94111806dc3027f85e2b19ebf5a9efcd4d29016e2bd538d0a2fdc6750f1abe08c57b73558e20ebce3a6567e681bb2ab34c010af0a4'

        twitter_bin = os.path.expanduser('~/.local/bin/twitter')
        result = subprocess.run(
            [twitter_bin, 'tweet', str(tweet_id), '--json'],
            capture_output=True, text=True, timeout=30,
            env=env, shell=False
        )
        if result.returncode != 0:
            return tweet_id, None

        data = json.loads(result.stdout)
        tweets = data.get('data', [])
        if not tweets:
            return tweet_id, None

        # Find the exact tweet by ID (twitter-cli may return replies too)
        for t in tweets:
            if str(t.get('id')) == str(tweet_id):
                return tweet_id, t

        # If exact match not found, return first result
        return tweet_id, tweets[0]
    except Exception:
        return tweet_id, None


def enrich_tweets_with_media(feed_data):
    """Enrich feed tweets with media and quoted tweet data using twitter-cli."""
    x_builders = feed_data.get('x', [])
    if not x_builders:
        return feed_data

    # Load cache
    cache = _load_media_cache()

    # Collect all tweet IDs that need enrichment (skip cached ones)
    tweet_ids = []
    for builder in x_builders:
        for t in builder.get('tweets', []):
            tid = t['id']
            # Skip if already has media data in feed
            if t.get('media'):
                continue
            # Skip if already in cache
            if tid in cache:
                continue
            tweet_ids.append(tid)

    if not tweet_ids:
        # All tweets are cached or already have media, use cache
        enriched = cache
    else:
        print(f"Enriching {len(tweet_ids)} tweets with media data ({len(cache)} cached)...")

        # Fetch tweets concurrently (3 workers with delay to avoid rate limiting)
        import time, random
        enriched = dict(cache)  # Start with cached data

        def _fetch_with_delay(tweet_id):
            time.sleep(random.uniform(0.5, 1.5))
            return _fetch_single_tweet(tweet_id)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_fetch_with_delay, tid): tid for tid in tweet_ids}
            for future in as_completed(futures):
                tweet_id, tweet_data = future.result()
                if tweet_data:
                    enriched[tweet_id] = tweet_data

        # Save updated cache
        _save_media_cache(enriched)

    # Merge enriched data back into feed
    for builder in x_builders:
        for t in builder.get('tweets', []):
            if t['id'] in enriched:
                src = enriched[t['id']]
                # Add media
                if src.get('media'):
                    t['media'] = src['media']
                # Add views from enriched metrics (keep original likes/retweets from feed)
                if src.get('metrics', {}).get('views'):
                    if 'metrics' not in t:
                        t['metrics'] = {}
                    t['metrics']['views'] = src['metrics']['views']
                # Add quoted tweet content
                if src.get('quotedTweet'):
                    qt = src['quotedTweet']
                    author = qt.get('author', {})
                    handle = author.get('screenName', '')
                    t['quotedTweetContent'] = qt.get('text', '')
                    t['quotedTweetAuthor'] = f"@{handle}" if handle else ''
                    t['isQuote'] = True

    enriched_count = sum(1 for builder in x_builders for t in builder.get('tweets', []) if t['id'] in enriched)
    media_count = sum(1 for builder in x_builders for t in builder.get('tweets', []) if t.get('media'))
    print(f"Enriched {enriched_count} tweets, {media_count} with media")
    return feed_data


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def generate_daily_report():
    today = datetime.now().strftime('%Y-%m-%d')
    report_path = REPORTS_DIR / f'{today}.html'

    result = subprocess.run(
        ['node', 'prepare-digest.js'],
        cwd=SKILL_DIR / 'scripts',
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"prepare-digest failed: {result.stderr}")

    data = json.loads(result.stdout)
    if data.get('status') != 'ok':
        raise RuntimeError(f"Feed error: {data.get('message', 'unknown')}")

    # Enrich tweets with media and quoted tweet data
    data = enrich_tweets_with_media(data)

    sources = load_sources()
    media_sites = sources.get('media_sites', DEFAULT_MEDIA_SITES)
    media_articles = []
    
    for site in media_sites:
        if not site.get('enabled', True):
            continue
        
        articles = []
        if site.get('type') == 'hackernews' or site.get('name') == 'Hacker News':
            articles = fetch_hackernews_rsshub(max_items=5)
            if not articles:
                articles = fetch_hackernews_legacy(max_items=5)
            if articles:
                media_articles.append({'name': 'Hacker News', 'articles': articles})
        elif site.get('type') == 'rss' and site.get('rssUrl'):
            articles = fetch_rss_feed(site['rssUrl'], max_items=3)
            if articles:
                media_articles.append({'name': site['name'], 'articles': articles})

    data['media'] = media_articles
    
    # Fetch AI funding news
    print("Fetching AI funding news...")
    funding_articles = fetch_all_funding_news()
    data['funding'] = funding_articles
    print(f"Found {len(funding_articles)} funding articles")
    
    html = build_report_html(data, today)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return str(report_path)

# ---------------------------------------------------------------------------
# Build Report HTML
# ---------------------------------------------------------------------------

def build_report_html(data, date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    display_date = dt.strftime('%B %d, %Y')

    x_builders = data.get('x', [])
    podcasts = data.get('podcasts', [])
    blogs = data.get('blogs', [])
    media = data.get('media', [])
    stats = data.get('stats', {})

    timeline_items = []

    for builder in x_builders:
        for t in builder.get('tweets', []):
            full_text = t['text'].replace('\n', '<br>')
            media_html = ""
            for m in t.get('media', []):
                if m.get('url'):
                    mtype = m.get('type', 'photo')
                    if mtype in ('video', 'animated_gif'):
                        media_html += f'<video src="{m["url"]}" class="tweet-media" controls {"loop" if mtype == "animated_gif" else ""} preload="metadata"></video>'
                    else:
                        media_html += f'<img src="{m["url"]}" class="tweet-media" loading="lazy">'

            quote_html = ""
            if t.get('isQuote') and t.get('quotedTweetContent'):
                quote_text = t['quotedTweetContent'].replace('\n', '<br>')
                quote_author = t.get('quotedTweetAuthor', '')
                quote_header = f'<div class="quoted-tweet-author">{quote_author}</div>' if quote_author else ''
                quote_html = f'<div class="quoted-tweet">{quote_header}<div class="quoted-tweet-text">{quote_text}</div></div>'

            metrics = t.get('metrics', {})
            likes = metrics.get('likes', t.get('likes', 0))
            retweets = metrics.get('retweets', t.get('retweets', 0))
            views = metrics.get('views', 0)

            timeline_items.append({
                'type': 'twitter', 'category': 'Twitter',
                'source': builder['name'], 'handle': builder['handle'],
                'avatar': f"https://unavatar.io/x/{builder['handle']}",
                'content': full_text, 'content_zh': translate(full_text, 'zh-CN'),
                'media': media_html, 'quote': quote_html,
                'likes': likes, 'retweets': retweets, 'views': views, 'url': t['url'],
            })

    for blog in blogs:
        content = blog.get('content', '')
        preview = content[:800].replace('&#x27;', "'").replace('&quot;', '"').replace('&amp;', '&')
        if len(content) > 800:
            preview += '...'
        timeline_items.append({
            'type': 'blog', 'category': 'Blog', 'source': blog['name'], 'avatar': '',
            'content': preview, 'content_zh': translate(preview, 'zh-CN'),
            'media': '', 'quote': '', 'likes': 0, 'retweets': 0, 'url': blog['url'],
        })

    for pod in podcasts:
        transcript = pod.get('transcript', '')
        preview = transcript[:800].replace('\n', '<br>') if transcript else ''
        if len(transcript or '') > 800:
            preview += '...'
        timeline_items.append({
            'type': 'podcast', 'category': 'Podcast', 'source': pod['name'], 'avatar': '',
            'content': preview, 'content_zh': translate(preview, 'zh-CN'),
            'media': '', 'quote': '', 'likes': 0, 'retweets': 0, 'url': pod['url'],
        })

    for site in media:
        for article in site.get('articles', []):
            title = article.get('title', '')
            desc = article.get('description', '')
            content = f"<strong>{title}</strong><br><br>{desc}" if desc else title
            timeline_items.append({
                'type': 'media', 'category': 'Media', 'source': site['name'], 'avatar': '',
                'content': content, 'content_zh': translate(content, 'zh-CN'),
                'media': '', 'quote': '', 'likes': 0, 'retweets': 0, 'url': article['url'],
            })

    # Add funding news
    funding = data.get('funding', [])
    for article in funding:
        title = article.get('title', '')
        desc = article.get('description', '')
        source = article.get('source', 'Unknown')
        content = f"<strong>{title}</strong><br><br>{desc}" if desc else title
        timeline_items.append({
            'type': 'funding', 'category': 'Funding', 'source': source, 'avatar': '',
            'content': content, 'content_zh': translate(content, 'zh-CN'),
            'media': '', 'quote': '', 'likes': 0, 'retweets': 0, 'url': article['url'],
        })

    category_counts = {}
    for item in timeline_items:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Build sidebar with categories + date selector
    sidebar_html = ""
    categories = ['All', 'Twitter', 'Blog', 'Podcast', 'Media', 'Funding']
    for cat in categories:
        count = len(timeline_items) if cat == 'All' else category_counts.get(cat, 0)
        active_class = 'active' if cat == 'All' else ''
        sidebar_html += f'''
        <div class="sidebar-tab {active_class}" data-category="{cat}" onclick="filterCategory('{cat}')">
            <span class="tab-icon">{get_category_icon(cat)}</span>
            <span class="tab-name">{cat}</span>
            <span class="tab-count">{count}</span>
        </div>'''

    # Build date list for archive
    reports = get_reports()
    date_list_html = ""
    for r in reports[:10]:  # Show last 10 days
        active = 'active' if r['date'] == date_str else ''
        date_list_html += f'''
        <div class="date-item {active}" onclick="window.location.href='/report/{r['date']}'">
            <span class="date-text">{r['display']}</span>
        </div>'''

    cards_html = ""
    for i, item in enumerate(timeline_items):
        cards_html += build_card_html(item, i)

    media_count = sum(len(s.get('articles', [])) for s in media)

    return f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Builders Digest — {display_date}</title>
    <style>
        :root {{
            --bg: #000000;
            --surface: #16181c;
            --surface-hover: #1d1f23;
            --text: #e7e9ea;
            --text-muted: #71767b;
            --accent: #1d9bf0;
            --border: #2f3336;
            --radius: 16px;
        }}
        [data-theme="light"] {{
            --bg: #ffffff;
            --surface: #f7f9f9;
            --surface-hover: #eff1f1;
            --text: #0f1419;
            --text-muted: #536471;
            --border: #eff3f4;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
        }}
        .container {{
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            min-height: 100vh;
        }}
        .sidebar {{
            width: 280px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            padding: 20px 16px;
            border-right: 1px solid var(--border);
        }}
        .sidebar-header {{
            margin-bottom: 24px;
        }}
        .sidebar-header h1 {{
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent), #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .sidebar-header .subtitle {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 4px;
        }}
        .sidebar-section {{
            margin-bottom: 24px;
        }}
        .sidebar-section-title {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            padding: 0 12px;
        }}
        .sidebar-tabs {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .sidebar-tab {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-radius: var(--radius);
            cursor: pointer;
            transition: all 0.2s;
            color: var(--text);
        }}
        .sidebar-tab:hover {{
            background: var(--surface-hover);
        }}
        .sidebar-tab.active {{
            background: var(--accent);
            color: #fff;
        }}
        .tab-icon {{ font-size: 1.2rem; }}
        .tab-name {{ flex: 1; font-weight: 600; font-size: 1rem; }}
        .tab-count {{
            background: var(--border);
            padding: 2px 8px;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .sidebar-tab.active .tab-count {{
            background: rgba(255,255,255,0.2);
        }}
        .date-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .date-item {{
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            color: var(--text-muted);
            transition: all 0.2s;
        }}
        .date-item:hover {{
            background: var(--surface-hover);
            color: var(--text);
        }}
        .date-item.active {{
            color: var(--accent);
            font-weight: 600;
        }}
        .main {{
            flex: 1;
            min-height: 100vh;
        }}
        .main-header {{
            position: sticky;
            top: 0;
            background: var(--bg);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            z-index: 10;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .main-header h2 {{
            font-size: 1.25rem;
            font-weight: 800;
        }}
        .main-header .date {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .controls {{
            display: flex;
            gap: 8px;
        }}
        .ctrl-btn {{
            padding: 6px 12px;
            border-radius: 100px;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .ctrl-btn:hover {{ background: var(--surface-hover); }}
        .ctrl-btn.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        .stats-bar {{
            display: flex;
            gap: 20px;
            padding: 12px 20px;
            border-bottom: 1px solid var(--border);
            background: var(--surface);
        }}
        .stat {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        .stat-num {{
            font-weight: 700;
            color: var(--text);
        }}
        .tweet-card {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
            cursor: pointer;
        }}
        .tweet-card:hover {{ background: var(--surface-hover); }}
        .tweet-header {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}
        .tweet-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
        }}
        .tweet-body {{ flex: 1; min-width: 0; }}
        .tweet-author {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }}
        .tweet-name {{ font-weight: 700; font-size: 0.95rem; }}
        .tweet-handle {{ color: var(--text-muted); font-size: 0.85rem; }}
        .tweet-content {{
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 12px;
            word-wrap: break-word;
        }}
        .tweet-content-zh {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding: 8px 12px;
            background: var(--surface);
            border-radius: 12px;
            border-left: 3px solid var(--accent);
        }}
        .tweet-media {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }}
        video.tweet-media {{
            max-height: 500px;
            background: #000;
        }}
        .quoted-tweet {{
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 16px;
            margin-bottom: 12px;
            background: var(--surface);
        }}
        .quoted-tweet-author {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 4px;
        }}
        .quoted-tweet-text {{ font-size: 0.9rem; color: var(--text-muted); }}
        .tweet-actions {{
            display: flex;
            gap: 40px;
            margin-top: 12px;
        }}
        .tweet-action {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .tweet-action:hover {{ color: var(--accent); }}
        .category-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .category-twitter {{ background: rgba(29,155,240,0.15); color: var(--accent); }}
        .category-blog {{ background: rgba(245,158,11,0.15); color: #f59e0b; }}
        .category-podcast {{ background: rgba(0,186,124,0.15); color: #00ba7c; }}
        .category-media {{ background: rgba(139,92,246,0.15); color: #8b5cf6; }}
        .category-funding {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
        body.lang-zh .tweet-content-zh {{ display: block; }}
        body.lang-en .tweet-content-zh {{ display: none; }}
        body.lang-original .tweet-content-zh {{ display: none; }}
        @media (max-width: 768px) {{
            .container {{ flex-direction: column; }}
            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
                border-right: none;
                border-bottom: 1px solid var(--border);
                padding: 16px;
            }}
            .sidebar-tabs {{ flex-direction: row; overflow-x: auto; gap: 8px; }}
            .sidebar-tab {{ padding: 8px 12px; white-space: nowrap; }}
            .date-list {{ flex-direction: row; overflow-x: auto; gap: 8px; }}
            .date-item {{ white-space: nowrap; }}
        }}
    </style>
</head>
<body class="lang-original">
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>AI Builders Digest</h1>
                <div class="subtitle">Follow builders, not influencers.</div>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Categories</div>
                <div class="sidebar-tabs">
                    {sidebar_html}
                </div>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-section-title">Archive</div>
                <div class="date-list">
                    {date_list_html}
                </div>
            </div>
        </aside>

        <main class="main">
            <div class="main-header">
                <div>
                    <h2>Timeline</h2>
                    <div class="date">{display_date}</div>
                </div>
                <div class="controls">
                    <button class="ctrl-btn" id="themeToggle" onclick="toggleTheme()">🌙</button>
                    <button class="ctrl-btn active" onclick="setLang('original')">Original</button>
                    <button class="ctrl-btn" onclick="setLang('en')">EN</button>
                    <button class="ctrl-btn" onclick="setLang('zh')">CN</button>
                </div>
            </div>
            <div class="stats-bar">
                <div class="stat"><span class="stat-num">{stats.get('xBuilders', 0)}</span> Builders</div>
                <div class="stat"><span class="stat-num">{stats.get('totalTweets', 0)}</span> Tweets</div>
                <div class="stat"><span class="stat-num">{stats.get('podcastEpisodes', 0)}</span> Podcasts</div>
                <div class="stat"><span class="stat-num">{media_count}</span> Media</div>
            </div>
            <div id="timeline">
                {cards_html}
            </div>
        </main>
    </div>
    <script>
        function getSystemTheme() {{
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }}
        function setTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('fb-theme', theme);
            document.getElementById('themeToggle').textContent = theme === 'dark' ? '☀️' : '🌙';
        }}
        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme');
            setTheme(current === 'dark' ? 'light' : 'dark');
        }}
        const savedTheme = localStorage.getItem('fb-theme');
        if (savedTheme) {{ setTheme(savedTheme); }} else {{ setTheme(getSystemTheme()); }}
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {{
            if (!localStorage.getItem('fb-theme')) {{ setTheme(e.matches ? 'dark' : 'light'); }}
        }});

        function filterCategory(category) {{
            document.querySelectorAll('.sidebar-tab').forEach(tab => {{
                tab.classList.toggle('active', tab.dataset.category === category);
            }});
            document.querySelectorAll('.tweet-card').forEach(card => {{
                card.style.display = (category === 'All' || card.dataset.category === category) ? 'block' : 'none';
            }});
        }}

        function setLang(lang) {{
            document.body.classList.remove('lang-en', 'lang-zh', 'lang-original');
            document.body.classList.add('lang-' + lang);
            document.querySelectorAll('.ctrl-btn').forEach(btn => {{
                const text = btn.textContent.trim();
                if (['Original', 'EN', 'CN'].includes(text)) {{
                    btn.classList.toggle('active', 
                        (lang === 'original' && text === 'Original') ||
                        (lang === 'en' && text === 'EN') ||
                        (lang === 'zh' && text === 'CN')
                    );
                }}
            }});
            localStorage.setItem('fb-lang', lang);
        }}
        const savedLang = localStorage.getItem('fb-lang');
        if (savedLang) setLang(savedLang);
    </script>
</body>
</html>'''

def get_category_icon(category):
    icons = {'All': '🏠', 'Twitter': '🐦', 'Blog': '📝', 'Podcast': '🎙️', 'Media': '📰', 'Funding': '💰'}
    return icons.get(category, '📄')

def build_card_html(item, index):
    category_class = f"category-{item['category'].lower()}"
    
    if item['avatar']:
        avatar_html = f'<img class="tweet-avatar" src="{item["avatar"]}" onerror="this.src=\'https://ui-avatars.com/api/?name={item["source"].replace(chr(32), chr(43))}&background=random\'" alt="">'
    else:
        avatar_html = f'<div class="tweet-avatar" style="background:var(--surface);display:flex;align-items:center;justify-content:center;font-size:1.5rem;">{get_category_icon(item["category"])}</div>'

    actions_html = ""
    if item['likes'] > 0 or item['retweets'] > 0:
        views_html = f'<div class="tweet-action">👁️ {item.get("views", 0):,}</div>' if item.get('views', 0) > 0 else ''
        actions_html = f'''
        <div class="tweet-actions">
            <div class="tweet-action">💬 0</div>
            <div class="tweet-action">🔄 {item["retweets"]}</div>
            <div class="tweet-action">❤️ {item["likes"]}</div>
            {views_html}
        </div>'''

    return f'''
    <div class="tweet-card" data-category="{item['category']}" onclick="window.open('{item['url']}', '_blank')">
        <div class="tweet-header">
            {avatar_html}
            <div class="tweet-body">
                <div class="tweet-author">
                    <span class="tweet-name">{item["source"]}</span>
                    <span class="tweet-handle">{f'@{item["handle"]}' if item.get("handle") else ""}</span>
                    <span class="category-badge {category_class}">{item["category"]}</span>
                </div>
                <div class="tweet-content">{item["content"]}</div>
                <div class="tweet-content-zh">{item["content_zh"]}</div>
                {item["media"]}
                {item["quote"]}
                {actions_html}
            </div>
        </div>
    </div>'''

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        path = generate_daily_report()
        print(path)
    else:
        app.run(host='127.0.0.1', port=25520, debug=False)
