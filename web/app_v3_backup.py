#!/usr/bin/env python3
"""
Follow Builders Web Dashboard v3 - Twitter Feed Style
- Unified timeline with collapsible cards
- Bilingual EN/CN support
- RSS media sources
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
import re
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
# RSS Media Fetching
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

def fetch_hackernews(max_items=5):
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

def one_sentence_summary(text, max_words=20):
    if not text:
        return ''
    text = re.sub(r'https?://\S+', '', text).replace('\n', ' ').strip()
    words = text.split()
    if len(words) <= max_words:
        return text
    sentence_end = ' '.join(words[:max_words])
    for punct in ['. ', '! ', '? ']:
        idx = sentence_end.rfind(punct)
        if idx > 20:
            return sentence_end[:idx + 1]
    return sentence_end + '...'

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

    sources = load_sources()
    media_sites = sources.get('media_sites', DEFAULT_MEDIA_SITES)
    media_articles = []
    for site in media_sites:
        if not site.get('enabled', True):
            continue
        if site.get('type') == 'rss' and site.get('rssUrl'):
            articles = fetch_rss_feed(site['rssUrl'], max_items=3)
            if articles:
                media_articles.append({'name': site['name'], 'articles': articles})
        elif site.get('type') == 'hackernews' or site.get('name') == 'Hacker News':
            articles = fetch_hackernews(max_items=5)
            if articles:
                media_articles.append({'name': site['name'], 'articles': articles})

    data['media'] = media_articles

    html = build_report_html(data, today)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return str(report_path)

# ---------------------------------------------------------------------------
# Build unified timeline HTML (Twitter feed style)
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

    # X/Twitter items
    for builder in x_builders:
        for t in builder.get('tweets', []):
            text = t['text'].replace('\n', ' ')
            summary = one_sentence_summary(text)
            summary_zh = translate(summary, 'zh-CN') if summary else ''

            # Build detail HTML
            detail_html = ""
            full_text = t['text'].replace('\n', '<br>')
            detail_html += f'<div class="detail-text">{full_text}</div>'

            media_html = ""
            for m in t.get('media', []):
                if m.get('url'):
                    media_html += f'<img src="{m["url"]}" class="detail-media" loading="lazy">'
            if media_html:
                detail_html += media_html

            if t.get('isQuote') and t.get('quotedTweetContent'):
                detail_html += (
                    '<div class="detail-quote">'
                    '<div class="detail-quote-label">Quoted Tweet</div>'
                    f'<div class="detail-quote-text">{t["quotedTweetContent"].replace(chr(10), "<br>")}</div>'
                    '</div>'
                )

            detail_html += (
                f'<div class="detail-meta">'
                f'<a href="{t["url"]}" target="_blank">View on X &rarr;</a>'
                f'<span>&hearts; {t.get("likes", 0)} &nbsp; &#9851; {t.get("retweets", 0)}</span>'
                f'</div>'
            )

            timeline_items.append({
                'type': 'x',
                'source': builder['name'],
                'handle': builder['handle'],
                'avatar': f"https://unavatar.io/x/{builder['handle']}",
                'summary': summary,
                'summary_zh': summary_zh,
                'detail': detail_html,
                'url': t['url'],
            })

    # Blog items
    for blog in blogs:
        summary = blog.get('title', '')
        summary_zh = translate(summary, 'zh-CN') if summary else ''
        content = blog.get('content', '')
        preview = content[:500].replace('&#x27;', "'").replace('&quot;', '"').replace('&amp;', '&')
        if len(content) > 500:
            preview += '...'

        detail_html = (
            f'<div class="detail-text">{preview}</div>'
            f'<div class="detail-meta">'
            f'<a href="{blog["url"]}" target="_blank">Read article &rarr;</a>'
            f'</div>'
        )

        timeline_items.append({
            'type': 'blog',
            'source': blog['name'],
            'avatar': '',
            'summary': summary,
            'summary_zh': summary_zh,
            'detail': detail_html,
            'url': blog['url'],
        })

    # Podcast items
    for pod in podcasts:
        summary = pod.get('title', '')
        summary_zh = translate(summary, 'zh-CN') if summary else ''
        transcript = pod.get('transcript', '')
        preview = transcript[:500].replace('\n', ' ') if transcript else ''
        if len(transcript or '') > 500:
            preview += '...'

        detail_html = (
            f'<div class="detail-text">{preview}</div>'
            f'<div class="detail-meta">'
            f'<a href="{pod["url"]}" target="_blank">Listen on YouTube &rarr;</a>'
            f'</div>'
        )

        timeline_items.append({
            'type': 'podcast',
            'source': pod['name'],
            'avatar': '',
            'summary': summary,
            'summary_zh': summary_zh,
            'detail': detail_html,
            'url': pod['url'],
        })

    # Media items
    for site in media:
        for article in site.get('articles', []):
            summary = article.get('title', '')
            summary_zh = translate(summary, 'zh-CN') if summary else ''
            desc = article.get('description', '')

            detail_html = ''
            if desc:
                detail_html += f'<div class="detail-text">{desc}</div>'
            detail_html += (
                f'<div class="detail-meta">'
                f'<a href="{article["url"]}" target="_blank">Read on {site["name"]} &rarr;</a>'
                f'</div>'
            )

            timeline_items.append({
                'type': 'media',
                'source': site['name'],
                'avatar': '',
                'summary': summary,
                'summary_zh': summary_zh,
                'detail': detail_html,
                'url': article['url'],
            })

    # Build timeline HTML
    timeline_html = ""
    for i, item in enumerate(timeline_items):
        idx = i
        type_colors = {
            'x': '#6366f1',
            'blog': '#f59e0b',
            'podcast': '#22c55e',
            'media': '#a78bfa',
        }
        type_labels = {
            'x': 'X',
            'blog': 'Blog',
            'podcast': 'Podcast',
            'media': 'Media',
        }
        color = type_colors.get(item['type'], '#888')
        label = type_labels.get(item['type'], item['type'])

        avatar_html = ""
        if item['avatar']:
            avatar_html = (
                f'<img class="card-avatar" src="{item["avatar"]}" '
                f'onerror="this.src=\'https://ui-avatars.com/api/?name={item["source"].replace(chr(32), chr(43))}&background=random\'" alt="">'
            )
        else:
            avatar_html = (
                '<div class="card-avatar fallback">'
                + {'blog': '&#128221;', 'podcast': '&#127897;', 'media': '&#128240;'}.get(item['type'], '&#128240;')
                + '</div>'
            )

        timeline_html += (
            '<div class="feed-card">'
            '<div class="feed-card-inner" onclick="toggleDetail(' + str(idx) + ')">'
            + avatar_html +
            '<div class="feed-body">'
            '<div class="feed-header">'
            '<span class="feed-source">' + item['source'] + '</span>'
            '<span class="feed-tag" style="background:' + color + '22;color:' + color + ';">' + label + '</span>'
            '</div>'
            '<div class="feed-summary en">' + item['summary'] + '</div>'
            '<div class="feed-summary zh">' + item['summary_zh'] + '</div>'
            '</div>'
            '<div class="feed-arrow" id="arrow-' + str(idx) + '">&#9662;</div>'
            '</div>'
            '<div class="feed-detail" id="detail-' + str(idx) + '">'
            + item['detail'] +
            '</div>'
            '</div>'
        )

    if not timeline_html:
        timeline_html = '<p style="color:#888;text-align:center;padding:60px 0;">No new updates today.</p>'

    media_count = sum(len(s.get('articles', [])) for s in media)

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>AI Builders Digest &mdash; ' + display_date + '</title>'
        '<style>'
        ':root{--bg:#0a0a0f;--surface:#141419;--surface-2:#1e1e28;--text:#e8e8ec;--text-muted:#888899;--accent:#6366f1;--accent-2:#a78bfa;--border:#272736;--radius:14px;}'
        '*{margin:0;padding:0;box-sizing:border-box;}'
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:40px 20px;}'
        '.container{max-width:700px;margin:0 auto;padding:0 20px;}'
        'header{text-align:center;margin-bottom:32px;grid-column:1/-1;position:relative;}'
        'header h1{font-size:2rem;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px;background:linear-gradient(135deg,var(--accent),var(--accent-2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}'
        'header .subtitle{color:var(--text-muted);font-size:0.95rem;}'
        'header .date{display:inline-block;margin-top:12px;padding:6px 18px;background:var(--surface);border-radius:100px;font-size:0.85rem;color:var(--accent);border:1px solid var(--border);font-weight:600;}'
        '.header-lang{position:absolute;top:0;right:0;display:flex;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:4px;}'
        '.header-lang-btn{padding:6px 12px;border-radius:8px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;font-size:0.8rem;font-weight:600;transition:all 0.2s;}'
        '.header-lang-btn.active{background:var(--accent);color:#fff;}'
        '.header-lang-btn:hover:not(.active){color:var(--text);}'
        '.container{max-width:700px;margin:0 auto;padding:0 20px;}'
        '.stats-bar{display:flex;justify-content:center;gap:24px;margin-bottom:32px;padding:16px;background:var(--surface);border-radius:var(--radius);border:1px solid var(--border);}'
        '.feed-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:12px;transition:background 0.15s;overflow:hidden;}'
        '.feed-card:hover{background:var(--surface-2);}'
        '.feed-card-inner{display:flex;align-items:flex-start;gap:14px;padding:16px 18px;cursor:pointer;}'
        '.card-avatar{width:40px;height:40px;border-radius:50%;object-fit:cover;border:2px solid var(--border);flex-shrink:0;font-size:1.4rem;display:flex;align-items:center;justify-content:center;background:var(--bg);}'
        '.feed-body{flex:1;min-width:0;}'
        '.feed-header{display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap;}'
        '.feed-source{font-weight:700;font-size:0.95rem;}'
        '.feed-tag{font-size:0.7rem;font-weight:600;padding:2px 8px;border-radius:100px;text-transform:uppercase;letter-spacing:0.5px;}'
        '.feed-summary{font-size:0.93rem;line-height:1.55;color:var(--text-muted);}'
        '.feed-summary.zh{margin-top:3px;font-size:0.88rem;}'
        '.feed-arrow{color:var(--text-muted);font-size:0.8rem;margin-top:4px;flex-shrink:0;transition:transform 0.2s;}'
        '.feed-arrow.open{transform:rotate(180deg);}'
        '.feed-detail{display:none;padding:0 18px 16px 72px;border-top:1px solid var(--border);}'
        '.feed-detail.open{display:block;}'
        '.detail-text{font-size:0.92rem;line-height:1.6;margin-bottom:12px;word-break:break-word;}'
        '.detail-media{max-width:100%;max-height:300px;border-radius:10px;margin:10px 0;display:block;}'
        '.detail-quote{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;margin:10px 0;}'
        '.detail-quote-label{font-size:0.75rem;color:var(--accent);font-weight:600;margin-bottom:4px;}'
        '.detail-quote-text{font-size:0.88rem;color:var(--text-muted);line-height:1.5;}'
        '.detail-meta{display:flex;justify-content:space-between;align-items:center;font-size:0.85rem;}'
        '.detail-meta a{color:var(--accent);text-decoration:none;font-weight:500;}'
        '.detail-meta a:hover{text-decoration:underline;}'
        '.detail-meta span{color:var(--text-muted);}'
        'footer{text-align:center;padding:30px 0;color:var(--text-muted);font-size:0.8rem;border-top:1px solid var(--border);margin-top:20px;grid-column:1/-1;}'
        'footer a{color:var(--accent);text-decoration:none;}'
        '@media(max-width:800px){.container{grid-template-columns:1fr;}.sidebar{position:static;order:-1;}.stats-bar{gap:16px;flex-wrap:wrap;}body{padding:20px 14px;}header h1{font-size:1.7rem;}.feed-detail{padding-left:18px;}}'
        'body.lang-zh .feed-summary.en,body.lang-zh .detail-text.en{display:none;}'
        'body.lang-en .feed-summary.zh{display:none;}'
        '</style>'
        '</head><body>'
        '<div class="container">'
        '<header>'
        '<div class="header-lang">'
        '<button class="header-lang-btn active" id="btn-en" onclick="setLang(\'en\')">EN</button>'
        '<button class="header-lang-btn" id="btn-zh" onclick="setLang(\'zh\')">CN</button>'
        '</div>'
        '<h1>AI Builders Digest</h1>'
        '<div class="subtitle">Follow builders, not influencers.</div>'
        '<div class="date">' + display_date + '</div>'
        '</header>'
        '<div class="stats-bar">'
        '<div class="stat"><span class="stat-num">' + str(stats.get('xBuilders', 0)) + '</span>Builders</div>'
        '<div class="stat"><span class="stat-num">' + str(stats.get('totalTweets', 0)) + '</span>Tweets</div>'
        '<div class="stat"><span class="stat-num">' + str(stats.get('podcastEpisodes', 0)) + '</span>Podcasts</div>'
        '<div class="stat"><span class="stat-num">' + str(stats.get('blogPosts', 0)) + '</span>Blogs</div>'
        '<div class="stat"><span class="stat-num">' + str(media_count) + '</span>Media</div>'
        '</div>'
        '<div class="main">'
        + timeline_html +
        '</div>'
        '<footer>Generated by <a href="https://github.com/Mine77/agent-workspace" target="_blank">Follow Builders</a></footer>'
        '</div>'
        '<script>'
        'function setLang(lang){'
        'document.body.classList.remove("lang-en","lang-zh");'
        'document.body.classList.add("lang-"+lang);'
        'document.querySelectorAll(".header-lang-btn").forEach(b=>b.classList.remove("active"));'
        'document.getElementById("btn-"+lang).classList.add("active");'
        'localStorage.setItem("fb-lang",lang);'
        '}'
        'function toggleDetail(idx){'
        'const d=document.getElementById("detail-"+idx);'
        'const a=document.getElementById("arrow-"+idx);'
        'd.classList.toggle("open");'
        'a.classList.toggle("open");'
        '}'
        'var saved=localStorage.getItem("fb-lang");'
        'if(saved) setLang(saved);'
        '</script>'
        '</body></html>'
    )

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        path = generate_daily_report()
        print(path)
    else:
        app.run(host='127.0.0.1', port=25520, debug=False)
