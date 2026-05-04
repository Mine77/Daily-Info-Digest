#!/usr/bin/env python3
"""
Distribution script for posting digest content to social platforms.
Supports Twitter/X and Telegram.
"""

import json
import os
import sys
import tweepy
import requests
from pathlib import Path
from datetime import datetime

# Configuration
CONFIG_PATH = Path.home() / '.follow-builders' / 'config.json'

def load_config():
    """Load distribution config"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def post_to_twitter(text, image_path=None):
    """Post to Twitter/X using API v2"""
    config = load_config()
    twitter_config = config.get('twitter', {})
    
    # Check for required credentials
    required_keys = ['api_key', 'api_secret', 'access_token', 'access_token_secret']
    for key in required_keys:
        if not twitter_config.get(key):
            return {'success': False, 'error': f'Missing Twitter {key}'}
    
    try:
        # Authenticate with Twitter API v2
        client = tweepy.Client(
            consumer_key=twitter_config['api_key'],
            consumer_secret=twitter_config['api_secret'],
            access_token=twitter_config['access_token'],
            access_token_secret=twitter_config['access_token_secret']
        )
        
        # Upload media if provided
        media_ids = None
        if image_path and os.path.exists(image_path):
            auth = tweepy.OAuth1UserHandler(
                twitter_config['api_key'],
                twitter_config['api_secret'],
                twitter_config['access_token'],
                twitter_config['access_token_secret']
            )
            api = tweepy.API(auth)
            media = api.media_upload(filename=image_path)
            media_ids = [media.media_id]
        
        # Post tweet
        response = client.create_tweet(text=text, media_ids=media_ids)
        
        return {
            'success': True,
            'tweet_id': response.data['id'],
            'url': f"https://x.com/i/status/{response.data['id']}"
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def post_to_telegram(text, image_path=None, chat_id=None):
    """Post to Telegram channel"""
    config = load_config()
    telegram_config = config.get('telegram', {})
    
    bot_token = telegram_config.get('bot_token')
    if not chat_id:
        chat_id = telegram_config.get('chat_id')
    
    if not bot_token or not chat_id:
        return {'success': False, 'error': 'Missing Telegram bot_token or chat_id'}
    
    try:
        if image_path and os.path.exists(image_path):
            # Send photo with caption
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            with open(image_path, 'rb') as photo:
                response = requests.post(url, data={
                    'chat_id': chat_id,
                    'caption': text[:1024],  # Telegram caption limit
                    'parse_mode': 'HTML'
                }, files={'photo': photo})
        else:
            # Send text message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, data={
                'chat_id': chat_id,
                'text': text[:4096],  # Telegram message limit
                'parse_mode': 'HTML'
            })
        
        result = response.json()
        if result.get('ok'):
            return {
                'success': True,
                'message_id': result['result']['message_id']
            }
        else:
            return {'success': False, 'error': result.get('description', 'Unknown error')}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_digest_text(items, max_items=5):
    """Create formatted digest text for social posting"""
    lines = ["🤖 AI Builders Digest", ""]
    
    for i, item in enumerate(items[:max_items], 1):
        source = item.get('source', 'Unknown')
        summary = item.get('summary', item.get('title', ''))
        url = item.get('url', '')
        
        # Truncate summary
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        lines.append(f"{i}. {source}")
        lines.append(f"   {summary}")
        if url:
            lines.append(f"   🔗 {url}")
        lines.append("")
    
    lines.append("Follow builders, not influencers.")
    return "\n".join(lines)

def distribute_digest(date_str=None, platforms=None):
    """Distribute digest to specified platforms"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    if not platforms:
        platforms = ['twitter', 'telegram']
    
    # Load digest data (simplified - in production you'd parse the actual report)
    sample_items = [
        {
            'source': 'Sam Altman',
            'summary': 'i keep thinking i want the models to be cheaper/faster more than i want them to be smarter',
            'url': 'https://x.com/sama/status/2050671161915371998'
        },
        {
            'source': 'Aaron Levie',
            'summary': 'If you think AI replaces software engineers, here\'s a quick thought experiment...',
            'url': 'https://x.com/levie/status/2050684160151617603'
        },
        {
            'source': 'Training Data',
            'summary': 'OpenAI\'s Greg Brockman: Why Human Attention Is the New Bottleneck',
            'url': 'https://www.youtube.com/playlist?list=PLOhHNjZItNnMm5tdW61JpnyxeYH5NDDx8'
        }
    ]
    
    # Create digest text
    digest_text = create_digest_text(sample_items)
    
    # Find image card
    cards_dir = Path(__file__).parent.parent / 'web' / 'static' / 'cards'
    image_path = None
    if cards_dir.exists():
        # Look for 1:1 card for social media
        for f in cards_dir.glob('*_1x1.png'):
            image_path = str(f)
            break
    
    results = {}
    
    # Post to each platform
    for platform in platforms:
        if platform == 'twitter':
            print("Posting to Twitter...")
            results['twitter'] = post_to_twitter(digest_text, image_path)
        elif platform == 'telegram':
            print("Posting to Telegram...")
            results['telegram'] = post_to_telegram(digest_text, image_path)
    
    return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Distribute digest to social platforms')
    parser.add_argument('--date', type=str, help='Date to distribute (YYYY-MM-DD)')
    parser.add_argument('--platforms', nargs='+', choices=['twitter', 'telegram'],
                       default=['twitter', 'telegram'], help='Platforms to post to')
    parser.add_argument('--dry-run', action='store_true', help='Print content without posting')
    
    args = parser.parse_args()
    
    if args.dry_run:
        sample_items = [
            {'source': 'Sam Altman', 'summary': 'i keep thinking i want the models to be cheaper/faster', 'url': 'https://x.com/sama/status/123'},
            {'source': 'Aaron Levie', 'summary': 'If you think AI replaces software engineers...', 'url': 'https://x.com/levie/status/456'}
        ]
        print("=== Dry Run ===")
        print(create_digest_text(sample_items))
        print("\nPlatforms:", args.platforms)
    else:
        results = distribute_digest(args.date, args.platforms)
        for platform, result in results.items():
            if result['success']:
                print(f"✅ {platform}: Success - {result.get('url', result.get('message_id', ''))}")
            else:
                print(f"❌ {platform}: Failed - {result['error']}")
