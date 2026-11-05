"""ChatGPT route safety: no cursor, no guessed chat, no Codex-as-ChatGPT."""
from __future__ import annotations

import asyncio
import json
import plistlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from dodaios.core.protocols import ExecutionContext
from dodaios.cu import chat_navigation as route
from dodaios.live.tools import LiveTools
from dodaios.plugins.tool import open_app
from dodaios.plugins.tool.open_chatgpt_chat import OpenChatGPTChatTool

FAKE_URL = "https://chatgpt.com/c/11111111-2222-3333-4444-555555555555"


@pytest.mark.parametrize("words,expected", [
    ("Kali, open ChatGPT", True),
    ("please open the ChatGPT app", True),
    ("open Rippling Equity Watch chat", True),
    ("launch the Terminal", True),
    ("go to the Rippling Equity Watch chat", True),
    ("Open Chrome then search for videos", False),
    ("Use the browser to edit my spreadsheet", False),
    ("Send READY to Rippling Equity Watch chat", False),
    ("open Chrome and click its bookmark", False),
    ("close the app", False),
])
def test_nav_intent(words, expected):
    assert route.navigation_only_request(words) is expected


@pytest.mark.parametrize("url,expected", [
    (FAKE_URL, True),
    ("https://chatgpt.com/c/11111111-2222-3333-4444-555555555555?abc=1", False),
    ("https://evil-chatgpt.com/c/11111111-2222-3333-4444-555555555555", False),
    ("https://chatgpt.com.evil.com/c/11111111-2222-3333-4444-555555555555", False),
    ("http://chatgpt.com/c/11111111-2222-3333-4444-555555555555", False),
    ("https://chatgpt.com/share/11111111-2222-3333-4444-555555555555", False),
    ("https://chatgpt.com/", False),
    ("https://chatgpt.com@evil.com/c/11111111-2222-3333-4444-555555555555", False),
])
def test_url_guard(url, expected):
    assert route.valid_conversation_url(url) is expected


def test_chat_lookup_exact_match_never_guesses(tmp_path):
    path = tmp_path / "chatgpt_chat_links.json"
    path.write_text(json.dumps({"Rippling Equity Watch": FAKE_URL}), encoding="utf-8")
    assert route.lookup_chat_link("rippling equity watch", tmp_path) == FAKE_URL
    assert route.lookup_chat_link("Rippling Equity", tmp_path) is None
    assert route.lookup_chat_link("Audit and fix a Jarvis voice control", tmp_path) is None


def test_chat_lookup_rejects_malicious_map(tmp_path):
    path = tmp_path / "chatgpt_chat_links.json"
    path.write_text(json.dumps({"Rippling Equity Watch": "https://evil-chatgpt.com/"}))
    assert route.lookup_chat_link("Rippling Equity Watch", tmp_path) is None


def test_detect_codex_bundle(tmp_path):
    app = tmp_path / "ChatGPT.app"
    info = app / "Contents" / "Info.plist"
    info.parent.mkdir(parents=True)
    info.write_bytes(plistlib.dumps({"CFBundleIdentifier": "com.openai.codex"}))
    assert route.installed_chatgpt_bundle_id(app) == "com.openai.codex"


def test_url_launcher_never_clicks(monkeypatch):
    captured = []
    monkeypatch.setattr(route.sys, "platform", "darwin")
    monkeypatch.setattr(route.subprocess, "run", lambda *args, **kwargs: captured.append((args, kwargs)))
    route.launch_chatgpt_url(FAKE_URL)
    assert captured == [((["open", "-a", "ChatGPT", FAKE_URL],), {
        "shell": False, "check": True, "capture_output": True, "timeout": 10,
    })]
    with pytest.raises(ValueError):
        route.launch_chatgpt_url("https://evil-chatgpt.com/")


def _ctx():
    return ExecutionContext(
        trace_id=uuid4(),
        user_utterance="Open Rippling Equity Watch chat",
        config={}, memory_read=None,
    )


