"""Release boundary checks. Dynamic network/Keychain tests run separately on macOS."""
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ReleaseBoundary(unittest.TestCase):
    def test_release_is_independent_of_diagnostics(self):
        source = (ROOT / "DiscordDVR.m").read_text(encoding="utf-8")
        keychain = (ROOT / "DAVEKeychain.inc").read_text(encoding="utf-8")
        for name in ("UIKit", "AVFoundation", "VoiceControl", "SessionState", "DiagnosticPanel",
                     "DTControlEmit", "DTLog", "NDJSON", "NSUserDefaults", "dispatch_source_create",
                     "NSJSONSerialization", "UIApplication", "UIButton", "DTSession", "DTKeychainResult"):
            self.assertNotIn(name, source + keychain)
        for pattern in (r"\bopen\s*\(", r"\bfopen\s*\(", r"\bfwrite\s*\(", r"\bNSLog\s*\(",
                        r"\bprintf\s*\(", r"\bwriteToFile\b", r"\bcontentsOfDirectoryAtPath\b"):
            self.assertNotRegex(source + keychain, pattern)
        hooks = re.findall(r'\{"([A-Za-z0-9_]+)", \(void \*\)Hook_', source)
        self.assertEqual(set(hooks), {"socket", "close", "sendto", "sendmsg", "send", "write", "writev",
                         "SecItemCopyMatching", "SecItemAdd", "SecItemUpdate", "SecItemDelete", "SecKeyCreateRandomKey"})
        initializer = source[source.index("static void DVRInitialize(void)"):]
        self.assertLess(initializer.index("g_ready = true"), initializer.index("_dyld_register_func_for_add_image"))
        self.assertNotIn("drover-mode-v1", source)

    def test_no_proprietary_or_packet_input_in_source(self):
        forbidden = {".ipa", ".p12", ".p8", ".mobileprovision", ".ndjson", ".dylib", ".bin"}
        for path in ROOT.rglob("*"):
            self.assertFalse(path.is_file() and path.suffix.lower() in forbidden, str(path.name))

    def test_optional_baseline_packet_input(self):
        import os
        if not os.getenv("DVR_TEST_PACKET_PATH"):
            self.skipTest("Public tests use an owned synthetic 1200-byte fixture")
        data = Path(os.environ["DVR_TEST_PACKET_PATH"]).read_bytes()
        self.assertEqual(len(data), 1200)
        self.assertEqual(hashlib.sha256(data).hexdigest(), "f4589c57749f956bb30538197a521d7005f8b0a8723b4707e72405e51ddac50a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
