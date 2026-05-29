#!/usr/bin/env python3
"""Fetch latest posts from blog RSS and rewrite the BLOG-POSTS section of README.md."""
from __future__ import annotations

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://blog.pachoalto.xyz/rss.xml"
README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- BLOG-POSTS:START -->"
END = "<!-- BLOG-POSTS:END -->"
MAX_POSTS = 10


def classify(title: str, link: str) -> str:
    blob = f"{title} {link}".lower()
    if "htb" in blob or "hack the box" in blob or "/htb/" in blob:
        return "HTB"
    return "Posts"


def fetch_items(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "z3moo-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
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
    return items[:MAX_POSTS]


def render(items: list[dict]) -> str:
    lines = [
        "| # | Name | Type | Date |",
        "|---|------|------|------|",
    ]
    for i, it in enumerate(items, 1):
        name = it["title"].replace("|", "\\|")
        kind = classify(it["title"], it["link"])
        date = it["date"].strftime("%Y-%m-%d")
        lines.append(f"| {i} | [{name}]({it['link']}) | {kind} | {date} |")
    return "\n".join(lines)


def splice(readme: str, table: str) -> str:
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END), flags=re.DOTALL
    )
    block = f"{START}\n{table}\n{END}"
    if pattern.search(readme):
        return pattern.sub(block, readme)
    sep = "" if readme.endswith("\n") else "\n"
    return f"{readme}{sep}\n## Latest Blog Posts\n\n{block}\n"


def main() -> int:
    items = fetch_items(FEED_URL)
    if not items:
        print("No items in feed", file=sys.stderr)
        return 1
    table = render(items)
    original = README.read_text(encoding="utf-8")
    updated = splice(original, table)
    if original == updated:
        print("README already up to date.")
        return 0
    README.write_text(updated, encoding="utf-8")
    print(f"Updated README with {len(items)} posts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
