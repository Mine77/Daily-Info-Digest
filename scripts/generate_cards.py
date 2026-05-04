#!/usr/bin/env python3
"""
Generate shareable image cards from digest data.
Uses PIL/Pillow for image generation.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Configuration
CARD_WIDTH = 1080
CARD_HEIGHT_1_1 = 1080
CARD_HEIGHT_9_16 = 1920
BACKGROUND_COLOR = (15, 15, 18)  # #0f0f12
SURFACE_COLOR = (26, 26, 31)  # #1a1a1f
TEXT_COLOR = (232, 232, 236)  # #e8e8ec
TEXT_MUTED_COLOR = (154, 154, 164)  # #9a9aa4
ACCENT_COLOR = (99, 102, 241)  # #6366f1
BORDER_COLOR = (42, 42, 53)  # #2a2a35

# Paths
BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / 'web' / 'static' / 'reports'
CARDS_DIR = BASE_DIR / 'web' / 'static' / 'cards'
CARDS_DIR.mkdir(parents=True, exist_ok=True)

def load_font(size, bold=False):
    """Load font with fallback"""
    try:
        # Try system fonts
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        else:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

def download_avatar(url, size=80):
    """Download and resize avatar image"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            # Create circular mask
            mask = Image.new('L', (size, size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, size, size], fill=255)
            return img, mask
    except Exception as e:
        print(f"Failed to download avatar: {e}")
    return None, None

def create_card(item, aspect_ratio='1:1', index=0):
    """Create a single image card"""
    # Determine dimensions
    if aspect_ratio == '9:16':
        width, height = CARD_WIDTH, CARD_HEIGHT_9_16
    else:
        width, height = CARD_WIDTH, CARD_HEIGHT_1_1
    
    # Create image
    img = Image.new('RGB', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    title_font = load_font(32, bold=True)
    summary_font = load_font(24)
    meta_font = load_font(18)
    source_font = load_font(20, bold=True)
    
    # Calculate padding based on aspect ratio
    if aspect_ratio == '9:16':
        padding = 60
        content_width = width - (padding * 2)
    else:
        padding = 40
        content_width = width - (padding * 2)
    
    # Draw header
    y = padding
    
    # Source and type badge
    source_text = item.get('source', 'Unknown')
    type_text = item.get('type', 'tweet').upper()
    
    # Draw source
    draw.text((padding, y), source_text, font=source_font, fill=TEXT_COLOR)
    y += 30
    
    # Draw type badge
    badge_color = {
        'X': ACCENT_COLOR,
        'TWEET': ACCENT_COLOR,
        'PODCAST': (34, 197, 94),
        'BLOG': (245, 158, 11),
        'MEDIA': (167, 139, 250)
    }.get(type_text, ACCENT_COLOR)
    
    badge_width = len(type_text) * 12 + 20
    draw.rounded_rectangle(
        [padding, y, padding + badge_width, y + 24],
        radius=12,
        fill=badge_color
    )
    draw.text((padding + 10, y + 2), type_text, font=meta_font, fill=(255, 255, 255))
    y += 40
    
    # Draw separator line
    draw.line([(padding, y), (width - padding, y)], fill=BORDER_COLOR, width=2)
    y += 30
    
    # Draw summary text with word wrapping
    summary_text = item.get('summary', '')
    if not summary_text:
        summary_text = item.get('title', 'No summary available')
    
    # Simple word wrapping
    words = summary_text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=summary_font)
        if bbox[2] - bbox[0] <= content_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    # Draw summary lines
    for line in lines[:8]:  # Limit to 8 lines
        draw.text((padding, y), line, font=summary_font, fill=TEXT_COLOR)
        y += 36
    
    y += 20
    
    # Draw avatar if available
    avatar_url = item.get('avatar')
    if avatar_url:
        avatar_img, avatar_mask = download_avatar(avatar_url)
        if avatar_img:
            avatar_x = padding
            avatar_y = y
            # Paste avatar with mask
            img.paste(avatar_img, (avatar_x, avatar_y), avatar_mask)
            # Draw source name next to avatar
            draw.text((avatar_x + 90, avatar_y + 10), source_text, font=source_font, fill=TEXT_COLOR)
            draw.text((avatar_x + 90, avatar_y + 40), f"@{item.get('handle', '')}", font=meta_font, fill=TEXT_MUTED_COLOR)
            y += 100
    
    # Draw URL at bottom
    url_text = item.get('url', '')
    if url_text:
        # Shorten URL for display
        display_url = url_text[:50] + "..." if len(url_text) > 50 else url_text
        draw.text((padding, height - padding - 30), display_url, font=meta_font, fill=TEXT_MUTED_COLOR)
    
    # Draw branding at bottom
    brand_text = "AI Builders Digest"
    draw.text((width - padding - len(brand_text) * 10, height - padding - 30), 
              brand_text, font=meta_font, fill=ACCENT_COLOR)
    
    # Draw card number
    if index > 0:
        num_text = f"#{index}"
        draw.text((width - padding - 50, padding), num_text, font=meta_font, fill=TEXT_MUTED_COLOR)
    
    return img

