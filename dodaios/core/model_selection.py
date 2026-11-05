"""Per-operation model selection; never mutate the shared BrainManager for a call."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str | None
    reasoning_effort: str = ""
    # An operation-owned client preserves the selected account and billing path.
    # It is intentionally process-local, never persisted or shown in repr/logs.
    brain_override: Any = field(default=None, repr=False, compare=False)


operation_model: ContextVar[ModelSelection | None] = ContextVar("operation_model", default=None)


def worker_selection(config: Any) -> ModelSelection | None:
    worker = getattr(getattr(config, "brain", None), "worker", None)
    if worker is None or not getattr(worker, "provider", ""):
        return None
    from dodaios.missions.worker_runtime.provider_map import CODEX_SUBAGENT_SLUGS

    provider = worker.provider
    if provider in CODEX_SUBAGENT_SLUGS:
        provider = "codex"
    elif provider in {"claude-subscription", "claude-code"}:
        provider = "claude-cli"
    elif provider == "openai-api":
        provider = "openai"
    return ModelSelection(provider, worker.model, str(getattr(worker, "reasoning_effort", "")))


@contextmanager
def use_operation_model(selection: ModelSelection | None):
    token = operation_model.set(selection)
    try:
        yield
    finally:
        operation_model.reset(token)


def tool_selection(config: Any) -> ModelSelection | None:
    """An explicit Tool Model takes priority over the default mission worker."""
    selected = operation_model.get()
    if selected is not None:
        return selected
    brain = getattr(config, "brain", None)
    tier = getattr(brain, "tool_model", None) or getattr(brain, "computer_use", None)
    provider = str(getattr(tier, "provider", "") or "").strip()
    if provider and provider != "auto":
        pc = (getattr(brain, "providers", None) or {}).get(provider)
        model = (getattr(pc, "tool_model", None) or getattr(pc, "cu_model", None)
                 or getattr(pc, "model", None))
        return ModelSelection(provider, model)
    return worker_selection(config)