@pytest.mark.asyncio
async def test_unknown_chat_fails_without_mouse(monkeypatch, tmp_path):
    monkeypatch.setattr("dodaios.plugins.tool.open_chatgpt_chat.user_data_dir", lambda: tmp_path)
    def should_never_launch(_url):
        raise AssertionError("No saved URL: must never navigate")
    monkeypatch.setattr("dodaios.plugins.tool.open_chatgpt_chat.launch_chatgpt_url", should_never_launch)
    result = await OpenChatGPTChatTool().execute({"target_chat": "Rippling Equity Watch"}, _ctx())
    assert result.success is False
    assert "No verified direct link" in result.error


@pytest.mark.asyncio
async def test_known_chat_uses_url_not_mouse(monkeypatch, tmp_path):
    (tmp_path / "chatgpt_chat_links.json").write_text(json.dumps({"Rippling Equity Watch": FAKE_URL}))
    monkeypatch.setattr("dodaios.plugins.tool.open_chatgpt_chat.user_data_dir", lambda: tmp_path)
    calls = []
    monkeypatch.setattr("dodaios.plugins.tool.open_chatgpt_chat.launch_chatgpt_url", lambda url: calls.append(url))
    result = await OpenChatGPTChatTool().execute({"target_chat": "Rippling Equity Watch"}, _ctx())
    assert result.success
    assert calls == [FAKE_URL]
    assert "No message" in result.output


@pytest.mark.asyncio
async def test_live_guard_blocks_click_mission_without_gateway():
    tools = LiveTools(gateway=SimpleNamespace(), ledger=SimpleNamespace(), session_id="safe",
                      language="en", backend_model="")
    tools.user_text = "Kali, open ChatGPT"
    result = await tools._execute("computer", {
        "steps": [{"action": "click", "x": 123, "y": 456}],
    }, tools.revision)
    assert result["executed"] is False
    assert result["status"] == "navigation_requires_direct_tool"


@pytest.mark.asyncio
async def test_live_guard_refuses_open_only_send():
    tools = LiveTools(gateway=SimpleNamespace(), ledger=SimpleNamespace(), session_id="safe",
                      language="en", backend_model="")
    tools.user_text = "open Rippling Equity Watch chat"
    result = await tools._execute("chatgpt_task", {
        "target_chat": "Rippling Equity Watch", "prompt": "READY"
    }, tools.revision)
    assert result["status"] == "open_only_not_send"
    assert result["executed"] is False


@pytest.mark.asyncio
async def test_open_chatgpt_app_uses_native_url_not_spotlight(monkeypatch):
    called = []
    monkeypatch.setattr(open_app, "detect_platform", lambda: "darwin")
    monkeypatch.setattr(open_app.subprocess, "run", lambda argv, **kwargs: called.append((argv, kwargs)))
    monkeypatch.setattr(open_app, "_is_plausible_app_name", lambda name: (_ for _ in ()).throw(AssertionError("No lookup needed")))
    result = await open_app.OpenAppTool().execute({"app_name": "ChatGPT"}, _ctx())
    assert result.success
    assert called == [(["open", "-a", "ChatGPT"], {
        "shell": False, "check": True, "capture_output": True, "timeout": 10,
    })]
    assert "Codex" in result.output


@pytest.mark.asyncio
async def test_codex_work_not_regular_chatgpt_task(monkeypatch):
    monkeypatch.setattr(route, "installed_chatgpt_bundle_id", lambda: "com.openai.codex")
    monkeypatch.setattr(route.sys, "platform", "darwin")
    tools = LiveTools(gateway=SimpleNamespace(), ledger=SimpleNamespace(), session_id="safe",
                      language="en", backend_model="")
    tools.user_text = "Send READY to the ChatGPT chat named Jarvis Test"
    result = await tools._execute("chatgpt_task", {
        "target_chat": "Audit and fix a Jarvis voice control", "prompt": "READY",
    }, tools.revision)
    assert result["executed"] is False
    assert result["status"] == "codex_not_regular_chatgpt"
