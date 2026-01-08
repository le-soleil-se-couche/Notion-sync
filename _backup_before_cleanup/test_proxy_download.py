import os
import json
import httpx
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # 1. Check for Token
    token_v2 = os.getenv("NOTION_TOKEN_V2")
    if not token_v2:
        print("Error: NOTION_TOKEN_V2 not found in .env file.")
        print("Please add 'NOTION_TOKEN_V2=your_token_value' to .env")
        return

    # 2. Read Target Block Info
    try:
        with open("block.json", "r", encoding="utf-8") as f:
            block = json.load(f)
    except FileNotFoundError:
        print("Error: block.json not found. Please run debug_one_image.py first.")
        return

    # Extract info
    block_id = block["id"]
    try:
        original_url = block["image"]["external"]["url"]
    except KeyError:
        print("Error: Could not find image url in block.json")
        return

    print(f"Target Block ID: {block_id}")
    print(f"Original URL (Expired): {original_url[:60]}...")

    # 3. Construct Proxy URL
    # https://www.notion.so/image/{encoded_url}?table=block&id={block_id}&cache=v2
    encoded_url = urllib.parse.quote(original_url, safe='')
    proxy_url = f"https://www.notion.so/image/{encoded_url}?table=block&id={block_id}&cache=v2"
    
    print(f"\nProxy URL: {proxy_url[:80]}...")

    # 4. Download with Cookie
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"token_v2={token_v2}",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
    }

    print("\nAttempting download via Notion Proxy...")
    try:
        # Enable HTTP/2 for Notion internal usage if supported, or stick to http1.1 for safety first
        # httpx requires 'httpx[http2]' for http2 support. Fallback to False to be safe.
        with httpx.Client(http2=False, verify=False, follow_redirects=True, timeout=30.0) as client:
            r = client.get(proxy_url, headers=headers)
            
            with open("proxy_debug.log", "w", encoding="utf-8") as log:
                log.write(f"URL: {proxy_url}\n")
                log.write(f"Status: {r.status_code}\n")
                log.write(f"Headers: {dict(r.headers)}\n")
                log.write(f"Body Preview: {r.text[:500]}\n")
            
            if r.status_code == 200:
                print("Download SUCCESS! (From Notion Cache)")
                ext = "bin"
                ctype = r.headers.get("content-type", "")
                if "webp" in ctype: ext = "webp"
                elif "png" in ctype: ext = "png"
                elif "jpeg" in ctype or "jpg" in ctype: ext = "jpg"
                
                filename = f"proxy_test_download.{ext}"
                with open(filename, "wb") as f:
                    f.write(r.content)
                print(f"Saved to {filename}")
            else:
                print(f"Download Failed. Body preview:\n{r.text[:300]}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
