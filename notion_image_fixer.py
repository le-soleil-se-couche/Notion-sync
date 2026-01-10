import logging
import os
import sys
import time
import json
import httpx
from typing import Dict, Any, List, Optional, Tuple
from io import BytesIO
from pathlib import Path
import urllib.parse
from PIL import Image

from dotenv import load_dotenv

from notion_client import Client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# 配置项
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_TOKEN_V2 = os.getenv("NOTION_TOKEN_V2", "").strip()
DATABASE_ID = os.getenv("DATABASE_ID", "").strip()
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

NOTION_RATE_LIMIT_DELAY = 0.4
NOTION_VERSION_QUERY = "2022-06-28"   # Old version for Database Query (avoid DataSource schema)
NOTION_VERSION_UPLOAD = "2025-09-03"  # New version for File Uploads

def get_notion_headers(version: str = NOTION_VERSION_UPLOAD):
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": version,
        "Accept": "application/json",
    }

def create_file_upload(filename: str, content_type: str) -> str:
    """创建 Notion 文件上传会话"""
    url = "https://api.notion.com/v1/file_uploads"
    # File upload requires new version
    headers = {**get_notion_headers(NOTION_VERSION_UPLOAD), "Content-Type": "application/json"}
    body = {"filename": filename, "content_type": content_type}
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=30.0)
        resp.raise_for_status()
        return resp.json()["id"]
    except httpx.HTTPStatusError as e:
        logging.error(f"[API ERROR] create_file_upload failed: {e.response.text}")
        raise e


def send_file_upload(file_upload_id: str, filename: str, content_type: str, content: bytes):
    """发送文件内容到 Notion 上传会话"""
    url = f"https://api.notion.com/v1/file_uploads/{file_upload_id}/send"
    headers = get_notion_headers(NOTION_VERSION_UPLOAD)
    # httpx 会自动设置 multipart boundaries
    files = {"file": (filename, BytesIO(content), content_type)}
    try:
        resp = httpx.post(url, headers=headers, files=files, timeout=60.0)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(f"[API ERROR] send_file_upload failed: {e.response.text}")
        raise e


def download_image_to_stream(url: str, block_id: str = None) -> Tuple[Optional[BytesIO], Optional[str]]:
    """下载图片并返回 (BytesIO, MIME-Type)"""
    # === Direct Download ===
    try:
        # 使用 verify=False 和 headers 模拟浏览器，防止某些防盗链 (如小红书)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 小红书特殊处理
        if "xhscdn.com" in url:
             headers["Referer"] = "https://www.xiaohongshu.com/"

        # http2=False 更稳定
        with httpx.Client(http2=False, verify=False, headers=headers, follow_redirects=True, timeout=30.0) as client:
            response = client.get(url)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "image/jpeg")
                return BytesIO(response.content), content_type
            else:
                logging.warning(f"Direct download failed: {response.status_code}")
    except Exception as e:
        logging.warning(f"Failed to download image (direct): {e}")

    # === Fallback: Notion Proxy ===
    if block_id and NOTION_TOKEN_V2:
        logging.info(f"Attempting Fallback via Notion Proxy for block {block_id}...")
        try:
            encoded_url = urllib.parse.quote(url, safe='')
            proxy_url = f"https://www.notion.so/image/{encoded_url}?table=block&id={block_id}&cache=v2"
            
            proxy_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Cookie": f"token_v2={NOTION_TOKEN_V2}",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            
            with httpx.Client(http2=False, verify=False, follow_redirects=True, timeout=30.0) as client:
                r = client.get(proxy_url, headers=proxy_headers)
                if r.status_code == 200:
                     logging.info(f"[OK] Proxy Download SUCCESS! Size: {len(r.content)}")
                     stream = BytesIO(r.content)
                     content_type = r.headers.get("content-type", "image/jpeg")
                     
                     # Simple conversion check if needed (Notion uploads support webp, but just in case)
                     return stream, content_type
                else:
                    logging.warning(f"[FAIL] Proxy Download Failed: Status {r.status_code}")
        except Exception as e:
            logging.error(f"[FAIL] Proxy Download Exception: {e}")

    return None, None


