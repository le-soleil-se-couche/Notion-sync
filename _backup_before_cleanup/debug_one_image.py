import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import httpx
from io import BytesIO
from docx import Document
from docx.shared import Inches
from PIL import Image

# Load environment variables
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
NOTION_API = "https://api.notion.com/v1"

def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

def get_notebooklm_page_id() -> str:
    # User provided specific page: https://www.notion.so/594324d996ba4e668b98d8b9cef4ea31
    return "594324d9-96ba-4e66-8b98-d8b9cef4ea31"

def list_block_children(block_id: str) -> List[Dict[str, Any]]:
    results = []
    url = f"{NOTION_API}/blocks/{block_id}/children"
    try:
        with httpx.Client(http2=False, timeout=30.0) as client:
            r = client.get(url, headers=notion_headers(NOTION_TOKEN), params={"page_size": 100})
            r.raise_for_status()
            results = r.json().get("results", [])
    except Exception as e:
        print(f"Error fetching blocks: {e}")
    return results

def main():
    page_id = get_notebooklm_page_id()
    if not page_id:
        print("Page not found")
        return

    print(f"Page ID: {page_id}")
    blocks = list_block_children(page_id)
    
    for block in blocks:
        if block["type"] == "image":
            img_data = block["image"]
            url = img_data.get(img_data["type"], {}).get("url", "")
            if "xhscdn.com" in url:
                print("Found XHS URL, saving JSON to block.json...")
                import json
                with open("block.json", "w", encoding="utf-8") as f:
                    json.dump(block, f, indent=2, ensure_ascii=False)
                
                print(f"Block ID: {block['id']}")
                break

if __name__ == "__main__":
    main()
