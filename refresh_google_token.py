#!/usr/bin/env python3
"""
刷新 Google OAuth Token，并在可选情况下把最新值写回 GitHub Secret：GOOGLE_TOKEN_JSON。

输出说明：
  stdout —— 输出刷新后的（或当前仍有效的）token JSON，可直接写入
            GitHub Actions 的 $GITHUB_ENV，或供你手动复制更新。
  stderr —— 输出执行过程中的提示、警告和错误信息。

若同时提供以下环境变量，则会自动回写 GitHub Secret：
  GH_TOKEN          —— GitHub Personal Access Token（需具备 repo 权限）
  GITHUB_REPOSITORY —— 例如 "owner/repo"（GitHub Actions 中会自动提供）

使用示例
--------
# 本地执行：仅输出刷新后的 token
GOOGLE_TOKEN_JSON="$(cat token.json)" python refresh_google_token.py

# GitHub Actions 中调用（完整写法见 workflow）：
#   env:
#     GOOGLE_TOKEN_JSON: ${{ secrets.GOOGLE_TOKEN_JSON }}
#     GH_TOKEN: ${{ secrets.GH_PAT }}
#     GITHUB_REPOSITORY: ${{ github.repository }}
#   run: python refresh_google_token.py
"""

import json
import os
import subprocess
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _err(*args, **kwargs):
    """输出到 stderr。"""
    print(*args, file=sys.stderr, **kwargs)


def load_credentials() -> Credentials:
    env_token = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if not env_token:
        _err("错误：未设置 GOOGLE_TOKEN_JSON，或其内容为空。")
        _err("  请先在本地运行 setup_oauth.py 生成 token，再把它更新到 GitHub Secret。")
        sys.exit(1)
    try:
        info = json.loads(env_token)
        return Credentials.from_authorized_user_info(info, DRIVE_SCOPES)
    except Exception as exc:
        _err(f"错误：解析 GOOGLE_TOKEN_JSON 失败：{exc}")
        sys.exit(1)


def refresh_credentials(creds: Credentials) -> Credentials:
    if creds.valid:
        _err("当前 token 仍然有效，无需刷新。")
        return creds

    if not creds.refresh_token:
        _err("错误：当前 token 不包含 refresh_token，无法自动刷新。")
        _err("  请在本地重新运行 setup_oauth.py，并手动更新 GOOGLE_TOKEN_JSON Secret。")
        sys.exit(1)

    _err("正在刷新已过期的 Google OAuth token ...")
    try:
        creds.refresh(Request())
        _err("Token 刷新成功。")
    except Exception as exc:
        _err(f"错误：Token 刷新失败：{exc}")
        _err("  refresh token 可能已经失效或被撤销。")
        _err("  请在本地重新运行 setup_oauth.py，并手动更新 GOOGLE_TOKEN_JSON Secret。")
        sys.exit(1)

    return creds


def update_github_secret(token_json: str) -> None:
    """通过 gh CLI 将刷新后的 token 回写到 GitHub Secret。"""
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GH_TOKEN", "").strip()  # 必须是具有 repo 权限的 PAT

    if not repo or not gh_token:
        # 未配置自动回写参数，由调用方自行处理 stdout 输出
        return

    _err(f"正在更新 {repo} 中的 GOOGLE_TOKEN_JSON Secret ...")
    env = {**os.environ, "GH_TOKEN": gh_token}
    try:
        subprocess.run(
            ["gh", "secret", "set", "GOOGLE_TOKEN_JSON", "--repo", repo],
            input=token_json,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        _err("GOOGLE_TOKEN_JSON Secret 更新成功。")
    except subprocess.CalledProcessError as exc:
        _err(f"警告：更新 GitHub Secret 失败：{exc.stderr.strip()}")
        _err("  请使用 stdout 输出的 token 内容，手动更新 GOOGLE_TOKEN_JSON。")
    except FileNotFoundError:
        _err("警告：未找到 gh CLI，无法自动更新 Secret。")
        _err("  请使用 stdout 输出的 token 内容，手动更新 GOOGLE_TOKEN_JSON。")


def main() -> None:
    creds = load_credentials()
    creds = refresh_credentials(creds)
    token_json = creds.to_json()

    update_github_secret(token_json)

    # 始终将当前最新 token JSON 输出到 stdout，方便调用方写入
    # $GITHUB_ENV，或手动复制后更新到 GitHub Secret。
    print(token_json)


if __name__ == "__main__":
    main()
