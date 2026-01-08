# Notion to Google Drive Sync

将 Notion 数据库中的页面同步到 Google Drive，支持增量同步和图片永久化。

## 功能

| 脚本 | 用途 |
|------|------|
| `notion_to_drive_sync.py` | 将 Notion 页面导出为 DOCX 并上传到 Google Drive |
| `notion_image_fixer.py` | 修复小红书等平台图片过期问题（上传到 Drive 并更新 Notion 链接） |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 说明 |
|------|------|
| `NOTION_TOKEN` | Notion Integration Token |
| `DATABASE_ID` | 要同步的 Notion 数据库 ID |
| `DRIVE_FOLDER_ID` | Google Drive 目标文件夹 ID |

### 3. 运行

```bash
# 同步页面到 Drive
python notion_to_drive_sync.py

# 修复小红书图片（仅处理"平台"属性为"小红书"的页面）
python notion_image_fixer.py
```

## 文件说明

```
├── notion_to_drive_sync.py   # 主同步脚本
├── notion_image_fixer.py     # 图片永久化脚本
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── client_secret.json        # Google OAuth 凭据
├── token.json                # OAuth Token（自动生成）
├── sync_state.json           # 同步状态记录
├── exports/                  # 导出的 DOCX 文件
└── _backup_before_cleanup/   # 旧版调试文件备份（可删除）
```

## 回滚

如需恢复旧版调试文件：

```powershell
Move-Item .\_backup_before_cleanup\* .\
```

## GitHub Actions 自动化

### 配置步骤

1. **上传代码到 GitHub**（如果尚未上传）
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```

2. **配置 GitHub Secrets**
   
   在仓库页面 → Settings → Secrets and variables → Actions → New repository secret，添加：
   
   | Secret Name | 值 | 说明 |
   |-------------|-----|------|
   | `NOTION_TOKEN` | `secret_xxx...` | Notion Integration Token |
   | `DATABASE_ID` | `2ddec5f4...` | Notion 数据库 ID |

3. **启用 GitHub Actions**
   
   - 进入仓库 → Actions 标签页
   - 如果首次使用，点击"I understand my workflows, go ahead and enable them"
   - 工作流会自动出现在列表中

### 运行方式

- **自动定时执行**：每天北京时间 02:00 自动运行
- **手动触发**：Actions → "Notion 图片自动修复" → Run workflow → Run workflow

### 查看日志

Actions → 点击运行记录 → "fix-notion-images" → 展开各步骤查看日志
