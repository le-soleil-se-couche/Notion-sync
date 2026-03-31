#!/usr/bin/env python3
"""
Refresh Google OAuth token and optionally update the GOOGLE_TOKEN_JSON GitHub Secret.

Output:
  stdout — the refreshed (or still-valid) token JSON, suitable for piping or
            appending to $GITHUB_ENV inside a workflow step.
  stderr — all progress / error messages.

Auto-update the GitHub Secret by providing both:
  GH_TOKEN          — a Personal Access Token with repo / secrets:write scope
  GITHUB_REPOSITORY — e.g. "owner/repo"  (set automatically by GitHub Actions)

Usage examples
--------------
# Local: just print the refreshed token
GOOGLE_TOKEN_JSON="$(cat token.json)" python refresh_google_token.py

# GitHub Actions step (see workflow for the full heredoc pattern):
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
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


def load_credentials() -> Credentials:
    env_token = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if not env_token:
        _err("ERROR: GOOGLE_TOKEN_JSON is not set or empty.")
        _err("  Run setup_oauth.py locally to generate a token, then add it as a GitHub Secret.")
        sys.exit(1)
    try:
        info = json.loads(env_token)
        return Credentials.from_authorized_user_info(info, DRIVE_SCOPES)
    except Exception as exc:
        _err(f"ERROR: Failed to parse GOOGLE_TOKEN_JSON: {exc}")
        sys.exit(1)


def refresh_credentials(creds: Credentials) -> Credentials:
    if creds.valid:
        _err("Token is still valid — no refresh needed.")
        return creds

    if not creds.refresh_token:
        _err("ERROR: Token has no refresh_token and cannot be refreshed automatically.")
        _err("  Please re-run setup_oauth.py locally and update the GOOGLE_TOKEN_JSON secret.")
        sys.exit(1)

    _err("Refreshing expired Google OAuth token ...")
    try:
        creds.refresh(Request())
        _err("Token refreshed successfully.")
    except Exception as exc:
        _err(f"ERROR: Token refresh failed: {exc}")
        _err("  The refresh token may have been revoked.")
        _err("  Please re-run setup_oauth.py locally and update the GOOGLE_TOKEN_JSON secret.")
        sys.exit(1)

    return creds


def update_github_secret(token_json: str) -> None:
    """Push the refreshed token back to GitHub Secrets via the gh CLI."""
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GH_TOKEN", "").strip()  # Must be a PAT with secrets:write scope

    if not repo or not gh_token:
        # Auto-update not configured — caller handles output
        return

    _err(f"Updating GOOGLE_TOKEN_JSON secret in {repo} ...")
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
        _err("GOOGLE_TOKEN_JSON secret updated successfully.")
    except subprocess.CalledProcessError as exc:
        _err(f"WARNING: Failed to update GitHub secret: {exc.stderr.strip()}")
        _err("  Please update GOOGLE_TOKEN_JSON manually using the token printed to stdout.")
    except FileNotFoundError:
        _err("WARNING: 'gh' CLI not found; cannot update secret automatically.")
        _err("  Please update GOOGLE_TOKEN_JSON manually using the token printed to stdout.")


def main() -> None:
    creds = load_credentials()
    creds = refresh_credentials(creds)
    token_json = creds.to_json()

    update_github_secret(token_json)

    # Always print the (possibly refreshed) token JSON to stdout so the caller
    # can capture it for $GITHUB_ENV or manual copy-paste.
    print(token_json)


if __name__ == "__main__":
    main()