def update_notion_image_in_place(block_id: str, file_upload_id: str):
    """
    需要使用新版本 API (NOTION_VERSION_UPLOAD)
    注意：Payload 不包含 "type" 字段，只包含 "file_upload" 对象，以绕过 Update 校验
    """
    headers = get_notion_headers(NOTION_VERSION_UPLOAD)
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    payload = {
        "image": {
            "file_upload": {
                "id": file_upload_id
            }
        }
    }
    try:
        resp = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        resp.raise_for_status()
        logging.info(f"[OK] Successfully updated Notion block {block_id} (In-Place)")
    except httpx.HTTPStatusError as e:
        logging.error(f"[API ERROR] update_notion_image_in_place failed: {e.response.text}")
        raise e
    except Exception as e:
        logging.error(f"[FAIL] Failed to update Notion block {block_id}: {e}")


def list_block_children_safe(block_id: str) -> List[Dict[str, Any]]:
    """
    """
    blocks = []
    cursor = None
    # Block children list works with both, but let's stick to query version for safety unless we need new features
    # Actually, for deep fetching, either is fine. Let's use Query version to be safe, or Upload version?
    # User suggested: "File Upload / block update 继续用新版本".
    # Listing children is a read operation. Using Query version (old) is safer for compatibility.
    headers = get_notion_headers(NOTION_VERSION_QUERY)
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"

    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor

        try:
            response = httpx.get(url, headers=headers, params=params, timeout=30.0)
            # 如果是 404 等非重试错误，直接返回
            if response.status_code == 404:
                return blocks
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"[API ERROR] list_block_children_safe failed: {e.response.text}")
            return blocks
        except Exception as e:
            logging.error(f"Error fetching children for {block_id}: {e}")
            return blocks

        time.sleep(NOTION_RATE_LIMIT_DELAY)
        blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    
    return blocks


def process_block_recursively(block: Dict[str, Any], depth=0):
    """
    递归处理页面中的所有块：
    检查图片是否为XHS外链，若是则进行 File Upload 修复 (In-Place Update)
    """
    block_id = block["id"]
    block_type = block.get("type")

    # === 1. 处理图片 ===
    if block_type == "image":
        image_info = block.get("image", {})
        img_type = image_info.get("type")
        url_to_process = None
        
        # 情况A: Notion 托管 (忽略)
        if img_type == "file":
             logging.info(f"{'  '*depth}[SKIP] Notion hosted image (already fixed): {block_id}")
            
        # 情况B: 外部链接
        elif img_type == "external":
            url = image_info.get("external", {}).get("url", "")
            # 扩展域名匹配列表，增加日志
            # Whitelist: XHS (primary), WeChat/Tencent (common in XHS reposts)
            # qpic.cn / mmbiz covers WeChat images often found in XHS notes
            target_domains = ["xhscdn", "xiaohongshu.com", "qpic.cn", "mmbiz"]
            is_target_domain = any(domain in url for domain in target_domains)
            
            if is_target_domain:
                url_to_process = url
                logging.info(f"{'  '*depth}[IMG-TARGET] Found valid external image in block {block_id}")
            else:
                logging.warning(f"{'  '*depth}[SKIP-EXT] Found NON-TARGET external image in block {block_id}. URL: {url}")
    
        if url_to_process:
            # 下载
            stream, mime = download_image_to_stream(url_to_process, block_id=block_id)
            
            if stream:
                content = stream.read()
                filename = f"fixed_{block_id}.{mime.split('/')[-1] if mime else 'jpg'}"
                
                try:
                    logging.info(f"{'  '*depth}--> Fixing image: {filename}")
                    # 1. Create Upload
                    upload_id = create_file_upload(filename, mime or "image/jpeg")
                    # 2. Send Content
                    send_file_upload(upload_id, filename, mime or "image/jpeg", content)
                    # 3. Update Block (In-Place)
                    update_notion_image_in_place(block_id, upload_id)
                except Exception as e:
                    logging.error(f"{'  '*depth}[ERROR] Failed to fix block {block_id}: {e}")
            else:
                 logging.warning(f"{'  '*depth}[WARN] Failed to download content for block {block_id}. URL might be expired.")

    # === 2. 递归子块 ===
    if block.get("has_children"):
        children = list_block_children_safe(block_id)
        for child in children:
            process_block_recursively(child, depth + 1)


