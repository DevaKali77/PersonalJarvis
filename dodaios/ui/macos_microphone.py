"""Remember authorized microphone access for the installed app's own page."""
from __future__ import annotations
import logging
import sys
from urllib.parse import urlsplit

log = logging.getLogger(__name__)


def _origin(value: str) -> tuple[str, str, int | None] | None:
    try:
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            return None
        return parsed.scheme, parsed.hostname or "", parsed.port
    except (ValueError, TypeError):
        return None


def trusted_microphone_request(expected_url: str, page_url: str, request_url: str,
                               frame_url: str, *, main_frame: bool,
                               microphone_only: bool, os_granted: bool) -> bool:
    """Never expand permission to cameras, other ports, sites, or subframes."""
    expected = _origin(expected_url)
    return bool(
        expected and expected[0] == "http" and expected[1] == "127.0.0.1"
        and expected[2] is not None and main_frame and microphone_only and os_granted
        and all(_origin(url) == expected for url in (page_url, request_url, frame_url))
    )


def install_macos_microphone_permission(expected_url: str) -> bool:
    """Install the WKUIDelegate policy before pywebview creates its windows."""
    if sys.platform != "darwin":
        return False
    try:
        import AVFoundation
        import WebKit
        import objc
        import webview.platforms.cocoa as cocoa
        base = cocoa.BrowserView.BrowserDelegate
        if getattr(base, "_dodaios_microphone_policy", False):
            return True

        # Some WebKit decision blocks omit runtime signature metadata.
        # Invoke that public callback through its native NSInteger ABI.
        import ctypes
        from pathlib import Path
        library = ctypes.CDLL(str(Path(__file__).with_name("microphone_decision.dylib")))
        complete_decision = library.dodaios_complete_media_decision
        complete_decision.argtypes = [ctypes.c_void_p, ctypes.c_long]
        complete_decision.restype = None

        class DodaiosMicrophoneDelegate(base, protocols=[objc.protocolNamed("WKUIDelegate")]):
            _dodaios_microphone_policy = True

            def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
                self, webview, origin, frame, capture_type, handler
            ):
                decision = WebKit.WKPermissionDecisionPrompt
                try:
                    request_url = f"{origin.protocol()}://{origin.host()}:{origin.port()}"
                    allowed = trusted_microphone_request(
                        expected_url, str(webview.URL().absoluteString()), request_url,
                        str(frame.request().URL().absoluteString()),
                        main_frame=bool(frame.isMainFrame()),
                        microphone_only=capture_type == WebKit.WKMediaCaptureTypeMicrophone,
                        os_granted=AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                            AVFoundation.AVMediaTypeAudio
                        ) == AVFoundation.AVAuthorizationStatusAuthorized,
                    )
                    if allowed:
                        decision = WebKit.WKPermissionDecisionGrant
                        log.info("Microphone permission reused for the authorized Dodaios page.")
                except Exception:
                    log.exception("Microphone permission check failed; retaining the system prompt.")
                try:
                    complete_decision(objc.pyobjc_id(handler), int(decision))
                except Exception:
                    log.exception("Native microphone decision callback failed.")

        cocoa.BrowserView.BrowserDelegate = DodaiosMicrophoneDelegate
        log.info("Installed microphone permission reuse for the exact Dodaios origin.")
        return True
    except Exception:
        log.exception("Could not install microphone permission reuse; retaining system prompts.")
        return False
