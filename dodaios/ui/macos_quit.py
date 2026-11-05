"""Route native macOS Quit through the desktop's bounded cleanup path."""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


def request_orderly_quit(browser: Any, app: Any, sender: Any,
                         on_quit: Callable[[], None]) -> int:
    """Cancel Cocoa's immediate libc exit, then let webview.start return.

    A native terminate reply of YES exits without returning to DesktopApp's
    cleanup, racing native model finalizers against background Qt imports.
    Zero is NSTerminateCancel; stopping the event loop returns to our owner.
    """
    for instance in list(browser.instances.values()):
        if not browser.should_close(instance.pywebview_window):
            return 0
    on_quit()
    app.stop_(sender)
    return 0


def install_macos_quit_handler(on_quit: Callable[[], None]) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        import webview.platforms.cocoa as cocoa

        browser = cocoa.BrowserView
        base = browser.AppDelegate
        if getattr(base, "_dodaios_orderly_quit", False):
            base._dodaios_quit_callback = staticmethod(on_quit)
            return True

        class DodaiosQuitDelegate(base):
            _dodaios_orderly_quit = True
            _dodaios_quit_callback = staticmethod(on_quit)

            def applicationShouldTerminate_(self, app):
                try:
                    return request_orderly_quit(
                        browser, app, self, type(self)._dodaios_quit_callback,
                    )
                except Exception:
                    # Never fall back to immediate native exit on a failed
                    # cleanup request. The user can retry the normal Quit.
                    log.exception("Could not request orderly native Quit")
                    return 0

        browser.AppDelegate = DodaiosQuitDelegate
        log.info("Native macOS Quit uses the desktop cleanup owner")
        return True
    except Exception:
        log.exception("Could not install orderly native Quit")
        return False
