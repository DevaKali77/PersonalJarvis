import asyncio
from uuid import uuid4

from dodaios.core.bus import EventBus
from dodaios.core.config import SafetyConfig
from dodaios.core.protocols import ExecutionContext, ToolResult
from dodaios.plugins.tool.chatgpt_task import ChatGPTTaskTool
from dodaios.safety.approval import ApprovalWorkflow
from dodaios.safety.risk_tier import RiskTierEvaluator
from dodaios.safety.tool_executor import ToolExecutor, VOICE_CONFIRM_SENTINEL


def context():
    return ExecutionContext(trace_id=uuid4(), user_utterance="Send a test to Jarvis Test", config={}, memory_read=None)


async def test_missing_target_cannot_send(monkeypatch):
    async def unexpected(*_args, **_kwargs):
        raise AssertionError("No message may be sent without its named target")
    monkeypatch.setattr("dodaios.cu.chatgpt_desktop_flow.dispatch_prompt_flow", unexpected)
    result = await ChatGPTTaskTool(None).execute({"prompt": "hello"}, context())
    assert not result.success


async def test_task_waits_for_reply_and_preserves_exact_prompt(monkeypatch):
    gate = asyncio.Event()
    received = []
    async def transaction(dispatch, ctx, **kwargs):
        received.append(kwargs)
        await gate.wait()
        return ToolResult(True, {"stdout": "READY", "verified": True})
    monkeypatch.setattr("dodaios.cu.chatgpt_desktop_flow.dispatch_prompt_flow", transaction)
    task = asyncio.create_task(ChatGPTTaskTool(None).execute(
        {"prompt": "Reply with READY\nDo not edit anything.", "target_chat": "Jarvis Test"}, context()))
    await asyncio.sleep(0)
    assert not task.done()
    assert received[0]["prompt"] == "Reply with READY\nDo not edit anything."
    assert received[0]["target"] == "Jarvis Test"
    gate.set()
    assert (await task).success


async def test_voice_submission_waits_for_real_user_approval(monkeypatch):
    called = []
    async def transaction(*_args, **_kwargs):
        called.append(True)
        return ToolResult(True, "sent")
    monkeypatch.setattr("dodaios.cu.chatgpt_desktop_flow.dispatch_prompt_flow", transaction)
    bus = EventBus()
    executor = ToolExecutor(bus, RiskTierEvaluator(SafetyConfig(approval_mode="ask")), ApprovalWorkflow(bus))
    result = await executor.execute(
        ChatGPTTaskTool(None), {"prompt": "Reply READY", "target_chat": "Jarvis Test"},
        user_utterance="Send Reply READY to Jarvis Test", config_snapshot={"voice_confirm": True},
    )
    assert result.error == VOICE_CONFIRM_SENTINEL
    assert not called
