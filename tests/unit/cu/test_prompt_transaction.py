"""Prompt submission keeps normal tool safety and never retries a mutation."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from dodaios.core.protocols import ToolResult
from dodaios.cu import chatgpt_desktop_flow as flow


@pytest.mark.parametrize("deny", [None, "type_text", "hotkey"])
async def test_prompt_mutations_use_the_safety_executor(monkeypatch, deny):
    calls = []

    class Executor:
        async def execute(self, tool, args, **kwargs):
            calls.append((tool.name, args, kwargs))
            return ToolResult(success=tool.name != deny, output="ok", error="denied")

    monkeypatch.setattr(
        "dodaios.harness.computer_use_context.get_computer_use_context",
        lambda: SimpleNamespace(tool_executor=Executor()),
    )

    async def transaction(**kwargs):
        await kwargs["type_once"]("hello", "signature")
        await kwargs["submit_once"]("signature")
        return "reply"

    monkeypatch.setattr(flow, "run_prompt_flow", transaction)
    ctx = SimpleNamespace(user_utterance="send hello", config={}, memory_read=None, trace_id=uuid4())
    result = await flow.dispatch_prompt_flow(None, ctx, prompt="hello", target="chat", timeout_s=3, language="en")
    assert result.success == (deny is None)
    assert [call[0] for call in calls] == (["type_text"] if deny == "type_text" else ["type_text", "hotkey"])
    assert all(call[1]["_expected_window_signature"] == "signature" for call in calls)
    assert all(call[2]["user_utterance"] == ctx.user_utterance for call in calls)


@pytest.mark.parametrize("stage", ["type", "submit"])
async def test_uncertain_mutation_is_never_retried(stage):
    calls = []

    async def observe(_goal):
        return "verified"

    async def identity():
        return "same-window"

    async def type_once(*_args):
        calls.append("type")
        if stage == "type":
            raise RuntimeError("partial type")

    async def submit_once(*_args):
        calls.append("submit")
        raise RuntimeError("uncertain submission")

    with pytest.raises(RuntimeError):
        await flow.run_prompt_flow(prompt="hello", target="chat", observe=observe,
                                   identity=identity, type_once=type_once, submit_once=submit_once)
    assert calls == (["type"] if stage == "type" else ["type", "submit"])
