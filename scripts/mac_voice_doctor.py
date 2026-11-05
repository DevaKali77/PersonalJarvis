#!/usr/bin/env python3
"""Read-only Mac Jarvis voice preflight. Never records audio or changes settings.

Run: python3 scripts/mac_voice_doctor.py [--json]
Works with both legacy PersonalJarvis and newer Dodaios installations.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

CHECKED_KEYS = (
    "brain.policy.local_only",
    "brain.realtime.provider",
    "voice.mode",
    "stt.provider",
    "tts.provider",
    "trigger.wake_word_enabled",
)
PAID_REALTIME = {"gemini-live", "openai-live", "vertex-live"}
KNOWN_LOCAL_STT = {"nemotron-local", "whisper-local", "whisper-cpp", "faster-whisper"}
KNOWN_LOCAL_TTS = {"piper-local", "kokoro-local", "pocket-local", "system"}


def command_json(command: list[str], timeout: int = 8) -> dict:
    """Run only an explicit read-only CLI call; do not expose stderr or secrets."""
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout, check=False)
        if result.returncode != 0:
            return {}
        parsed = json.loads(result.stdout)
        return parsed if isinstance(parsed, dict) else {}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {}


def settings_snapshot(cli: str = "jarvisctl") -> dict:
    return {
        key: command_json([cli, "config", "get", key]).get("value")
        for key in CHECKED_KEYS
    }


def analyze_settings(values: dict) -> list[dict]:
    """Pure policy analysis: unknown values are not false certainty."""
    alerts: list[dict] = []
    local_only = values.get("brain.policy.local_only") is True
    mode = values.get("voice.mode")
    live = values.get("brain.realtime.provider")
    if local_only and mode == "realtime" and live in PAID_REALTIME:
        alerts.append({
            "severity": "critical",
            "code": "LOCAL_ONLY_REALTIME_CONFLICT",
            "message": "Local-only brain with an API realtime voice provider selected.",
            "action": "Use a supported local voice mode/provider; approval and restart may be required.",
        })
    if local_only and mode != "realtime":
        stt, tts = values.get("stt.provider"), values.get("tts.provider")
        if stt and stt not in KNOWN_LOCAL_STT:
            alerts.append({
                "severity": "warning", "code": "CHECK_STT_BILLING",
                "message": "Verify that the selected STT provider runs locally.",
            })
        if tts and tts not in KNOWN_LOCAL_TTS:
            alerts.append({
                "severity": "warning", "code": "CHECK_TTS_BILLING",
                "message": "Verify that the selected TTS provider runs locally.",
            })
    if values.get("trigger.wake_word_enabled") is False:
        alerts.append({
            "severity": "info", "code": "WAKE_DISABLED",
            "message": "Wake word is disabled; hotkey voice may still work.",
        })
    return alerts


def ollama_snapshot() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as response:
            data = json.load(response)
        models = data.get("models", [])
        return {"reachable": True, "model_count": len(models)}
    except (OSError, ValueError, KeyError):
        return {"reachable": False, "model_count": None}


def muted_gate_seen() -> bool | None:
    """Read only the tail of known local app logs, report a boolean, never log text."""
    paths = (
        Path.home() / ".dodaios/data/jarvis_desktop.log",
        Path.home() / ".jarvis/data/jarvis_desktop.log",
    )
    for path in paths:
        try:
            with path.open("rb") as stream:
                stream.seek(0, 2)
                stream.seek(max(0, stream.tell() - 8192))
                tail = stream.read().decode("utf-8", errors="replace")
            return "activation gate closed (voice is muted)" in tail.lower()
        except OSError:
            continue
    return None


def preflight() -> dict:
    cli = shutil.which("jarvisctl")
    values = settings_snapshot(cli) if cli else {}
    server = command_json([cli, "system", "status"]) if cli else {}
    permissions = command_json([cli, "permissions", "status"]) if cli else {}
    microphone = next(
        (p.get("status") for p in permissions.get("permissions", [])
         if p.get("id") == "microphone"),
        None,
    )
    alerts = analyze_settings(values)
    if cli is None:
        alerts.append({"severity": "warning", "code": "CLI_NOT_FOUND",
                       "message": "jarvisctl is unavailable in PATH."})
    if cli is not None and server.get("reachable") is False:
        alerts.append({"severity": "warning", "code": "SERVER_UNREACHABLE",
                       "message": "Jarvis control server did not respond."})
    if microphone in ("denied", "restricted"):
        alerts.append({"severity": "critical", "code": "MICROPHONE_PERMISSION",
                       "message": "macOS microphone permission is not granted."})
    return {
        "diagnostic": "mac_voice_doctor",
        "read_only": True,
        "platform": sys.platform,
        "jarvisctl_present": cli is not None,
        "server_reachable": server.get("reachable"),
        "microphone_permission": microphone,
        "mute_gate_observed_in_log_tail": muted_gate_seen(),
        "ollama": ollama_snapshot(),
        "settings": values,
        "alerts": alerts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON, no private audio or tokens.")
    args = parser.parse_args()
    status = preflight()
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print("Jarvis voice preflight — read-only")
        print("App reachable:", status["server_reachable"])
        print("Microphone permission:", status["microphone_permission"])
        print("Mute gate seen recently:", status["mute_gate_observed_in_log_tail"])
        print("Ollama available:", status["ollama"]["reachable"])
        for alert in status["alerts"]:
            print(f"[{alert['severity'].upper()}] {alert['code']}: {alert['message']}")
        if not status["alerts"]:
            print("No configuration alerts. A human-triggered acoustic test is still required.")
    return 2 if any(x["severity"] == "critical" for x in status["alerts"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())

[executed on device: MacBookPro.lan (f7e7ab18-9a6e-4c17-a336-37f4547ad376)]