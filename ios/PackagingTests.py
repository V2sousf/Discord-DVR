"""Test header-only Mach-O injection and hostile ZIP rejection without Discord files."""
import importlib.util
import plistlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("private_packager", Path(__file__).with_name("prepare_ipa.py"))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
verify_spec = importlib.util.spec_from_file_location("package_verifier", Path(__file__).with_name("verify_package.py"))
verifier = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(verifier)


def fixture(encrypted=False):
    # ARM64 executable with segment + one section and verified header padding.
    segment = bytearray(152)
    struct.pack_into("<II", segment, 0, 0x19, 152)
    struct.pack_into("<I", segment, 64, 1)
    struct.pack_into("<Q", segment, 72 + 40, 16)
    struct.pack_into("<I", segment, 72 + 48, 512)
    encryption = struct.pack("<6I", 0x2C, 24, 512, 16, int(encrypted), 0)
    header = struct.pack("<8I", 0xFEEDFACF, 0x0100000C, 0, 2, 2, len(segment) + len(encryption), 0, 0)
    return bytearray(header + segment + encryption + bytes(512 - len(header + segment + encryption)) + b"UNCHANGED-PAYLOAD")


def initializer_fixture(kind=0x16, target=512, size=None, writable=False):
    """Owned minimal image with a real ARM64 RET at its constructor target."""
    width = 4 if kind == 0x16 else 8
    if size is None: size = width
    base = 0x100000000
    segment = bytearray(72 + 2 * 80)
    struct.pack_into("<II", segment, 0, 0x19, len(segment))
    segment[8:14] = b"__TEXT"
    struct.pack_into("<4Q", segment, 24, base, 1024, 0, 1024)
    struct.pack_into("<4I", segment, 56, 7, 7 if writable else 5, 2, 0)
    for index, (name, start, length, flags) in enumerate(((b"__text", 512, 64, 0),
                                                       (b"__init_offsets" if width == 4 else b"__mod_init_func", 640, size, kind))):
        s = 72 + index * 80
        segment[s:s + len(name)] = name
        segment[s + 16:s + 22] = b"__TEXT"
        struct.pack_into("<2Q", segment, s + 32, base + start, length)
        struct.pack_into("<I", segment, s + 48, start)
        struct.pack_into("<I", segment, s + 64, flags)
    data = bytearray(1024)
    struct.pack_into("<8I", data, 0, 0xFEEDFACF, 0x0100000C, 0, 6, 1, len(segment), 0, 0)
    data[32:32 + len(segment)] = segment
    struct.pack_into("<I", data, 512, 0xD65F03C0)
    struct.pack_into("<I" if width == 4 else "<Q", data, 640, target if width == 4 else base + target)
    return data


class Packaging(unittest.TestCase):
    def test_header_injection_preserves_payload_and_exact_name(self):
        data = fixture(); payload = bytes(data[512:])
        original = bytes(data)
        patch = package.inject(data)
        self.assertEqual(data[512:], payload)
        self.assertEqual(patch["load_path"], "@executable_path/Frameworks/DiscordDVR.dylib")
        self.assertEqual(struct.unpack_from("<I", data, 16)[0], 3)
        insertion = int(patch["inserted_at"], 16)
        self.assertEqual(data[32:insertion], original[32:insertion])
        with self.assertRaises(ValueError): package.inject(data)

    def test_encrypted_or_unverified_padding_rejected(self):
        with self.assertRaises(ValueError): package.inject(fixture(encrypted=True))
        data = fixture(); data[220] = 1
        with self.assertRaises(ValueError): package.inject(data)

    def test_zip_traversal_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("Payload/../../escape", "/Payload/Discord.app/bad", "Payload\\bad"):
                archive = root / "bad.zip"
                info = zipfile.ZipInfo("placeholder")
                info.filename = name  # ZipInfo on Windows otherwise normalizes backslashes.
                with zipfile.ZipFile(archive, "w") as z: z.writestr(info, b"bad")
                with self.assertRaises(ValueError): package.extract(archive, root / "stage")
            info = zipfile.ZipInfo("Payload/Discord.app/link")
            info.create_system = 3; info.external_attr = (0o120777 << 16)
            with zipfile.ZipFile(root / "link.zip", "w") as z: z.writestr(info, "../../../escape")
            with self.assertRaises(ValueError): package.extract(root / "link.zip", root / "stage")

    def test_initializer_offset_and_pointer_formats_target_executable_code(self):
        for kind, expected in ((0x16, "S_INIT_FUNC_OFFSETS"), (0x09, "S_MOD_INIT_FUNC_POINTERS")):
            result = verifier.initializer_details(initializer_fixture(kind=kind))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["format"], expected)
            self.assertEqual(result[0]["target_file_offset"], "0x200")
            self.assertEqual(result[0]["target_section"], "__TEXT/__text")

    def test_invalid_initializer_encodings_rejected(self):
        for data in (initializer_fixture(target=640), initializer_fixture(target=513),
                     initializer_fixture(size=3), initializer_fixture(writable=True),
                     initializer_fixture(kind=0)):
            with self.assertRaises(AssertionError): verifier.initializer_details(data)
        with self.assertRaises(AssertionError): verifier.initializer_details(initializer_fixture()[:642])

    def test_codesign_explicit_empty_xml_formats(self):
        self.assertTrue(verifier.verify_empty_entitlements(plistlib.dumps({}), "OwnedTestBinary"))
        self.assertTrue(verifier.verify_empty_entitlements(b'<plist version="1.0"><dict/></plist>\n', "OwnedTestBinary"))

    def test_signed_nested_library_without_entitlements_is_accepted(self):
        # The integration verifier checks each code signature before passing
        # allow_absent=True; absent output alone is not evidence of a signature.
        self.assertTrue(verifier.verify_empty_entitlements(b"", "OwnedTestDylib", allow_absent=True))
        self.assertTrue(verifier.verify_empty_entitlements(plistlib.dumps({}), "OwnedTestDylib", allow_absent=True))
        with self.assertRaises(ValueError):
            verifier.verify_empty_entitlements(b"", "OwnedTestExecutable")

    def test_nested_library_rejects_nonempty_or_malformed_entitlements(self):
        for output in (b"\n", b"[Dict]", b"<plist><dict>",
                       plistlib.dumps({}, fmt=plistlib.FMT_BINARY),
                       plistlib.dumps({"com.apple.developer.team-identifier": "SECRET-TEAM"})):
            with self.assertRaises(ValueError) as caught:
                verifier.verify_empty_entitlements(output, "OwnedTestDylib", allow_absent=True)
            self.assertIn("OwnedTestDylib", str(caught.exception))
            self.assertNotIn("SECRET", str(caught.exception))

    def test_absent_der_text_malformed_or_nonempty_entitlements_rejected(self):
        for output in (b"", b"[Dict]", b"Executable=/private/location\n[Dict]", b"<plist><dict>",
                       plistlib.dumps({}, fmt=plistlib.FMT_BINARY),
                       plistlib.dumps({"com.apple.developer.team-identifier": "SECRET-TEAM"}),
                       plistlib.dumps(["SECRET-ACCOUNT"])):
            with self.assertRaises(ValueError) as caught:
                verifier.verify_empty_entitlements(output, "OwnedTestBinary")
            self.assertIn("OwnedTestBinary", str(caught.exception))
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertNotIn("/private", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
