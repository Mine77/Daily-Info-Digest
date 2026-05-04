#!/usr/bin/env python3
"""
Follow Builders Web Dashboard v5.1 - Twitter-like Rich Cards
- Rich card content with images, quoted tweets
- Sidebar category filtering
- Twitter-style layout
- Dark/Light theme toggle (follows system by default)
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

from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__, template_folder=str(Path(__file__).parent / 'templates'), static_folder=str(Path(__file__).parent / 'static'))

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'static' / 'reports'
SKILL_DIR = Path.home() / '.hermes' / 'skills' / 'follow-builders'
SOURCES_FILE = DATA_DIR / 'sources.json'

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# RSSHub configuration
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
# RSSHub Integration
# ---------------------------------------------------------------------------

def fetch_rsshub_feed(route, max_items=10):
    """Fetch and parse RSS from RSSHub"""
    url = f"{RSSHUB_BASE}{route}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
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
            pub_date = item.findtext('pubDate', '').strip()

            # Clean HTML from description
            description = re.sub(r'<[^>]+>', ' ', description).replace('&nbsp;', ' ').strip()
            if len(description) > 300:
                description = description[:297] + '...'

            if title and link:
                articles.append({
                    'title': title,
                    'url': link,
                    'description': description,
                    'pubDate': pub_date
                })

        return articles
    except Exception as e:
        print(f"RSSHub XML parse error for {route}: {e}")
        return []

def fetch_youtube_channel(channel_id, max_items=5):
    """Fetch YouTube channel via RSSHub"""
    return fetch_rsshub_feed(f'/youtube/channel/{channel_id}', max_items)

def fetch_hackernews_rsshub(max_items=5):
    """Fetch Hacker News via RSSHub"""
    return fetch_rsshub_feed('/hackernews/best', max_items)

# ---------------------------------------------------------------------------
# Legacy RSS Media Fetching (fallback)
# ---------------------------------------------------------------------------

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
               'humanoid', 'figure', 'tesla', 'xai', 'meta', 'microsoft', 'apple', 'amazon',
               'scaling', 'alignment', 'safety', 'benchmark', 'dataset', 'multimodal',
               'vision', 'robotics', 'drone', 'cybersecurity', 'quantum', 'cloud']

def is_ai_related(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in AI_KEYWORDS)

def fetch_rss_feed(rss_url, max_items=5):
    """Legacy RSS fetcher - fallback when RSSHub doesn't have a route"""
    try:
        req = urllib.request.Request(rss_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return []

    articles = []
    item_pattern = re.compile(r'<item>([\s\S]*?)</item>', re.IGNORECASE)
    title_pattern = re.compile(r'<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</title>', re.IGNORECASE)
    link_pattern = re.compile(r'<link>([^<]+)</link>', re.IGNORECASE)
    desc_pattern = re.compile(r'<description>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</description>', re.IGNORECASE)
    pubdate_pattern = re.compile(r'<pubDate>([^<]+)</pubDate>', re.IGNORECASE)

    for match in item_pattern.finditer(xml):
        block = match.group(1)
        title_m = title_pattern.search(block)
        link_m = link_pattern.search(block)
        desc_m = desc_pattern.search(block)
        pub_m = pubdate_pattern.search(block)

        if not title_m or not link_m:
            continue

        title = title_m.group(1).strip()
        link = link_m.group(1).strip()
        desc = desc_m.group(1).strip() if desc_m else ''
        desc = re.sub(r'<[^>]+>', ' ', desc).replace('&nbsp;', ' ').strip()
        if len(desc) > 300:
            desc = desc[:297] + '...'

        # Filter by AI relevance
        combined = title + ' ' + desc
        if not is_ai_related(combined):
            continue

        if pub_m:
            try:
                pub_dt = datetime.strptime(pub_m.group(1).strip(), '%a, %d %b %Y %H:%M:%S %z')
                if (datetime.now(pub_dt.tzinfo) - pub_dt).days > 2:
                    continue
            except Exception:
                pass

        articles.append({'title': title, 'url': link, 'description': desc})
        if len(articles) >= max_items:
            break

    return articles

def fetch_hackernews_legacy(max_items=5):
    """Legacy Hacker News fetcher - fallback"""
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
# Content Cleaning (replaces Firecrawl)
# ---------------------------------------------------------------------------

def clean_html_content(html_content, max_length=500):
    """Clean HTML content to readable text"""
    if not html_content:
        return ''
    
    # Remove script and style tags
    html_content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content, flags=re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#x27;', "'").replace('&nbsp;', ' ')
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + '...'
    
    return text

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

def save_sources(data):
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_reports():
    reports = []
    for p in sorted(REPORTS_DIR.glob('*.html'), reverse=True):
        date_str = p.stem
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            reports.append({
                'date': date_str,
                'display': dt.strftime('%B %d, %Y'),
                'url': f'/static/reports/{p.name}'
            })
        except ValueError:
            continue
    return reports

def get_latest_report():
    reports = get_reports()
    return reports[0] if reports else None

def slugify(text):
    return re.sub(r'[^a-z0-9]', '-', text.lower())[:50]

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/archive')
def archive():
    return render_template('archive.html')

@app.route('/report/<date>')
def report_by_date(date):
    report_path = REPORTS_DIR / f'{date}.html'
    if not report_path.exists():
        abort(404)
    return render_template('report_view.html', date=date)

@app.route('/latest')
def latest_report():
    latest = get_latest_report()
    if not latest:
        abort(404)
    return render_template('report_view.html', date=latest['date'])

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route('/api/sources', methods=['GET'])
def api_sources_get():
    return jsonify(load_sources())

@app.route('/api/sources', methods=['POST'])
def api_sources_post():
    data = request.get_json(force=True)
    save_sources(data)
    return jsonify({'status': 'ok'})

@app.route('/api/reports', methods=['GET'])
def api_reports():
    return jsonify(get_reports())

@app.route('/api/latest', methods=['GET'])
def api_latest():
    latest = get_latest_report()
    return jsonify(latest or {})

@app.route('/api/report/<date>/content', methods=['GET'])
def api_report_content(date):
    report_path = REPORTS_DIR / f'{date}.html'
    if not report_path.exists():
        abort(404)
    with open(report_path, 'r', encoding='utf-8') as f:
        return f.read()

# ---------------------------------------------------------------------------
# Report Generator (Hybrid RSSHub + Legacy)
# ---------------------------------------------------------------------------

def generate_daily_report():
    today = datetime.now().strftime('%Y-%m-%d')
    report_path = REPORTS_DIR / f'{today}.html'

    # Step 1: Fetch Twitter/podcast/blog data from GitHub feeds (existing system)
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

    # Step 2: Fetch media sites using RSSHub or legacy RSS
    sources = load_sources()
    media_sites = sources.get('media_sites', DEFAULT_MEDIA_SITES)
    media_articles = []
    
    for site in media_sites:
        if not site.get('enabled', True):
            continue
        
        articles = []
        
        if site.get('type') == 'hackernews' or site.get('name') == 'Hacker News':
            # Try RSSHub first, fallback to legacy
            articles = fetch_hackernews_rsshub(max_items=5)
            if not articles:
                articles = fetch_hackernews_legacy(max_items=5)
            if articles:
                media_articles.append({'name': 'Hacker News', 'articles': articles})
        
        elif site.get('type') == 'rss' and site.get('rssUrl'):
            # Try to use RSSHub generic route for RSS feeds
            # RSSHub doesn't have a generic RSS passthrough, so use legacy
            articles = fetch_rss_feed(site['rssUrl'], max_items=3)
            if articles:
                media_articles.append({'name': site['name'], 'articles': articles})
        
        elif site.get('type') == 'youtube' and site.get('channelId'):
            # Use RSSHub for YouTube channels
            articles = fetch_youtube_channel(site['channelId'], max_items=3)
            if articles:
                media_articles.append({'name': site['name'], 'articles': articles})

    data['media'] = media_articles

    # Step 3: Build and save report
    html = build_report_html(data, today)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return str(report_path)

# ---------------------------------------------------------------------------
# Build Twitter-like rich card timeline HTML with theme toggle
# ---------------------------------------------------------------------------

def build_report_html(data, date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    display_date = dt.strftime('%B %d, %Y')

    x_builders = data.get('x', [])
    podcasts = data.get('podcasts', [])
    blogs = data.get('blogs', [])
    media = data.get('media', [])
    stats = data.get('stats', {})

    # Build unified timeline items
    timeline_items = []

    # X/Twitter items - show rich content by default
    for builder in x_builders:
        for t in builder.get('tweets', []):
            full_text = t['text'].replace('\n', '<br>')
            
            # Build media HTML (images)
            media_html = ""
            for m in t.get('media', []):
                if m.get('url'):
                    media_html += f'<img src="{m["url"]}" class="tweet-media" loading="lazy">'
            
            # Build quoted tweet HTML
            quote_html = ""
            if t.get('isQuote') and t.get('quotedTweetContent'):
                quote_text = t['quotedTweetContent'].replace('\n', '<br>')
                quote_html = (
                    '<div class="quoted-tweet">'
                    f'<div class="quoted-tweet-text">{quote_text}</div>'
                    '</div>'
                )
            
            timeline_items.append({
                'type': 'twitter',
                'category': 'Twitter',
                'source': builder['name'],
                'handle': builder['handle'],
                'avatar': f"https://unavatar.io/x/{builder['handle']}",
                'content': full_text,
                'content_zh': translate(full_text, 'zh-CN') if full_text else '',
                'media': media_html,
                'quote': quote_html,
                'likes': t.get('likes', 0),
                'retweets': t.get('retweets', 0),
                'url': t['url'],
            })

    # Blog items
    for blog in blogs:
        content = blog.get('content', '')
        preview = content[:800].replace('&#x27;', "'").replace('&quot;', '"').replace('&amp;', '&')
        if len(content) > 800:
            preview += '...'
        
        timeline_items.append({
            'type': 'blog',
            'category': 'Blog',
            'source': blog['name'],
            'avatar': '',
            'content': preview,
            'content_zh': translate(preview, 'zh-CN') if preview else '',
            'media': '',
            'quote': '',
            'likes': 0,
            'retweets': 0,
            'url': blog['url'],
        })

    # Podcast items
    for pod in podcasts:
        transcript = pod.get('transcript', '')
        preview = transcript[:800].replace('\n', '<br>') if transcript else ''
        if len(transcript or '') > 800:
            preview += '...'
        
        timeline_items.append({
            'type': 'podcast',
            'category': 'Podcast',
            'source': pod['name'],
            'avatar': '',
            'content': preview,
            'content_zh': translate(preview, 'zh-CN') if preview else '',
            'media': '',
            'quote': '',
            'likes': 0,
            'retweets': 0,
            'url': pod['url'],
        })

    # Media items
    for site in media:
        for article in site.get('articles', []):
            title = article.get('title', '')
            desc = article.get('description', '')
            content = f"<strong>{title}</strong><br><br>{desc}" if desc else title
            
            timeline_items.append({
                'type': 'media',
                'category': 'Media',
                'source': site['name'],
                'avatar': '',
                'content': content,
                'content_zh': translate(content, 'zh-CN') if content else '',
                'media': '',
                'quote': '',
                'likes': 0,
                'retweets': 0,
                'url': article['url'],
            })

    # Count by category
    category_counts = {}
    for item in timeline_items:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Build sidebar HTML
    sidebar_html = ""
    categories = ['All', 'Twitter', 'Blog', 'Podcast', 'Media']
    for cat in categories:
        count = len(timeline_items) if cat == 'All' else category_counts.get(cat, 0)
        active_class = 'active' if cat == 'All' else ''
        sidebar_html += f'''
        <div class="sidebar-tab {active_class}" data-category="{cat}" onclick="filterCategory('{cat}')">
            <span class="tab-icon">{get_category_icon(cat)}</span>
            <span class="tab-name">{cat}</span>
            <span class="tab-count">{count}</span>
        </div>
        '''

    # Build timeline cards HTML
    cards_html = ""
    for i, item in enumerate(timeline_items):
        cards_html += build_card_html(item, i)

    # Build stats
    media_count = sum(len(s.get('articles', [])) for s in media)

    return f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Builders Digest — {display_date}</title>
    <style>
        /* Dark theme (default) */
        :root {{
            --bg: #000000;
            --surface: #16181c;
            --surface-hover: #1d1f23;
            --text: #e7e9ea;
            --text-muted: #71767b;
            --accent: #1d9bf0;
            --border: #2f3336;
            --radius: 16px;
            --danger: #f4212e;
            --success: #00ba7c;
        }}

        /* Light theme */
        [data-theme="light"] {{
            --bg: #ffffff;
            --surface: #f7f9f9;
            --surface-hover: #eff1f1;
            --text: #0f1419;
            --text-muted: #536471;
            --accent: #1d9bf0;
            --border: #eff3f4;
            --danger: #f4212e;
            --success: #00ba7c;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
        }}

        /* Layout */
        .container {{
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* Sidebar */
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
        .tab-icon {{
            font-size: 1.2rem;
        }}
        .tab-name {{
            flex: 1;
            font-weight: 600;
            font-size: 1rem;
        }}
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

        /* Main content */
        .main {{
            flex: 1;
            border-left: 1px solid var(--border);
            min-height: 100vh;
        }}
        .main-header {{
            position: sticky;
            top: 0;
            background: var(--bg);
            backdrop-filter: blur(12px);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            z-index: 10;
        }}
        .main-header h2 {{
            font-size: 1.25rem;
            font-weight: 800;
        }}
        .main-header .date {{
            color: var(--text-muted);
            font-size: 0.85rem;
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

        /* Tweet cards */
        .tweet-card {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
            cursor: pointer;
        }}
        .tweet-card:hover {{
            background: var(--surface-hover);
        }}
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
        .tweet-body {{
            flex: 1;
            min-width: 0;
        }}
        .tweet-author {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }}
        .tweet-name {{
            font-weight: 700;
            font-size: 0.95rem;
        }}
        .tweet-handle {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .tweet-source {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
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

        /* Media */
        .tweet-media {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }}

        /* Quoted tweet */
        .quoted-tweet {{
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 16px;
            margin-bottom: 12px;
            background: var(--surface);
        }}
        .quoted-tweet-text {{
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        /* Tweet actions */
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
        .tweet-action:hover {{
            color: var(--accent);
        }}

        /* Category badge */
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
        .category-podcast {{ background: rgba(0,186,124,0.15); color: var(--success); }}
        .category-media {{ background: rgba(139,92,246,0.15); color: #8b5cf6; }}

        /* Footer */
        footer {{
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
        }}
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}

        /* Mobile responsive */
        @media (max-width: 768px) {{
            .container {{
                flex-direction: column;
            }}
            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
                border-right: none;
                border-bottom: 1px solid var(--border);
                padding: 16px;
            }}
            .sidebar-tabs {{
                flex-direction: row;
                overflow-x: auto;
                gap: 8px;
            }}
            .sidebar-tab {{
                padding: 8px 12px;
                white-space: nowrap;
            }}
            .main {{
                border-left: none;
            }}
        }}

        /* Theme and Language toggle */
        .controls {{
            position: fixed;
            top: 16px;
            right: 16px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }}
        .ctrl-btn {{
            padding: 8px 16px;
            border-radius: 100px;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .ctrl-btn:hover {{
            background: var(--surface-hover);
        }}
        .ctrl-btn.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        body.lang-zh .tweet-content-zh {{ display: block; }}
        body.lang-en .tweet-content-zh {{ display: none; }}
    </style>
</head>
<body class="lang-en">
    <div class="controls">
        <button class="ctrl-btn" id="themeToggle" onclick="toggleTheme()" title="Toggle theme">🌙</button>
        <button class="ctrl-btn active" onclick="setLang('en')">EN</button>
        <button class="ctrl-btn" onclick="setLang('zh')">CN</button>
    </div>

    <div class="container">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>AI Builders Digest</h1>
                <div class="subtitle">Follow builders, not influencers.</div>
            </div>
            <div class="sidebar-tabs">
                {sidebar_html}
            </div>
        </aside>

        <!-- Main content -->
        <main class="main">
            <div class="main-header">
                <h2>Timeline</h2>
                <div class="date">{display_date}</div>
            </div>
            <div class="stats-bar">
                <div class="stat">
                    <span class="stat-num">{stats.get('xBuilders', 0)}</span> Builders
                </div>
                <div class="stat">
                    <span class="stat-num">{stats.get('totalTweets', 0)}</span> Tweets
                </div>
                <div class="stat">
                    <span class="stat-num">{stats.get('podcastEpisodes', 0)}</span> Podcasts
                </div>
                <div class="stat">
                    <span class="stat-num">{media_count}</span> Media
                </div>
            </div>

            <div id="timeline">
                {cards_html}
            </div>

            <footer>
                Generated by <a href="https://github.com/Mine77/agent-workspace" target="_blank">Follow Builders</a>
            </footer>
        </main>
    </div>

    <script>
        // Theme toggle - follows system preference by default
        function getSystemTheme() {{
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }}

        function setTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('fb-theme', theme);
            updateThemeButton(theme);
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            setTheme(next);
        }}

        function updateThemeButton(theme) {{
            const btn = document.getElementById('themeToggle');
            btn.textContent = theme === 'dark' ? '☀️' : '🌙';
            btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
        }}

        // Initialize theme
        const savedTheme = localStorage.getItem('fb-theme');
        if (savedTheme) {{
            setTheme(savedTheme);
        }} else {{
            setTheme(getSystemTheme());
        }}

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {{
            if (!localStorage.getItem('fb-theme')) {{
                setTheme(e.matches ? 'dark' : 'light');
            }}
        }});

        // Category filter
        function filterCategory(category) {{
            // Update active tab
            document.querySelectorAll('.sidebar-tab').forEach(tab => {{
                tab.classList.toggle('active', tab.dataset.category === category);
            }});

            // Filter cards
            document.querySelectorAll('.tweet-card').forEach(card => {{
                if (category === 'All' || card.dataset.category === category) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        // Language toggle
        function setLang(lang) {{
            document.body.classList.remove('lang-en', 'lang-zh');
            document.body.classList.add('lang-' + lang);
            document.querySelectorAll('.ctrl-btn').forEach(btn => {{
                if (btn.textContent.trim() === 'EN' || btn.textContent.trim() === 'CN') {{
                    btn.classList.toggle('active', btn.textContent.trim() === (lang === 'en' ? 'EN' : 'CN'));
                }}
            }});
            localStorage.setItem('fb-lang', lang);
        }}

        // Load saved language preference
        const savedLang = localStorage.getItem('fb-lang');
        if (savedLang) setLang(savedLang);
    </script>
</body>
</html>'''

def get_category_icon(category):
    """Get icon for category"""
    icons = {
        'All': '🏠',
        'Twitter': '🐦',
        'Blog': '📝',
        'Podcast': '🎙️',
        'Media': '📰'
    }
    return icons.get(category, '📄')

def build_card_html(item, index):
    """Build HTML for a single card"""
    category_class = f"category-{item['category'].lower()}"
    
    avatar_html = ""
    if item['avatar']:
        avatar_html = f'<img class="tweet-avatar" src="{item["avatar"]}" onerror="this.src=\'https://ui-avatars.com/api/?name={item["source"].replace(chr(32), chr(43))}&background=random\'" alt="">'
    else:
        avatar_html = f'<div class="tweet-avatar" style="background:var(--surface);display:flex;align-items:center;justify-content:center;font-size:1.5rem;">{get_category_icon(item["category"])}</div>'

    actions_html = ""
    if item['likes'] > 0 or item['retweets'] > 0:
        actions_html = f'''
        <div class="tweet-actions">
            <div class="tweet-action">💬 0</div>
            <div class="tweet-action">🔄 {item["retweets"]}</div>
            <div class="tweet-action">❤️ {item["likes"]}</div>
            <div class="tweet-action">📤</div>
        </div>
        '''

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
    </div>
    '''

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        path = generate_daily_report()
        print(path)
    else:
        app.run(host='127.0.0.1', port=25520, debug=False)
