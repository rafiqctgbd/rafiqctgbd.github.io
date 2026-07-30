#!/usr/bin/env python3
"""
Updates <lastmod> in sitemap.xml for pages whose HTML files changed
in the most recent git diff. Leaves every other entry untouched, and
preserves the existing formatting of sitemap.xml (no reformatting,
no reordering).

Usage:
    python3 scripts/update_sitemap.py <before_sha> <after_sha> [sitemap_path] [site_root]

If <before_sha> is empty or "none", the script exits without making
changes (nothing to diff against, e.g. the very first commit).
"""

import re
import subprocess
import sys
from datetime import datetime, timezone


def get_changed_html_files(before_sha: str, after_sha: str) -> list[str]:
    """Returns paths (relative to repo root) of .html files changed between two commits."""
    if not before_sha or before_sha in ("none", "0000000000000000000000000000000000000000"):
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", before_sha, after_sha, "--", "*.html"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"::warning::git diff failed, skipping sitemap update: {e.stderr.strip()}")
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def file_path_to_url(path: str, site_root: str) -> str:
    """
    Converts a repo-relative file path to the URL convention used in sitemap.xml:
      index.html                 -> https://site/
      folder/index.html          -> https://site/folder/
      folder/page.html           -> https://site/folder/page.html
    """
    site_root = site_root.rstrip("/")
    if path == "index.html":
        return f"{site_root}/"
    if path.endswith("/index.html"):
        folder = path[: -len("index.html")]
        return f"{site_root}/{folder}"
    return f"{site_root}/{path}"


def update_sitemap(sitemap_path: str, changed_urls: set[str]) -> int:
    with open(sitemap_path, "r", encoding="utf-8") as f:
        content = f.read()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    updated_count = 0

    def replace_block(match: re.Match) -> str:
        nonlocal updated_count
        block = match.group(0)
        loc_match = re.search(r"<loc>(.*?)</loc>", block)
        if not loc_match or loc_match.group(1).strip() not in changed_urls:
            return block

        updated_count += 1
        if re.search(r"<lastmod>.*?</lastmod>", block):
            new_block = re.sub(
                r"<lastmod>.*?</lastmod>", f"<lastmod>{today}</lastmod>", block
            )
        else:
            # No existing lastmod tag: insert one right after </loc>
            new_block = re.sub(
                r"(</loc>)", rf"\1\n    <lastmod>{today}</lastmod>", block, count=1
            )
        return new_block

    new_content = re.sub(r"<url>.*?</url>", replace_block, content, flags=re.DOTALL)

    if updated_count:
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return updated_count


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: update_sitemap.py <before_sha> <after_sha> [sitemap_path] [site_root]")
        sys.exit(1)

    before_sha = sys.argv[1]
    after_sha = sys.argv[2]
    sitemap_path = sys.argv[3] if len(sys.argv) > 3 else "sitemap.xml"
    site_root = sys.argv[4] if len(sys.argv) > 4 else "https://mohammadrafiqulislam.com"

    changed_files = get_changed_html_files(before_sha, after_sha)
    if not changed_files:
        print("No changed HTML files detected (or no valid diff range) — nothing to update.")
        return

    changed_urls = {file_path_to_url(p, site_root) for p in changed_files}
    print("Changed HTML files -> sitemap URLs:")
    for path, url in zip(changed_files, [file_path_to_url(p, site_root) for p in changed_files]):
        print(f"  {path} -> {url}")

    updated = update_sitemap(sitemap_path, changed_urls)
    if updated:
        print(f"Updated lastmod for {updated} sitemap entr{'y' if updated == 1 else 'ies'}.")
    else:
        print("Changed files didn't match any sitemap <loc> entries — nothing to update.")


if __name__ == "__main__":
    main()
