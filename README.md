# Notion to Google Drive Sync

将 Notion 数据库内容自动同步到 Google Drive，解决 Save to Notion 插件图片链接过期问题。

## ✨ 功能特性

- 🖼️ **图片永久化**：自动将外部图片（小红书、微信公众号等）迁移到 Notion 内部存储
- 📦 **自动备份**：将 Notion 页面导出为 DOCX 格式并上传至 Google Drive
- ⏰ **定时执行**：通过 GitHub Actions 每天自动运行
- 🔄 **代理回退**：支持 Notion 内部代理，即使原链接过期也能挽救图片

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 `Fork` 按钮创建你自己的副本。

### 2. 配置 GitHub Secrets

进入你 Fork 后的仓库：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下 Secrets：

| Secret 名称 | 说明 | 获取方式 |
|---|---|---|
| `NOTION_TOKEN` | Notion API 集成密钥 | [Notion Integrations](https://www.notion.so/my-integrations) 创建 |
| `DATABASE_ID` | 目标数据库 ID | 从 Notion 数据库 URL 复制 |
| `NOTION_TOKEN_V2` | Notion 登录 Cookie | 浏览器 F12 → Application → Cookies → token_v2 |
| `DRIVE_FOLDER_ID` | Google Drive 文件夹 ID | 从 Drive 文件夹 URL 复制 |
| `GOOGLE_CREDENTIALS_JSON` | Google 服务账号凭据 | GCP Console 创建服务账号并下载 JSON |

### 3. 启用 GitHub Actions

进入 `Actions` 标签页，启用 workflows。

### 4. 手动测试

点击 `Run workflow` 手动触发一次，检查日志确认运行正常。

## 📁 项目结构

```
├── notion_image_fixer.py      # 图片永久化脚本
├── notion_to_drive_sync.py    # Notion → Google Drive 同步脚本
├── run_full_recovery.py       # 一键完整修复脚本
├── requirements.txt           # Python 依赖
└── .github/workflows/         # GitHub Actions 工作流
```

## 🔧 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/Notion-sync.git
cd Notion-sync

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的密钥

# 5. 运行
python run_full_recovery.py
```

## ⚠️ 安全提示

- **永远不要**将 `.env` 文件提交到 Git
- 使用 GitHub Secrets 存储敏感信息
- 定期轮换 API 密钥
- `token_v2` 是登录凭据，请妥善保管

## 📝 环境变量说明

创建 `.env` 文件（本地运行时）：

```env
NOTION_TOKEN=secret_xxxxx
DATABASE_ID=your-database-id
NOTION_TOKEN_V2=v02%3Auser_token_data...
DRIVE_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
GOOGLE_APPLICATION_CREDENTIALS=./your-service-account.json
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT
