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

### 2. 配置 GitHub Secrets (关键步骤)

进入你 Fork 后的仓库：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`。

**你需要添加以下 5 个密钥：**

#### 1️⃣ `NOTION_TOKEN` (Notion 机器人密钥)
1. 访问 [Notion My Integrations](https://www.notion.so/my-integrations)
2. 点击 "+ New integration"
3. 命名 (如 "Notion Backup")，Capabilities 保持默认，点击 Submit
4. 点击 "Show" 复制 `Internal Integration Secret`
5. **重要**：在你的 Notion 数据库页面，点击右上角 `...` → `Connect to` → 选择你刚才创建的机器人

#### 2️⃣ `DATABASE_ID` (数据库 ID)
1. 在浏览器打开你的 Notion 数据库页面
2. URL 格式通常为：`https://www.notion.so/myworkspace/a8aec43384f447ed84390e8e42c2e089?v=...`
3. 复制 `myworkspace/` 之后、`?` 之前的那串字符 (即 `a8aec43384f447ed84390e8e42c2e089`)

#### 3️⃣ `NOTION_TOKEN_V2` (用户登录 Cookie)
*用于下载由于防盗链无法直接下载的图片（如微信、小红书）。*
1. 在浏览器登录 Notion 网页版
2. 按 `F12` 打开开发者工具，切换到 `Application` (或 Storage) 标签页
3. 在左侧展开 `Cookies` → `https://www.notion.so`
4. 找到名为 `token_v2` 的条目，复制它的 Value (通常以 `v02%...` 开头)

#### 4️⃣ `DRIVE_FOLDER_ID` (Google Drive 文件夹 ID)
1. 打开 Google Drive，进入你想保存文件的文件夹
2. 查看地址栏 URL 格式：`https://drive.google.com/drive/u/0/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ`
3. 复制 `folders/` 后面的那串字符 (即 `1aBcDeFgHiJkLmNoPqRsTuVwXyZ`)

#### 5️⃣ `GOOGLE_CREDENTIALS_JSON` (Google 服务账号凭据)
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建一个新项目 (或使用现有项目)
3. 搜索并启用 **"Google Drive API"**
4. 【方法一】点击左侧菜单栏的 **"凭证" (Credentials)** (钥匙图标) → 点击顶部 **"+ 创建凭证"** → 选择 **"服务账号"**
   *或者*：【方法二】点击左上角汉堡菜单 (≡) → "IAM 和管理" → "服务账号" → "创建服务账号"
5. 填写名称，创建后，点击该账号进入详情页
6. 点击 `Keys` 标签页 → `Add Key` → `Create new key` → 选择 **JSON** → 下载文件
7. **用记事本打开下载的 JSON 文件，复制里面的全部内容** (从 `{` 开始到 `}` 结束)
8. **重要**：复制服务账号的邮箱 (例如 `notion-backup@project-id.iam.gserviceaccount.com`)，进入你的 Google Drive 文件夹，点击“共享”，将此邮箱添加为编辑者

---

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

## 🔧 本地运行 (可选)

如果你想在本地电脑运行：

1. 克隆仓库并安装依赖 (`pip install -r requirements.txt`)
2. 复制 `.env.example` 为 `.env`
3. 填入上述 5 个变量 (其中 `GOOGLE_APPLICATION_CREDENTIALS` 填 JSON 文件的**相对路径**)
4. 运行 `python run_full_recovery.py`

## ⚠️ 安全提示

- **永远不要**将 `.env` 文件或 `*.json` 密钥文件提交到 Git
- 定期轮换你的 API 密钥
- `token_v2` 代表你的用户权限，请绝对保密

## 📄 License

MIT
