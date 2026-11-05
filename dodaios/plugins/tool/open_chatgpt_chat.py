"""Open a saved exact ChatGPT chat link without visual cursor automation."""
from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from dodaios.core.paths import user_data_dir
from dodaios.core.protocols import ExecutionContext, ToolResult
from dodaios.cu.chat_navigation import launch_chatgpt_url, lookup_chat_link


class OpenChatGPTChatTool:
    name = "open_chatgpt_chat"
    risk_tier = "monitor"
    description = (
        "Open an exact named regular ChatGPT conversation with a previously saved "
        "verified chatgpt.com/c/... link. No cursor, bookmarks, sidebar search, "
        "typing, or sending. If no link is saved, fail and ask for the URL once. "
        "Codex/Work chats are not regular ChatGPT conversations."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "target_chat": {"type": "string", "minLength": 1, "maxLength": 200},
        },
        "required": ["target_chat"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ExecutionContext) -> ToolResult:
        title = str(args.get("target_chat") or "").strip()
        url = await asyncio.to_thread(lookup_chat_link, title, user_data_dir())
        if not url:
            return ToolResult(
                success=False, output=None,
                error=(
                    f"No verified direct link is saved for chat {title!r}. "
                    "Open that regular ChatGPT chat manually once and copy its "
                    "https://chatgpt.com/c/... URL into the private Jarvis chat-link "
                    "map. Do not click bookmarks/sidebar entries or substitute "
                    "a Codex/Work chat. No navigation or message was performed."
                ),
            )
        try:
            await asyncio.to_thread(launch_chatgpt_url, url)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:  # Return a visible refused-navigation receipt.
            return ToolResult(
                success=False, output=None,
                error=f"Native browser navigation failed: {exc}. No mouse action was attempted.",
            )
        return ToolResult(
            success=True,
            output=(
                f"Requested {title!r} via its verified saved ChatGPT conversation URL. "
                "The browser accepted navigation; the displayed chat has not been "
                "visually confirmed. No message was typed or sent."
            ),
        )
