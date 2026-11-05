"""Pure policy tests for scripts/mac_voice_doctor.py (stdlib-only)."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "mac_voice_doctor.py"
spec = importlib.util.spec_from_file_location("mac_voice_doctor", MODULE)
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class VoiceDoctorTests(unittest.TestCase):
    def test_local_only_gemini_realtime_mismatch(self):
        settings = {"brain.policy.local_only": True,
                    "voice.mode": "realtime",
                    "brain.realtime.provider": "gemini-live"}
        codes = [a["code"] for a in doctor.analyze_settings(settings)]
        self.assertIn("LOCAL_ONLY_REALTIME_CONFLICT", codes)

    def test_local_classic_no_false_warning(self):
        settings = {"brain.policy.local_only": True,
                    "voice.mode": "classic",
                    "stt.provider": "nemotron-local",
                    "tts.provider": "piper-local"}
        self.assertEqual(doctor.analyze_settings(settings), [])

    def test_cloud_stt_in_classic_mode_detected(self):
        settings = {"brain.policy.local_only": True,
                    "voice.mode": "classic",
                    "stt.provider": "gemini",
                    "tts.provider": "piper-local"}
        codes = [a["code"] for a in doctor.analyze_settings(settings)]
        self.assertIn("CHECK_STT_BILLING", codes)

    def test_cloud_tts_in_classic_mode_detected(self):
        settings = {"brain.policy.local_only": True,
                    "voice.mode": "classic",
                    "stt.provider": "nemotron-local",
                    "tts.provider": "elevenlabs"}
        codes = [a["code"] for a in doctor.analyze_settings(settings)]
        self.assertIn("CHECK_TTS_BILLING", codes)

    def test_wake_disabled_is_info_not_failure(self):
        settings = {"trigger.wake_word_enabled": False}
        a = doctor.analyze_settings(settings)
        self.assertEqual(a[0]["severity"], "info")
        self.assertEqual(a[0]["code"], "WAKE_DISABLED")

    def test_unknown_values_not_misclassified(self):
        self.assertEqual(doctor.analyze_settings({}), [])


if __name__ == "__main__":
    unittest.main()

[executed on device: MacBookPro.lan (f7e7ab18-9a6e-4c17-a336-37f4547ad376)]