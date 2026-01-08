"""Notion 图片洗链脚本 (XHS Image Fixer)
将小红书外链图片 (xhscdn.com) 迁移到 Notion 内部存储 (Direct Upload)。
解决防盗链和签名过期导致的导出失败问题。
"""
from __future__ import annotations

import os
import time
import json
import logging
import hashlib
import httpx
from typing import Optional, Tuple, Dict, Any, List
from io import BytesIO
from datetime import datetime, timezone
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables
load_dotenv()

# Configuration
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
DATABASE_ID = os.getenv("DATABASE_ID", "").strip()

# Format DB ID if needed
if len(DATABASE_ID) == 32:
    DATABASE_ID = f"{DATABASE_ID[:8]}-{DATABASE_ID[8:12]}-{DATABASE_ID[12:16]}-{DATABASE_ID[16:20]}-{DATABASE_ID[20:]}"

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Headers for downloading images (Anti-hotlink)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixer.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def sniff_ext_and_mime(content: bytes, fallback_mime: str = "application/octet-stream") -> Tuple[str, str]:
    """Simple content sniffing to determine file extension and mime type."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return "", fallback_mime


def download_xhs_image(url: str, timeout: float = 30.0) -> Optional[Tuple[bytes, str]]:
    """
    Download image from XHS CDN using browser-like headers.
    Returns (content_bytes, mime_type) or None if failed.
    """
    # Parse domain for Referer
    from urllib.parse import urlparse
    parsed = urlparse(url)
    referer_domain = f"{parsed.scheme}://{parsed.netloc}/"
    
    headers = {
        "User-Agent": UA,
        "Referer": referer_domain,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    
    try:
        # Disable HTTP/2 as it causes SSL EOF errors with some CDNs/proxies
        # Verify=False to avoid certificate issues (optional but safer for stability here)
        with httpx.Client(follow_redirects=True, timeout=timeout, http2=False, verify=False, headers=headers) as client:
            r = client.get(url)
            if r.status_code != 200 or not r.content:
                logging.warning(f"Download failed: {r.status_code} - {url[:60]}...")
                return None
            
            ctype = (r.headers.get("content-type") or "").split(";")[0].strip()
            if ctype and not ctype.startswith("image/"):
                logging.warning(f"Invalid content-type: {ctype} for {url[:60]}...")
                # Allow ignoring this check if it looks like an image but has wrong header
                if len(r.content) < 1000: # Too small likely not an image
                     return None
            
            return r.content, (ctype or "application/octet-stream")
    except Exception as e:
        logging.error(f"Download exception: {e}")
        return None


def notion_headers(notion_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Accept": "application/json",
    }


def create_file_upload(notion_token: str, filename: str, content_type: str) -> str:
    """Step 1: Create a File Upload object and get upload URL/ID."""
    payload = {"filename": filename, "content_type": content_type}
    try:
        r = httpx.post(
            f"{NOTION_API}/file_uploads",
            headers={**notion_headers(notion_token), "Content-Type": "application/json"},
            json=payload,
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Create file upload failed: {e}")
        if 'r' in locals():
            logging.error(f"Response: {r.text}")
        raise e


def send_file_upload(notion_token: str, upload_url: str, filename: str, content_type: str, content: bytes) -> None:
    """Step 2: Upload partial content to the signed URL."""
    # Note: The official docs say to use the signed URL directly
    r = httpx.put(
        upload_url,
        headers={"Content-Type": content_type},
        content=content,
        timeout=60.0,
    )
    r.raise_for_status()


def update_image_block_to_file_upload(
    notion_token: str,
    block_id: str,
    file_id: str,
    access_url: str,
    caption: Optional[list] = None,
) -> None:
    """
    Step 3: Update the block to point to the uploaded file.
    Note: 'file_uploads' API is internal/beta.
    The official public API uses 'file' type with 'external' or 'file' object.
    But for 'Direct Upload' we are essentially creating an Internal file.
    
    Wait: The Notion Public API does NOT strictly support 'Direct Upload' for 3rd party apps yet 
    in the sense of hosting the file on Notion's S3 bucket indefinitely without using the 'file' object 
    pointing to an external URL. 
    However, the user selected 'Notion Direct Upload' (Scheme A) which implies we try to mimic 
    uploading to Notion.
    
    Wait, Scheme A description says:
    Step 1: POST /v1/file_uploads ...
    Step 2: POST /v1/file_uploads/{id}/send ...
    Step 3: PATCH /v1/blocks/{block_id} with type='file_upload'
    
    This suggests using an internal/undocumented API or a specific capability. 
    Let's implement exactly as Scheme A described.
    """
    
    # As per Scheme A description:
    image_obj: Dict[str, Any] = {
        "type": "file_upload",
        "file_upload": {"id": file_id},
    }
    if caption:
        image_obj["caption"] = caption

    payload = {"image": image_obj}

    try:
        r = httpx.patch(
            f"{NOTION_API}/blocks/{block_id}",
            headers={**notion_headers(notion_token), "Content-Type": "application/json"},
            json=payload,
            timeout=30.0,
        )
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Update block {block_id} failed: {e}")
        if 'r' in locals():
            logging.error(f"Response: {r.text}")
        raise e


def migrate_one_image_block(notion_token: str, block: Dict[str, Any]) -> bool:
    block_id = block["id"]
    image_data = block.get("image", {})
    
    # Only process external images
    if image_data.get("type") != "external":
        return False
        
    xhs_url = image_data.get("external", {}).get("url", "")
    caption = image_data.get("caption", [])
    
    # Check if it's an XHS image
    if "xhscdn.com" not in xhs_url:
        return False
        
    logging.info(f"==> Processor XHS Image in Block {block_id}")
    logging.info(f"    URL: {xhs_url[:80]}...")
    
    # 1. Download
    got = download_xhs_image(xhs_url)
    if not got:
        logging.warning("    [FAIL] Download failed.")
        return False

    content, resp_mime = got
    ext, mime = sniff_ext_and_mime(content, fallback_mime=resp_mime or "application/octet-stream")
    
    # Generate filename
    sha = hashlib.sha256(content).hexdigest()[:16]
    filename = f"xhs_{sha}{ext or '.jpg'}"
    
    logging.info(f"    [OK] Downloaded {len(content)} bytes. Filename: {filename}")

    try:
        # 2. Upload (Using the specific flow described in Scheme A)
        # However, checking Notion API docs, 'file_uploads' endpoint is not standard public API.
        # It seems the user provided instructions for an internal or specific API version.
        # I will implement exactly as requested but add error handling.
        
        # Implement exactly as Scheme A:
        # Step 1: Create
        payload = {"filename": filename, "content_type": mime}
        r1 = httpx.post(
            f"{NOTION_API}/file_uploads",
            headers={**notion_headers(notion_token), "Content-Type": "application/json"},
            json=payload,
            timeout=30.0
        )
        r1.raise_for_status()
        file_data = r1.json()
        file_upload_id = file_data["id"]
        # The response usually contains a signed URL for upload
        # Scheme A says: POST /v1/file_uploads/{id}/send with multipart
        # Let's try to follow Scheme A strictly first.
        
        # Step 2: Send content
        files = {"file": (filename, BytesIO(content), mime)}
        r2 = httpx.post(
            f"{NOTION_API}/file_uploads/{file_upload_id}/send",
            headers=notion_headers(notion_token), # requests/httpx will set Content-Type boundary
            files=files,
            timeout=60.0
        )
        r2.raise_for_status()
        
        logging.info("    [OK] Uploaded to Notion.")
        
        # Step 3: Update Block
        update_image_block_to_file_upload(notion_token, block_id, file_upload_id, "", caption)
        logging.info("    [SUCCESS] Block updated.")
        return True
        
    except Exception as e:
        logging.error(f"    [FAIL] Upload/Update failed: {e}")
        return False


def get_database_pages(database_id: str) -> List[Dict[str, Any]]:
    """Fetch all pages from database using httpx with retry."""
    pages = []
    cursor = None
    url = f"{NOTION_API}/databases/{database_id}/query"
    
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
            
        success = False
        for attempt in range(3):
            try:
                r = httpx.post(
                    url,
                    headers=notion_headers(NOTION_TOKEN),
                    json=payload,
                    timeout=30.0
                )
                r.raise_for_status()
                data = r.json()
                pages.extend(data.get("results", []))
                
                if not data.get("has_more"):
                    return pages # Done
                cursor = data.get("next_cursor")
                success = True
                break
            except Exception as e:
                logging.warning(f"Query database attempt {attempt+1} failed: {e}")
                time.sleep(2)
        
        if not success:
            logging.error("Failed to query database pages after retries.")
            break
            
    return pages


def get_all_blocks(block_id: str) -> List[Dict[str, Any]]:
    """Fetch all children blocks recursively with retry."""
    results = []
    cursor = None
    url = f"{NOTION_API}/blocks/{block_id}/children"
    
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        
        success = False
        for attempt in range(3):
            try:
                r = httpx.get(
                    url,
                    headers=notion_headers(NOTION_TOKEN),
                    params=params, 
                    timeout=30.0
                )
                if r.status_code == 404: 
                    return results # Block might not allow children or deleted
                r.raise_for_status()
                
                data = r.json()
                blocks = data.get("results", [])
                results.extend(blocks)
                
                if not data.get("has_more"):
                    return results # Done
                cursor = data.get("next_cursor")
                success = True
                break
            except Exception as e:
                logging.warning(f"List blocks attempt {attempt+1} failed for {block_id}: {e}")
                time.sleep(2)
                
        if not success:
            logging.error(f"Failed to list blocks for {block_id} after retries.")
            break
            
    return results


def scan_and_fix_database(dry_run: bool = False):
    logging.info(f"Scanning database {DATABASE_ID} for XHS images...")
    
    pages = get_database_pages(DATABASE_ID)
    logging.info(f"Found {len(pages)} pages.")

    total_fixed = 0
    total_failed = 0
    
    for page in pages:
        page_id = page["id"]
        
        # Get title for logging
        title = "Untitled"
        for prop in page.get("properties", {}).values():
            if prop.get("type") == "title":
                t = prop.get("title", [])
                if t: title = "".join([x.get("plain_text", "") for x in t])
                break
                
        logging.info(f"Checking page: {title} ({page_id})")
        
        # Recursive scan structure using a stack
        # This allows handling nested blocks like columns, toggles, etc.
        blocks_to_scan = get_all_blocks(page_id)
        # Convert list to a stack (reverse order so we pop in order, though order doesn't strictly matter for fixing)
        # We store tuples: (block_data, depth)
        
        stack = [(b, 0) for b in blocks_to_scan]
        
        scanned_count = 0
        img_count = 0
        xhs_count = 0
        
        while stack:
            block, depth = stack.pop(0) # BFS-like for easier log reading, or pop() for DFS
            scanned_count += 1
            
            b_type = block.get("type")
            
            if b_type == "image":
                img = block.get("image", {})
                if img.get("type") == "external":
                    url = img.get("external", {}).get("url", "")
                    logging.info(f"    [IMG FOUND] Depth={depth} URL={url[:60]}...")
                    img_count += 1
                    
                    if "xhscdn.com" in url:
                        logging.info(f"    [TARGET MATCH] Found XHS image at depth {depth}")
                        xhs_count += 1
                        if dry_run:
                            logging.info(f"      [DRY RUN] Would fix image in block {block['id']}")
                        else:
                            success = migrate_one_image_block(NOTION_TOKEN, block)
                            if success:
                                total_fixed += 1
                                logging.info(f"      [FIXED] Block {block['id']}")
                            else:
                                total_failed += 1
                                logging.warning(f"      [FAILED] Block {block['id']}")
            
            # Check for children
            if block.get("has_children"):
                # Avoid going too deep if not needed, but generally we want to find all images
                if depth < 3: # Limit recursion depth to 3 levels for safety
                    children = get_all_blocks(block["id"])
                    for child in children:
                        stack.append((child, depth + 1))
        
        logging.info(f"  Page Scan Summary: Scanned {scanned_count} blocks. Found {img_count} images ({xhs_count} XHS).")

    logging.info("="*40)
    logging.info(f"Scan Complete. Fixed: {total_fixed}, Failed: {total_failed}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix XHS images in Notion")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not modify")
    args = parser.parse_args()
    
    scan_and_fix_database(dry_run=args.dry_run)
