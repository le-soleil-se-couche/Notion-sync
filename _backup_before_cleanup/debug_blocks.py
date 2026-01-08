"""Debug script to check why some pages have no blocks."""
import json
import httpx
from dotenv import load_dotenv
import os
import time

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN', '').strip()
DATABASE_ID = os.getenv('DATABASE_ID', '').strip()

if len(DATABASE_ID) == 32:
    DATABASE_ID = f'{DATABASE_ID[:8]}-{DATABASE_ID[8:12]}-{DATABASE_ID[12:16]}-{DATABASE_ID[16:20]}-{DATABASE_ID[20:]}'

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

# Query the database to get pages
url = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
response = httpx.post(url, headers=headers, json={'page_size': 10}, timeout=60.0)
data = response.json()

print('=== Checking Pages for Blocks ===\n')

for i, page in enumerate(data.get('results', [])):
    page_id = page['id']
    # Get title
    title = 'Untitled'
    for prop_name, prop in page.get('properties', {}).items():
        if prop.get('type') == 'title':
            title_parts = prop.get('title', [])
            title = ''.join([p.get('plain_text', '') for p in title_parts])
            break
    
    # Check blocks
    blocks_url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    blocks_resp = httpx.get(blocks_url, headers=headers, timeout=60.0)
    blocks_data = blocks_resp.json()
    
    time.sleep(0.3)  # Rate limit
    
    if 'error' in blocks_data:
        print(f'[{i+1}] "{title[:40]}..."')
        print(f'    ERROR: {blocks_data.get("code")} - {blocks_data.get("message")}')
    else:
        results = blocks_data.get('results', [])
        block_types = [b.get('type') for b in results[:5]] if results else []
        
        print(f'[{i+1}] "{title[:40]}..."')
        print(f'    Page ID: {page_id}')
        print(f'    Blocks: {len(results)}')
        
        if not results:
            print(f'    >>> NO BLOCKS FOUND!')
            # Show properties
            props = list(page.get('properties', {}).keys())
            print(f'    Properties: {props}')
            
            # Check if this page is a synced database item (linked database)
            if 'URL' in page.get('properties', {}):
                url_prop = page['properties']['URL']
                if url_prop.get('type') == 'url':
                    print(f'    URL property: {url_prop.get("url", "N/A")}')
        else:
            print(f'    Block types: {block_types}')
    
    print()

print('=== Check Complete ===')
