"""Read-only proof of a selected chat when the native window title is generic."""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable


def selected_chat_matches(root: Any, target: str, read: Callable[[Any, str], Any]) -> bool:
    wanted = " ".join(target.split()).casefold()
    queue = deque([(root, 0)])
    deadline = time.monotonic() + 0.8
    visited = 0
    while queue and visited < 1500 and time.monotonic() < deadline:
        element, depth = queue.popleft()
        visited += 1
        if read(element, "AXSelected") == True:  # noqa: E712 - require a native true value
            labels = deque([(element, 0)])
            for _ in range(80):
                if not labels or time.monotonic() >= deadline:
                    break
                child, level = labels.popleft()
                for attribute in ("AXTitle", "AXDescription"):
                    value = read(child, attribute)
                    if isinstance(value, str) and " ".join(value.split()).casefold() == wanted:
                        return True
                if level < 3:
                    labels.extend((c, level + 1) for c in (read(child, "AXChildren") or []))
        if depth < 14:
            queue.extend((child, depth + 1) for child in (read(element, "AXChildren") or []))
    return False


def macos_named_chat_selected(pid: int, target: str) -> bool:
    try:
        import ApplicationServices as ax
        from dodaios.vision.ax_tree import _ax_copy_attr

        app = ax.AXUIElementCreateApplication(pid)
        window = _ax_copy_attr(app, "AXFocusedWindow")
        return bool(window is not None and selected_chat_matches(window, target, _ax_copy_attr))
    except Exception:
        return False
