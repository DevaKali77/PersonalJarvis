"""Voice app launch uses the native safety-gated tool, not keyboard emulation."""
from types import SimpleNamespace

import pytest

from dodaios.core.protocols import SupervisorToolDescriptor, ToolResult
from dodaios.live.native import NativeLiveVoiceSession
from dodaios.live.state import LiveLedger
from dodaios.live.tools import LiveTools
from tests.fakes.fake_native_voice import FakeToolGateway


def launcher():
    return SupervisorToolDescriptor(
        "open_app", "Open an application.",
        {"type": "object", "properties": {"app_name": {"type": "string"}},
         "required": ["app_name"]}, "monitor",
    )


@pytest.mark.parametrize("deferred", [False, True])
async def test_native_app_launcher_is_declared_without_discovery(tmp_path, deferred):
    ledger = LiveLedger(tmp_path / "tools.sqlite3")
    tools = LiveTools(FakeToolGateway((launcher(),)), ledger, "launch", language="en", backend_model="")
    try:
        definitions = tools.declarations(defer_catalog=deferred)
        assert sum(d["name"] == "open_app" for d in definitions) == 1
    finally:
        await tools.close()
        ledger.close()


async def test_launcher_survives_a_small_native_voice_budget(tmp_path):
    ledger = LiveLedger(tmp_path / "tools.sqlite3")
    tools = LiveTools(FakeToolGateway((launcher(),)), ledger, "launch", language="en", backend_model="")
    session = object.__new__(NativeLiveVoiceSession)
    session._tools = tools
    session._config = SimpleNamespace(voice=SimpleNamespace(realtime_tool_declaration_budget_tokens=2000))
    session._provider = SimpleNamespace(tool_declaration_budget_tokens=2000, name="fake")
    try:
        assert "open_app" in {d["name"] for d in session._tool_declarations()}
    finally:
        await tools.close()
        ledger.close()


@pytest.mark.parametrize("allowed", [True, False])
async def test_launch_keeps_gateway_safety_and_reports_denial(tmp_path, allowed):
    gateway = FakeToolGateway((launcher(),))
    gateway.results["open_app"] = ToolResult(allowed, "opened" if allowed else None, error=None if allowed else "blocked")
    ledger = LiveLedger(tmp_path / "tools.sqlite3")
    tools = LiveTools(gateway, ledger, "launch", language="en", backend_model="")
    try:
        result = await tools.execute("launch-one", "open_app", {"app_name": "Calculator"}, 0)
        assert result["success"] is allowed
        assert result["verified"] is False
        assert result["launch_accepted"] is allowed
        assert gateway.calls == [("open_app", {"app_name": "Calculator"})]
    finally:
        await tools.close()
        ledger.close()
