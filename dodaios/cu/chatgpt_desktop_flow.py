"""A bounded ChatGPT prompt transaction: verify, type once, send once, read."""
from __future__ import annotations
import asyncio
import json
from typing import Any

_FLOW_LOCK = asyncio.Lock()


class DesktopFlowError(RuntimeError):
    pass


async def run_prompt_flow(*, prompt: str, target: str, observe: Any,
                          type_once: Any, submit_once: Any, identity: Any,
                          timeout_s: float = 300) -> str:
    """Never retry a mutating action, including after an uncertain result.

    Callbacks keep the normal desktop tool permission and target checks. The
    observer must return verified evidence, not a model's unverified plan.
    """
    if not prompt.strip() or len(prompt) > 12000:
        raise DesktopFlowError('The prompt must contain 1–12000 characters.')
    if not target.strip():
        raise DesktopFlowError('An explicit target chat is required.')
    async with _FLOW_LOCK:
        async with asyncio.timeout(timeout_s):
            ready = await observe(
                f'In the ChatGPT app, target existing chat {json.dumps(target)}. '
                'Click inside its empty message composer at the bottom. An active assistant may accept a queued follow-up; do not stop it. Do not type or submit yet. '
                'If any draft exists, fail without altering it. If temporarily unavailable, wait. Finish with verified evidence '
                'that the named chat is active and its empty composer is focused.'
            )
            if not ready:
                raise DesktopFlowError('The target chat and empty composer were not verified.')
            expected = await identity()
            # Deliberately no retry around typing: an error may follow a partial write.
            await type_once(prompt, expected)
            draft = await observe(
                f'Read-only: in ChatGPT chat {json.dumps(target)}, verify the composer '
                f'contains EXACTLY this full draft: {json.dumps(prompt)}. '
                'Do not click, type, submit or change anything. Fail if it differs. '
                'Finish only with on-screen evidence that the entire draft matches.'
            )
            if not draft:
                raise DesktopFlowError('The draft was not verified; it has NOT been submitted.')
            if await identity() != expected:
                raise DesktopFlowError('The target window changed; the draft was not submitted.')
            # Exactly one submission attempt. Uncertainty never authorizes another Enter.
            await submit_once(expected)
            reply = await observe(
                f'Read-only: in ChatGPT chat {json.dumps(target)}, wait for the assistant '
                f'reply to the newly submitted user prompt {json.dumps(prompt)}. '
                'Do not type, press Enter, navigate away, or send another message. '
                'You may scroll within this chat to read the answer. '
                'If queued or still generating, wait. When complete, return the actual '
                'new assistant answer in your verified completion reason. '
                'Do not quote an older answer or this instruction. Fail if no answer arrives.'
            )
            if not reply:
                raise DesktopFlowError('The prompt was submitted once, but no completed reply was verified.')
            return reply


async def dispatch_prompt_flow(dispatch: Any, ctx: Any, *, prompt: str, target: str,
                               timeout_s: float, language: str) -> Any:
    from dodaios.core.protocols import ToolResult
    from dodaios.cu.target_guard import read_foreground_target
    from dodaios.plugins.tool.type_text import TypeTextTool
    from dodaios.plugins.tool.hotkey import HotkeyTool
    from dodaios.harness.computer_use_context import get_computer_use_context
    from dodaios.brain.local_action_gate import HARNESS_NAME
    from dodaios.voice.action_phrases import OUTPUT_LANGUAGE_ENV_KEY

    async def observe(goal: str) -> str:
        result = await dispatch.execute({'harness': HARNESS_NAME, 'prompt': goal,
            'timeout_s': min(120, timeout_s), 'env': {OUTPUT_LANGUAGE_ENV_KEY: language}},ctx)
        output = result.output if isinstance(result.output,dict) else {}
        stdout = str(output.get('stdout') or '')
        if not result.success or '[cu] done (verified:' not in stdout:
            raise DesktopFlowError('Desktop observation failed: '+str(result.error or output.get('stderr') or stdout)[-700:])
        return stdout

    async def identity() -> tuple[Any,...]:
        from dodaios.harness.computer_use_context import cu_recently_cancelled
        if cu_recently_cancelled():
            raise DesktopFlowError('Voice hangup cancelled the desktop transaction.')
        current = await asyncio.to_thread(read_foreground_target)
        title = str(getattr(current.window,'title','') or '')
        import sys
        if sys.platform == 'darwin':
            from AppKit import NSRunningApplication
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(current.window.pid)
            if app is None or str(app.bundleIdentifier()) not in {'com.openai.codex', 'com.openai.chat'}:
                raise DesktopFlowError('The foreground app is not the authorized ChatGPT/Codex app.')
            if target.casefold() not in title.casefold():
                from dodaios.cu.named_chat import macos_named_chat_selected
                if not await asyncio.to_thread(macos_named_chat_selected, current.window.pid, target):
                    raise DesktopFlowError('The named chat is not verifiably selected; no message was sent.')
        elif target.casefold() not in title.casefold():
            raise DesktopFlowError('The foreground title does not match the requested chat.')
        return current.signature

    async def type_once(text: str, expected: Any) -> None:
        result = await get_computer_use_context().tool_executor.execute(
            TypeTextTool(), {'text': text, '_expected_window_signature': expected},
            user_utterance=ctx.user_utterance, config_snapshot=ctx.config,
            memory_read=ctx.memory_read, trace_id=ctx.trace_id,
        )
        if not result.success:
            raise DesktopFlowError('Typing did not complete; not retrying: '+str(result.error))

    async def submit_once(expected: Any) -> None:
        result = await get_computer_use_context().tool_executor.execute(
            HotkeyTool(), {'keys': ['enter'], '_expected_window_signature': expected},
            user_utterance=ctx.user_utterance, config_snapshot=ctx.config,
            memory_read=ctx.memory_read, trace_id=ctx.trace_id,
        )
        if not result.success:
            raise DesktopFlowError('Submission uncertain; not retrying: '+str(result.error))

    try:
        reply=await run_prompt_flow(prompt=prompt,target=target,observe=observe,
            type_once=type_once,submit_once=submit_once,identity=identity,timeout_s=timeout_s)
        return ToolResult(success=True,output={'stdout':reply,'exit_code':0})
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return ToolResult(success=False,output={'stderr':str(exc),'exit_code':1},error=str(exc))
