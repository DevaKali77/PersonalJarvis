"""A named ChatGPT prompt/reply transaction owned by a tracked voice task."""
from __future__ import annotations

from typing import Any

from dodaios.core.protocols import ExecutionContext, ToolResult


class ChatGPTTaskTool:
    name = "chatgpt_task"
    risk_tier = "ask"
    description = (
        "Send the exact approved prompt to a named existing ChatGPT/Codex desktop chat, "
        "wait for its completed response, and return the verified answer. Supply the exact "
        "chat title and prompt. Never infer a target chat. This is one tracked task: a pending "
        "receipt means still working, not delivered or complete. Use task_status to follow it; "
        "never repeat an uncertain submission. Existing drafts are preserved."
    )
    schema = {
        "type": "object",
        "properties": {
            "target_chat": {"type": "string", "minLength": 1},
            "prompt": {"type": "string", "minLength": 1, "maxLength": 12000},
        },
        "required": ["target_chat", "prompt"],
        "additionalProperties": False,
    }

    def __init__(self, dispatch: Any) -> None:
        self._dispatch = dispatch

    async def execute(self, args: dict[str, Any], ctx: ExecutionContext) -> ToolResult:
        target = str(args.get("target_chat") or "").strip()
        prompt = str(args.get("prompt") or "")
        if not target or not prompt.strip() or len(prompt) > 12000:
            return ToolResult(False, None, error="An exact existing chat title and 1–12000 character prompt are required.")
        from dodaios.cu.chatgpt_desktop_flow import dispatch_prompt_flow

        # The supervisor owns ask-tier approval; the transaction's mutations
        # each retain ToolExecutor, foreground checks and exactly-once rules.
        return await dispatch_prompt_flow(
            self._dispatch, ctx, prompt=prompt, target=target, timeout_s=300,
            language=str(ctx.config.get("output_language") or "en"),
        )
