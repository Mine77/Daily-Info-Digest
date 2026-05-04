#!/usr/bin/env python3
"""
AI Funding News Fetcher
Fetches AI startup funding news from multiple sources.
"""

import urllib.request
import json
import re
from datetime import datetime, timedelta

FUNDING_KEYWORDS = [
    'raised', 'funding', 'series a', 'series b', 'series c', 'series d',
    'seed round', 'seed funding', 'pre-seed', 'venture', 'investment',
    'million', 'billion', 'valuation', 'round', 'backed', 'investors',
    'capital', 'financing', 'ipo', 'acquisition'
]

AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'llm', 'machine learning', 'ml',
    'deep learning', 'neural', 'openai', 'anthropic', 'google', 'gpt',
    'claude', 'gemini', 'model', 'agent', 'chatbot', 'generative',
    'transformer', 'nvidia', 'compute', 'gpu', 'startup', 'robot',
    'autonomous', 'chatgpt', 'copilot', 'mcp', 'rag', 'inference',
    'humanoid', 'xai', 'multimodal', 'vision', 'robotics'
]

def is_funding_news(title, description=''):
    """Check if news is about funding"""
    text = (title + ' ' + description).lower()
    has_funding = any(kw in text for kw in FUNDING_KEYWORDS)
    has_ai = any(kw in text for kw in AI_KEYWORDS)
    return has_funding and has_ai

def fetch_techcrunch_venture(max_items=10):
    """Fetch from TechCrunch Venture section"""
    url = 'https://techcrunch.com/category/venture/feed/'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"TechCrunch fetch error: {e}")
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

        # Filter for AI funding news
        if is_funding_news(title, desc):
            articles.append({
                'title': title,
                'url': link,
                'description': desc,
                'source': 'TechCrunch'
            })
        if len(articles) >= max_items:
            break

    return articles

def fetch_crunchbase_news(max_items=10):
    """Fetch from Crunchbase News"""
    url = 'https://news.crunchbase.com/feed/'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Crunchbase fetch error: {e}")
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

        # Filter for AI funding news
        if is_funding_news(title, desc):
            articles.append({
                'title': title,
                'url': link,
                'description': desc,
                'source': 'Crunchbase'
            })
        if len(articles) >= max_items:
            break

    return articles

def fetch_hackernews_funding(max_items=5):
    """Fetch funding news from Hacker News"""
    try:
        req = urllib.request.Request(
            'https://hn.algolia.com/api/v1/search?query=AI+funding+raised&tags=story&hitsPerPage=20',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"HackerNews fetch error: {e}")
        return []

    articles = []
    cutoff = datetime.now() - timedelta(days=7)  # Last 7 days
    
    for hit in data.get('hits', []):
        created = datetime.fromtimestamp(hit.get('created_at_i', 0))
        if created < cutoff:
            continue
            
        title = hit.get('title', '')
        url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        
        if is_funding_news(title):
            articles.append({
                'title': title,
                'url': url,
                'description': f"{hit.get('points', 0)} points · {hit.get('num_comments', 0)} comments",
                'source': 'Hacker News'
            })
        if len(articles) >= max_items:
            break

    return articles

def fetch_all_funding_news():
    """Fetch funding news from all sources"""
    all_articles = []
    
    # Fetch from TechCrunch
    tc_articles = fetch_techcrunch_venture(max_items=5)
    all_articles.extend(tc_articles)
    
    # Fetch from Crunchbase
    cb_articles = fetch_crunchbase_news(max_items=5)
    all_articles.extend(cb_articles)
    
    # Fetch from Hacker News
    hn_articles = fetch_hackernews_funding(max_items=3)
    all_articles.extend(hn_articles)
    
    # Remove duplicates by title similarity
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        title_key = article['title'].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)
    
    return unique_articles[:15]  # Return top 15

if __name__ == '__main__':
    print("Fetching AI funding news...")
    articles = fetch_all_funding_news()
    print(f"\nFound {len(articles)} articles:")
    for i, a in enumerate(articles, 1):
        print(f"\n{i}. [{a['source']}] {a['title']}")
        print(f"   {a['description'][:100]}...")
