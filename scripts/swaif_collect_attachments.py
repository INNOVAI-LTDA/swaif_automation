#!/usr/bin/env python3
"""Download GitHub Issue attachments referenced in issue body/comments.

What it does
------------
- Fetches issue body + comments via GitHub REST API.
- Extracts URLs that look like GitHub-hosted attachments:
  - https://user-images.githubusercontent.com/...
  - https://github.com/user-attachments/...
  - https://github.com/<org>/<repo>/assets/<id>/...
  - Any markdown link that ends with a common binary extension (.png/.jpg/.pdf/.zip/.csv/.xlsx/.pptx/.docx/.json/.log)
- Downloads them into: specs/<feature_slug>/attachments/
- Writes a manifest: specs/<feature_slug>/attachments/manifest.json

Notes / Caveats
---------------
- GitHub does NOT expose a clean “attachments API” for issues. Attachments appear as URLs in markdown. We parse and download URLs.
  Some private-repo attachments may still require auth and/or may not be downloadable from runners depending on GitHub's rules.
- Use a token with `repo` scope (PAT) or workflow `GITHUB_TOKEN` with proper permissions for private repos.

Usage
-----
python scripts/swaif_collect_attachments.py \
  --repo "$GITHUB_REPOSITORY" \
  --issue 123 \
  --token "$PROJECTS_TOKEN" \
  --out "specs/001-hub-branding/attachments"

Exit codes
----------
0: OK (even if zero files found)
2: CLI usage error
3: API error
4: Download error (one or more downloads failed)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import urllib.request
import urllib.error

BIN_EXT = (
    ".png",".jpg",".jpeg",".webp",".gif",
    ".pdf",".zip",".csv",".tsv",
    ".xlsx",".xls",".docx",".pptx",
    ".json",".log",".txt"
)

URL_RE = re.compile(r"https?://[^\s)>'\"]+", re.IGNORECASE)

# Common GitHub attachment hosts/paths
ATTACHMENT_HINTS = (
    "user-images.githubusercontent.com/",
    "github.com/user-attachments/",
    "/assets/",
)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def looks_like_attachment(url: str) -> bool:
    u = url.lower()
    if any(h in u for h in ATTACHMENT_HINTS):
        return True
    return u.endswith(BIN_EXT)

def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    urls = URL_RE.findall(text)
    # Trim trailing punctuation that often sticks to URLs in markdown
    cleaned = []
    for u in urls:
        u2 = u.rstrip(".,;:]})>")
        cleaned.append(u2)
    # Keep stable order, de-dup
    seen = set()
    out = []
    for u in cleaned:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def gh_api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "swaif-issueops-attachments",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"GitHub API error {e.code}: {body}") from e

def gh_api_list_comments(repo: str, issue: int, token: str) -> List[dict]:
    # GitHub paginates; we loop pages
    per_page = 100
    page = 1
    all_items = []
    while True:
        url = f"https://api.github.com/repos/{repo}/issues/{issue}/comments?per_page={per_page}&page={page}"
        items = gh_api_get(url, token)
        if not isinstance(items, list):
            raise RuntimeError("Unexpected response for comments list")
        all_items.extend(items)
        if len(items) < per_page:
            break
        page += 1
        if page > 50:
            break
    return all_items

def http_download(url: str, token: Optional[str]) -> Tuple[bytes, str]:
    headers = {"User-Agent": "swaif-issueops-attachments"}
    # Some attachments might require auth; try with token if provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type","")
            return data, ctype
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Download HTTPError {e.code} for {url}: {body[:200]}") from e

def infer_filename(url: str, content_type: str, fallback_idx: int) -> str:
    # Try last path segment
    name = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    if not name or len(name) < 3:
        name = f"attachment-{fallback_idx}"
    # If no extension, guess from content-type
    if "." not in name:
        ct = content_type.lower()
        if "pdf" in ct:
            name += ".pdf"
        elif "png" in ct:
            name += ".png"
        elif "jpeg" in ct or "jpg" in ct:
            name += ".jpg"
        elif "zip" in ct:
            name += ".zip"
        else:
            name += ".bin"
    return name

def safe_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--issue", required=True, type=int, help="issue number")
    ap.add_argument("--token", required=True, help="GitHub token (PAT or GITHUB_TOKEN)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--include-body", action="store_true", help="also parse issue body (default true)")
    ap.add_argument("--no-auth-download", action="store_true", help="do not send Authorization header on downloads")
    args = ap.parse_args()

    repo = args.repo
    issue = args.issue
    token = args.token
    out_dir = Path(args.out)

    # Fetch issue
    try:
        issue_data = gh_api_get(f"https://api.github.com/repos/{repo}/issues/{issue}", token)
    except Exception as e:
        print(f"[ERR] fetching issue: {e}", file=sys.stderr)
        return 3

    texts = []
    body = issue_data.get("body") or ""
    if body:
        texts.append(("issue_body", body))

    # Fetch comments
    try:
        comments = gh_api_list_comments(repo, issue, token)
    except Exception as e:
        print(f"[ERR] fetching comments: {e}", file=sys.stderr)
        return 3

    for c in comments:
        txt = c.get("body") or ""
        if txt:
            texts.append((f"comment_{c.get('id')}", txt))

    # Extract and filter urls
    all_urls = []
    for origin, txt in texts:
        for u in extract_urls(txt):
            if looks_like_attachment(u):
                all_urls.append((origin, u))

    # De-dup URLs
    seen = set()
    filtered = []
    for origin, u in all_urls:
        if u not in seen:
            seen.add(u)
            filtered.append((origin, u))

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "repo": repo,
        "issue": issue,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": 0,
        "items": [],
        "errors": [],
    }

    dl_token = None if args.no_auth_download else token
    had_error = False

    for idx, (origin, url) in enumerate(filtered, start=1):
        try:
            data, ctype = http_download(url, dl_token)
            filename = infer_filename(url, ctype, idx)
            digest = sha256_bytes(data)
            # Avoid collisions: prefix hash if filename already exists
            target = out_dir / filename
            if target.exists():
                target = out_dir / f"{digest[:10]}-{filename}"
            safe_write(target, data)
            manifest["items"].append({
                "origin": origin,
                "url": url,
                "filename": target.name,
                "bytes": len(data),
                "sha256": digest,
                "content_type": ctype,
            })
            manifest["count"] += 1
            print(f"[OK] {url} -> {target}")
        except Exception as e:
            had_error = True
            manifest["errors"].append({"origin": origin, "url": url, "error": str(e)})
            print(f"[ERR] {url}: {e}", file=sys.stderr)

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] wrote manifest: {out_dir/'manifest.json'}")

    return 4 if had_error else 0

if __name__ == "__main__":
    raise SystemExit(main())