def determine_filter_type(database_id: str) -> Optional[Dict[str, Any]]:
    """
    Check the property type of '平台' by querying one page.
    Returns the appropriate filter object.
    DANGER: Query needs OLD version (NOTION_VERSION_QUERY)
    """
    headers = get_notion_headers(NOTION_VERSION_QUERY)
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    # Query one page to inspect properties
    # Query one page to inspect properties
    try:
        response = httpx.post(url, headers=headers, json={"page_size": 1}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            logging.warning("[WARN] Database is empty, cannot determine property type automatically.")
            return None
            
        props = results[0].get("properties", {})
        platform_prop = props.get("平台")
        
        if not platform_prop:
            logging.warning("[WARN] Property 'pingtai' not found in database. Processing ALL pages.")
            return None
            
        prop_type = platform_prop.get("type")
        logging.info(f"[INFO] Detected property 'pingtai' type: {prop_type}")
        
        if prop_type == "select":
            return {
                "property": "平台",
                "select": {
                    "equals": "小红书"
                }
            }
        elif prop_type == "multi_select":
            return {
                "property": "平台",
                "multi_select": {
                    "contains": "小红书"
                }
            }
        else:
            logging.warning(f"[WARN] Property 'pingtai' is {prop_type}, not select/multi_select. Filter logic might need adjustment.")
            return None
            
    except httpx.HTTPStatusError as e:
        logging.error(f"[API ERROR] determine_filter_type failed: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"[FAIL] Error determining filter type: {e}")
        return None


def query_all_pages(database_id: str) -> List[Dict[str, Any]]:
    """查询所有页面 (带过滤)"""
    pages = []
    has_more = True
    next_cursor = None
    
    # Query Database MUST use OLD version
    headers = get_notion_headers(NOTION_VERSION_QUERY)
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    # 动态构建过滤器
    notion_filter = determine_filter_type(database_id)
    if notion_filter:
        logging.info(f"[FILTER] Applying filter: {json.dumps(notion_filter, ensure_ascii=False)}")
    else:
        logging.info("[WARN] No filter applied (All pages will be scanned)")

    logging.info(f"Querying database {database_id}...")

    while has_more:
        body = {"page_size": 100}
        if notion_filter:
            body["filter"] = notion_filter
        if next_cursor:
            body["start_cursor"] = next_cursor

        try:
            response = httpx.post(url, headers=headers, json=body, timeout=60.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"[API ERROR] query_all_pages failed: {e.response.text}")
            raise e
        
        pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
        time.sleep(0.3)
    
    return pages


def main():
    if not all([NOTION_TOKEN, DATABASE_ID]):
       print("[ERROR] Missing required env vars: NOTION_TOKEN, DATABASE_ID")
       return

    print("[START] Starting Notion Image Fixer (File Upload Mode)...")
    
    # 获取所有页面
    try:
        pages = query_all_pages(DATABASE_ID)
    except Exception as e:
        print(f"[ERROR] Failed to query database: {e}")
        return

    print(f"[INFO] Found {len(pages)} pages. Starting scan...")
    
    for page in pages:
        page_id = page["id"]
        title = "Untitled"
        # 尝试获取标题用于日志 (适配 title 属性)
        for prop in page.get("properties", {}).values():
            if prop["type"] == "title":
                t = prop.get("title", [])
                if t: title = t[0].get("plain_text", "Untitled")
        
        logging.info(f"[PAGE] Scanning page: {title} ({page_id})")
        
        # 获取页面的第一层子块
        children = list_block_children_safe(page_id)
        for child in children:
            process_block_recursively(child, depth=1)
            
    print("[DONE] All done!")

if __name__ == "__main__":
    main()
