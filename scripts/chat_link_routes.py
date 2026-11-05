#!/usr/bin/env python3
"""Save or list exact ChatGPT chat-title links privately for mouse-free opening.

Usage:
  python scripts/chat_link_routes.py set "Rippling Equity Watch" "https://chatgpt.com/c/..."
  python scripts/chat_link_routes.py list

This does not access your chat content or automate the browser.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

# Direct script use from the repository checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dodaios.core.paths import user_data_dir
from dodaios.cu.chat_navigation import valid_conversation_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    put = sub.add_parser("set")
    put.add_argument("title")
    put.add_argument("url")
    sub.add_parser("list")
    args = parser.parse_args()
    data_dir = user_data_dir()
    path = data_dir / "chatgpt_chat_links.json"
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        raise SystemExit("Refusing to replace malformed private chat-link map.")
    if args.operation == "list":
        for title in sorted(saved):
            print(title)
        return 0
    if not 1 <= len(args.title.strip()) <= 200:
        parser.error("Title length must be 1–200 characters.")
    if not valid_conversation_url(args.url):
        parser.error("Use an exact https://chatgpt.com/c/... conversation URL.")
    data_dir.mkdir(parents=True, exist_ok=True)
    saved[args.title.strip()] = args.url.strip()
    tmp = path.with_suffix(".json.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(saved, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(tmp, path)
    print(f"Saved direct ChatGPT chat link for {args.title!r} (private, no mouse).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
