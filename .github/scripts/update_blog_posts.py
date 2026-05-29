#!/usr/bin/env python3
"""Fetch latest entries from blog + HTB feeds and rewrite README.md tables."""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

POSTS_FEED = "https://blog.pachoalto.xyz/rss.xml"
HTB_FEED = "https://blog.pachoalto.xyz/htb/rss.xml"
README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- BLOG-POSTS:START -->"
END = "<!-- BLOG-POSTS:END -->"
MAX_ITEMS = 5


def fetch_items(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "z3moo-readme-bot"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        print(f"WARN: {url} returned {exc.code}", file=sys.stderr)
        return []
    if "xml" not in ctype:
        print(f"WARN: {url} returned non-XML ({ctype})", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        print(f"WARN: failed to parse {url}: {exc}", file=sys.stderr)
        return []
    items = []
    for it in root.iterfind(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        try:
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError, ValueError):
            dt = datetime.now(timezone.utc)
        items.append({"title": title, "link": link, "date": dt})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:MAX_ITEMS]


def render_table(items: list[dict], heading: str, kind: str, empty_msg: str) -> str:
    if not items:
        return f"#### {heading}\n\n_{empty_msg}_"
    rows = ["| # | Name | Type | Date |", "|---|------|------|------|"]
    for i, it in enumerate(items, 1):
        name = it["title"].replace("|", "\\|")
        date = it["date"].strftime("%Y-%m-%d")
        rows.append(f"| {i} | [{name}]({it['link']}) | {kind} | {date} |")
    return f"#### {heading}\n\n" + "\n".join(rows)


def render_block(posts: list[dict], htb: list[dict]) -> str:
    posts_md = render_table(posts, "Latest Posts", "Posts", "No posts found.")
    htb_md = render_table(htb, "Latest HTB", "HTB", "HTB feed not yet deployed.")
    return (
        "<table>\n<tr>\n<td valign=\"top\" width=\"50%\">\n\n"
        f"{posts_md}\n\n"
        "</td>\n<td valign=\"top\" width=\"50%\">\n\n"
        f"{htb_md}\n\n"
        "</td>\n</tr>\n</table>"
    )


def splice(readme: str, block: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.DOTALL)
    wrapped = f"{START}\n{block}\n{END}"
    if pattern.search(readme):
        return pattern.sub(wrapped, readme)
    sep = "" if readme.endswith("\n") else "\n"
    return f"{readme}{sep}\n## Latest Activity\n\n{wrapped}\n"


def main() -> int:
    posts = fetch_items(POSTS_FEED)
    htb = fetch_items(HTB_FEED)
    if not posts and not htb:
        print("Both feeds returned no items; aborting.", file=sys.stderr)
        return 1
    block = render_block(posts, htb)
    original = README.read_text(encoding="utf-8")
    updated = splice(original, block)
    if original == updated:
        print("README already up to date.")
        return 0
    README.write_text(updated, encoding="utf-8")
    print(f"Updated README ({len(posts)} posts, {len(htb)} HTB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
