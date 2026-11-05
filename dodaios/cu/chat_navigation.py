"""Deterministic ChatGPT navigation that never acquires the mouse.

A chat title is not a chat ID. Only a previously verified user-supplied
chatgpt.com conversation link permits opening a named chat. Codex/Work is
a separate application and cannot stand in for regular ChatGPT chats.
"""
from __future__ import annotations

import json
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

CHATGPT_HOME = "https://chatgpt.com/"
_OPEN_VERBS = ("open", "launch", "start", "bring up", "go to", "switch to", "show me", "take me to")
_CHATTY = ("chatgpt", "chat gpt")
_CHAT_PATH = re.compile(r"^/(?:g/[^/]+/)?c/[a-zA-Z0-9-]{20,}$")


def navigation_only_request(text: str) -> bool:
    """High-precision guard for requests that require navigation, not clicking.

    Never block actual computer tasks (editing, browser forms, research).
    ChatGPT navigation remains mouse-free even if extra work is requested.
    """
    spoken = re.sub(r"\s+", " ", str(text or "").casefold()).strip(" .!?,")
    spoken = re.sub(r"^(?:hey\s+)?(?:kali|jarvis)[, ]+", "", spoken)
    spoken = re.sub(r"^please\s+", "", spoken)
    spoken = re.sub(r"^(?:can|could|would) you (?:please )?", "", spoken)
    spoken = re.sub(r"^(?:i want you to|i need you to) ", "", spoken)
    navigates = any(spoken.startswith(v + " ") for v in _OPEN_VERBS)
    if not navigates:
        return False
    if any(name in spoken for name in _CHATTY):
        return True
    if any(term in spoken for term in (" chat", " conversation")):
        return True
    # Simple app launch only; multistep computer tasks retain screen control.
    if len(spoken) > 92 or any(
        re.search(r"\b" + w + r"\b", spoken)
        for w in ("then", "and", "click", "type", "send", "search", "edit",
                  "write", "message", "reply", "fix", "after", "before")
    ):
        return False
    return bool(re.fullmatch(
        r"(?:open|launch|start|bring up|go to|switch to|show me|take me to) "
        r"(?:the |my )?[a-z0-9._ -]+(?: app| application| window)?",
        spoken,
    ))


def valid_conversation_url(url: str) -> bool:
    """An editable regular-chat deep link, not a share/search/ad URL."""
    try:
        parsed = urlsplit(url.strip())
    except ValueError:  # Reject malformed destination URLs; never try navigation.
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == "chatgpt.com"
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and bool(_CHAT_PATH.fullmatch(parsed.path))
    )


def lookup_chat_link(title: str, data_dir: Path) -> str | None:
    """Exact, case-insensitive title match in a private user-owned JSON file."""
    if not 1 <= len(title.strip()) <= 200:
        return None
    path = data_dir / "chatgpt_chat_links.json"
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # Missing or invalid private map means no chat link.
        return None
    if not isinstance(mapping, dict):
        return None
    names = {str(k).strip().casefold(): v for k, v in mapping.items()}
    value = names.get(title.strip().casefold())
    return value if isinstance(value, str) and valid_conversation_url(value) else None


def installed_chatgpt_bundle_id(
    app: Path = Path("/Applications/ChatGPT.app")
) -> str | None:
    try:
        with (app / "Contents/Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, ValueError, TypeError):  # An unreadable app bundle is untrusted.
        return None
    return str(info.get("CFBundleIdentifier") or "") or None


def launch_chatgpt_url(url: str) -> None:
    """Open via OS app services; never move cursor or click screen coordinates."""
    if not (url == CHATGPT_HOME or valid_conversation_url(url)):
        raise ValueError("Untrusted ChatGPT destination; refusing to navigate.")
    if sys.platform == "darwin":
        # Native ChatGPT desktop app (Chat / Work / Codex), not Chrome. A
        # conversation link is supplied only when the owner verified it.
        # macOS's app bundle registers http/https URL schemes.
        argv = ["open", "-a", "ChatGPT"] + ([] if url == CHATGPT_HOME else [url])
    elif sys.platform == "win32":
        # os.startfile would obscure launch failures; direct URL handling
        # goes through the Windows shell verb without shell=True.
        argv = ["cmd", "/c", "start", "", url]
    else:
        argv = ["xdg-open", url]
    subprocess.run(argv, shell=False, check=True, capture_output=True, timeout=10)
