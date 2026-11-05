from types import SimpleNamespace

from dodaios.ui.macos_quit import request_orderly_quit


def test_native_quit_cancels_immediate_exit_and_stops_loop_after_request():
    calls = []
    browser = SimpleNamespace(
        instances={1: SimpleNamespace(pywebview_window="main")},
        should_close=lambda window: calls.append(("close", window)) or True,
    )
    app = SimpleNamespace(stop_=lambda sender: calls.append(("stop", sender)))
    reply = request_orderly_quit(browser, app, "sender", lambda: calls.append(("cleanup",)))
    assert reply == 0
    assert calls == [("close", "main"), ("cleanup",), ("stop", "sender")]


def test_declined_window_close_does_not_stop_or_quit():
    calls = []
    browser = SimpleNamespace(instances={1: SimpleNamespace(pywebview_window="main")},
                              should_close=lambda _: False)
    app = SimpleNamespace(stop_=lambda _: calls.append("stop"))
    assert request_orderly_quit(browser, app, None, lambda: calls.append("quit")) == 0
    assert not calls
