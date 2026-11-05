from types import SimpleNamespace
from uuid import uuid4

import pytest

from dodaios.core.protocols import ExecutionContext
from dodaios.plugins.tool import open_app as oa
from dodaios.live.tools import LiveTools


def context():
    return ExecutionContext(trace_id=uuid4(), user_utterance="Open my Downloads", config={}, memory_read=None)


async def test_nonexistent_path_is_not_reported_open(monkeypatch, tmp_path):
    monkeypatch.setattr(oa, "detect_platform", lambda: "darwin")
    monkeypatch.setattr(oa, "_is_plausible_app_name", lambda _: (True, "", ""))
    monkeypatch.setattr(oa, "resolve_app_launch_target", lambda value: SimpleNamespace(kind="startfile", value=value))
    monkeypatch.setattr(oa.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("Must not launch an absent path"))
    result = await oa.OpenAppTool().execute({"app_name": str(tmp_path / "missing")}, context())
    assert not result.success
    assert "does not exist" in result.error


async def test_os_refusal_is_not_reported_as_success(monkeypatch):
    monkeypatch.setattr(oa, "detect_platform", lambda: "darwin")
    monkeypatch.setattr(oa, "_is_plausible_app_name", lambda _: (True, "", ""))
    monkeypatch.setattr(oa, "resolve_app_launch_target", lambda _: SimpleNamespace(kind="open_a", value="Missing"))
    def refused(*_args, **_kwargs):
        raise oa.subprocess.CalledProcessError(1, ["open"])
    monkeypatch.setattr(oa.subprocess, "run", refused)
    result = await oa.OpenAppTool().execute({"app_name": "Missing", "reuse_existing": False}, context())
    assert not result.success
    assert LiveTools._result(result)["verified"] is False


async def test_downloads_uses_actual_user_directory(monkeypatch, tmp_path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    monkeypatch.setattr("dodaios.platform.user_dirs.downloads_dir", lambda: downloads)
    monkeypatch.setattr(oa, "detect_platform", lambda: "darwin")
    monkeypatch.setattr(oa, "_is_plausible_app_name", lambda _: (True, "", ""))
    monkeypatch.setattr(oa, "resolve_app_launch_target", lambda value: SimpleNamespace(kind="startfile", value=value))
    calls = []
    monkeypatch.setattr(oa.subprocess, "run", lambda argv, **kwargs: calls.append((argv, kwargs)))
    result = await oa.OpenAppTool().execute({"app_name": "Downloads"}, context())
    assert result.success
    assert calls[0][0] == ["open", str(downloads)]
    assert calls[0][1]["check"] is True
