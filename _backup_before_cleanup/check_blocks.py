import os
import logging
from typing import List, Dict, Any
from notion_client import Client
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
# 指定一个已知的有问题页面ID（来自之前的日志）
PAGE_ID = "5e808578-751c-434b-ae8b-8914d169426c"  # 替换为你想要检查的页面ID

NOTION_API = "https://api.notion.com/v1"

def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28", # Or whatever version is stable
        "Content-Type": "application/json",
    }

def get_latest_page_id() -> str:
    url = f"{NOTION_API}/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "title",
            "rich_text": {
                "contains": "NotebookLM"
            }
        }
    }
    try:
        # Use httpx for query too
        r = httpx.post(url, headers=notion_headers(NOTION_TOKEN), json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data["results"]:
            page = data["results"][0]
            title = "Untitled"
            if "properties" in page:
                try:
                    for prop in page["properties"].values():
                        if prop["type"] == "title":
                            title = prop["title"][0]["plain_text"]
                            break
                except:
                    pass
            print(f"Latest Page Found: {title} ({page['id']})")
            return page["id"]
    except Exception as e:
        print(f"Error getting latest page: {e}")
    return None

def list_block_children(block_id: str) -> List[Dict[str, Any]]:
    results = []
    cursor = None
    url = f"{NOTION_API}/blocks/{block_id}/children"
    
    while True:
        try:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            
            r = httpx.get(url, headers=notion_headers(NOTION_TOKEN), params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            results.extend(data.get("results", []))
            
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        except Exception as e:
            print(f"Error fetching blocks: {e}")
            break
    return results

def main():
    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN not found in .env")
        return

    # Auto-detect latest page
    page_id = get_latest_page_id()
    if not page_id:
        print("Could not find any pages.")
        return

    print(f"Checking Page ID: {page_id}")
    
    try:
        blocks = list_block_children(page_id)
        print(f"Found {len(blocks)} blocks.")
        
        found_img = False
        for i, block in enumerate(blocks):
            if block["type"] == "image":
                img_data = block["image"]
                img_type = img_data["type"]
                url = img_data.get(img_type, {}).get("url", "")
                
                print(f"\n[Block {i}] Image Type: {img_type}")
                print(f"URL: {url[:80]}...")
                
                if "xhscdn.com" in url:
                    print("--> Target XHS Image Found!")
                    print(url) # Print Full URL
                    
                    found_img = True
                    # Test Download Immediately
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.xiaohongshu.com/",
                        "Accept": "image/webp,image/*,*/*;q=0.8"
                    }
                    print("Attempting download with headers (http2=False, verify=False)...")
                    try:
                        # Mimic the main script's exact config
                        with httpx.Client(http2=False, verify=False, follow_redirects=True, timeout=10) as client:
                            r = client.get(url, headers=headers)
                            print(f"Status Code: {r.status_code}")
                            print(f"Content Type: {r.headers.get('content-type')}")
                            print(f"Content Length: {len(r.content)} bytes")
                            
                            if r.status_code != 200:
                                print(f"\nResponse Body Preview:\n{r.text[:500]}")
                            else:
                                print("Download SUCCESS!")
                    except Exception as e:
                        print(f"Download Exception: {e}")
                    
                    except Exception as e:
                        print(f"Download Exception: {e}")
                    
                    # Do not break, check all images to see if rate limit kicks in
                    import time
                    time.sleep(1) 
                    
        # Loop finished
        
        if not found_img:
            print("No XHS images found in this page.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