def generate_top5_carousel(date_str=None):
    """Generate Top 5 carousel images"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    report_path = REPORTS_DIR / f'{date_str}.html'
    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return []
    
    # Parse report HTML to extract items (simplified - in production you'd parse the actual HTML)
    # For now, create sample items
    sample_items = [
        {
            'source': 'Sam Altman',
            'handle': 'sama',
            'type': 'X',
            'summary': 'i keep thinking i want the models to be cheaper/faster more than i want them to be smarter',
            'url': 'https://x.com/sama/status/2050671161915371998',
            'avatar': 'https://unavatar.io/x/sama'
        },
        {
            'source': 'Aaron Levie',
            'handle': 'levie',
            'type': 'X',
            'summary': 'If you think AI replaces software engineers, here\'s a quick thought experiment...',
            'url': 'https://x.com/levie/status/2050684160151617603',
            'avatar': 'https://unavatar.io/x/levie'
        },
        {
            'source': 'Dan Shipper',
            'handle': 'danshipper',
            'type': 'X',
            'summary': 'clear that this is how we\'ll be doing most of our work for the next 10 years',
            'url': 'https://x.com/danshipper/status/2050583747041640608',
            'avatar': 'https://unavatar.io/x/danshipper'
        },
        {
            'source': 'Training Data',
            'type': 'PODCAST',
            'summary': 'OpenAI\'s Greg Brockman: Why Human Attention Is the New Bottleneck',
            'url': 'https://www.youtube.com/playlist?list=PLOhHNjZItNnMm5tdW61JpnyxeYH5NDDx8',
            'avatar': None
        },
        {
            'source': 'Anthropic Engineering',
            'type': 'BLOG',
            'summary': 'Scaling Managed Agents: Decoupling the brain from the hands',
            'url': 'https://www.anthropic.com/engineering/managed-agents',
            'avatar': None
        }
    ]
    
    generated_files = []
    
    # Generate 1:1 cards
    print("Generating 1:1 cards...")
    for i, item in enumerate(sample_items[:5], 1):
        img = create_card(item, aspect_ratio='1:1', index=i)
        filename = f'{date_str}_top{i}_1x1.png'
        filepath = CARDS_DIR / filename
        img.save(filepath, quality=95)
        generated_files.append(str(filepath))
        print(f"  Created: {filename}")
    
    # Generate 9:16 cards
    print("Generating 9:16 cards...")
    for i, item in enumerate(sample_items[:5], 1):
        img = create_card(item, aspect_ratio='9:16', index=i)
        filename = f'{date_str}_top{i}_9x16.png'
        filepath = CARDS_DIR / filename
        img.save(filepath, quality=95)
        generated_files.append(str(filepath))
        print(f"  Created: {filename}")
    
    return generated_files

def generate_single_card(item, aspect_ratio='1:1', index=0):
    """Generate a single card"""
    img = create_card(item, aspect_ratio, index)
    filename = f"card_{index}_{aspect_ratio.replace(':', 'x')}.png"
    filepath = CARDS_DIR / filename
    img.save(filepath, quality=95)
    return str(filepath)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate image cards from digest')
    parser.add_argument('--date', type=str, help='Date to generate cards for (YYYY-MM-DD)')
    parser.add_argument('--aspect', choices=['1:1', '9:16', 'both'], default='both',
                       help='Aspect ratio for cards')
    parser.add_argument('--top', type=int, default=5, help='Number of top items to generate')
    
    args = parser.parse_args()
    
    print("Generating image cards...")
    files = generate_top5_carousel(args.date)
    print(f"\nGenerated {len(files)} cards in {CARDS_DIR}")
