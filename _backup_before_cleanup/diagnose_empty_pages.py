"""诊断脚本：检查为什么某些页面没有blocks - 输出到文件"""
import json
import httpx
from dotenv import load_dotenv
import os

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

# 打开输出文件
with open('diagnosis_report.txt', 'w', encoding='utf-8') as f:
    # 查询数据库获取所有页面
    url = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
    response = httpx.post(url, headers=headers, json={'page_size': 100}, timeout=60.0)
    data = response.json()

    f.write(f"总共 {len(data.get('results', []))} 个页面\n\n")

    empty_pages = []
    
    # 检查每个页面
    for page in data.get('results', []):
        page_id = page['id']
        
        # 获取标题
        title = 'Untitled'
        for prop_name, prop in page.get('properties', {}).items():
            if prop.get('type') == 'title':
                title_parts = prop.get('title', [])
                title = ''.join([p.get('plain_text', '') for p in title_parts])
                break
        
        # 获取blocks
        blocks_url = f'https://api.notion.com/v1/blocks/{page_id}/children'
        blocks_resp = httpx.get(blocks_url, headers=headers, timeout=60.0)
        blocks_data = blocks_resp.json()
        
        blocks = blocks_data.get('results', [])
        
        if len(blocks) == 0:
            empty_pages.append({
                'title': title,
                'page_id': page_id,
                'page': page,
                'blocks_response': blocks_data
            })
            f.write(f"[空] {title}\n")
        else:
            f.write(f"[OK] {title} ({len(blocks)} blocks)\n")
    
    f.write(f"\n\n{'='*80}\n")
    f.write(f"空页面详细分析 ({len(empty_pages)} 个)\n")
    f.write(f"{'='*80}\n\n")
    
    for item in empty_pages:
        title = item['title']
        page = item['page']
        blocks_data = item['blocks_response']
        
        f.write(f"\n### {title}\n")
        f.write(f"Page ID: {item['page_id']}\n")
        f.write(f"URL: {page.get('url', 'N/A')}\n")
        
        # 检查blocks API响应
        if 'error' in blocks_data:
            f.write(f"!!! API ERROR: {blocks_data.get('code')} - {blocks_data.get('message')}\n")
        else:
            f.write(f"Blocks API returned: {len(blocks_data.get('results', []))} results\n")
        
        # 打印所有properties
        f.write("Properties:\n")
        for prop_name, prop in page.get('properties', {}).items():
            prop_type = prop.get('type')
            if prop_type == 'title':
                continue
            elif prop_type == 'url':
                val = prop.get('url', 'None')
                f.write(f"  - {prop_name} (url): {val}\n")
            elif prop_type == 'rich_text':
                text = ''.join([p.get('plain_text', '') for p in prop.get('rich_text', [])])
                f.write(f"  - {prop_name} (rich_text): {text[:200] if text else 'empty'}\n")
            elif prop_type == 'select':
                sel = prop.get('select')
                f.write(f"  - {prop_name} (select): {sel.get('name') if sel else 'None'}\n")
            elif prop_type == 'status':
                status = prop.get('status')
                f.write(f"  - {prop_name} (status): {status.get('name') if status else 'None'}\n")
            else:
                f.write(f"  - {prop_name} ({prop_type})\n")
        
        # Parent信息
        parent = page.get('parent', {})
        f.write(f"Parent type: {parent.get('type')}\n")
        
        # 保存完整的页面JSON供分析
        f.write(f"\n--- Raw Page JSON ---\n")
        f.write(json.dumps(page, indent=2, ensure_ascii=False)[:3000])
        f.write("\n\n")
        
        f.write("-"*60 + "\n")

print("诊断报告已保存到 diagnosis_report.txt")
