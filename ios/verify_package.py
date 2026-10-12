"""Verify a private IPA's compatibility, load path, payload preservation and signing privacy."""
import argparse
import hashlib
import json
import plistlib
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path
from prepare_ipa import BASE_SHA, LOAD_PATH, PACKET_SHA, VERSION, commands, extract


def digest(path):
    with path.open("rb") as f: return hashlib.file_digest(f, "sha256").hexdigest()


def image_details(data):
    loads, sections, minimum = [], {}, None
    for offset, command, length in commands(data):
        if command in (0xC, 0x80000018):
            nameoff = struct.unpack_from("<I", data, offset + 8)[0]
            loads.append(data[offset + nameoff:offset + length].split(b"\0", 1)[0].decode())
        elif command == 0x32:
            minimum = struct.unpack_from("<I", data, offset + 12)[0]
        elif command == 0x25:
            minimum = struct.unpack_from("<I", data, offset + 8)[0]
        elif command == 0x19:
            nsects = struct.unpack_from("<I", data, offset + 64)[0]
            for i in range(nsects):
                s = offset + 72 + i * 80
                name = data[s:s + 16].split(b"\0", 1)[0].decode()
                segment = data[s + 16:s + 32].split(b"\0", 1)[0].decode()
                size = struct.unpack_from("<Q", data, s + 40)[0]
                start = struct.unpack_from("<I", data, s + 48)[0]
                if start and size: sections[f"{segment}/{name}"] = data[start:start + size]
    assert minimum is not None and minimum <= ((15 << 16) | (8 << 8) | 8), "Minimum OS incompatible"
    assert struct.unpack_from("<I", data, 8)[0] & 0xFFFFFF == 0, "Expected generic ARM64, not ARM64e"
    return loads, sections, minimum


def initializer_details(data):
    """Validate ARM64 constructor targets for both dyld section encodings.

    Apple dyld-955 MachOAnalyzer::forEachInitializer supports S_INIT_FUNC_OFFSETS
    (0x16): aligned uint32 offsets relative to the preferred image address, in a
    read-only segment, pointing to executable code. See Apple's original source:
    https://github.com/apple-oss-distributions/dyld/blob/dyld-955/common/MachOAnalyzer.cpp
    This release additionally requires every target to lie inside __text.
    """
    segments, sections = [], []
    for offset, command, length in commands(data):
        if command != 0x19: continue
        vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<4Q", data, offset + 24)
        initprot, count = struct.unpack_from("<2I", data, offset + 60)
        assert length == 72 + count * 80
        segment = data[offset + 8:offset + 24].split(b"\0", 1)[0].decode()
        segments.append({"name": segment, "address": vmaddr, "size": vmsize,
                         "fileoff": fileoff, "filesize": filesize, "protection": initprot})
        for i in range(count):
            s = offset + 72 + i * 80
            name = data[s:s + 16].split(b"\0", 1)[0].decode()
            address, size = struct.unpack_from("<2Q", data, s + 32)
            start = struct.unpack_from("<I", data, s + 48)[0]
            flags = struct.unpack_from("<I", data, s + 64)[0]
            sections.append({"name": name, "segment": segment, "address": address,
                             "size": size, "fileoff": start, "type": flags & 0xFF, "protection": initprot})
    bases = [s["address"] for s in segments if s["fileoff"] == 0 and s["filesize"]]
    assert len(bases) == 1, "Ambiguous preferred image address"
    base = bases[0]
    text = [s for s in sections if s["name"] == "__text" and s["protection"] & 4]
    assert text, "No executable text section"
    result = []
    for s in sections:
        if s["type"] not in (0x09, 0x16): continue
        width = 4 if s["type"] == 0x16 else 8
        assert s["size"] > 0 and s["size"] % width == 0 and s["address"] % width == 0, "Malformed initializer section"
        assert s["fileoff"] and s["fileoff"] + s["size"] <= len(data), "Initializer data outside file"
        containers = [segment for segment in segments if segment["name"] == s["segment"] and
                      segment["address"] <= s["address"] and s["address"] + s["size"] <= segment["address"] + segment["size"] and
                      segment["fileoff"] <= s["fileoff"] and s["fileoff"] + s["size"] <= segment["fileoff"] + segment["filesize"]]
        assert len(containers) == 1, "Initializer section outside its segment"
        if s["type"] == 0x16: assert not s["protection"] & 2, "Initializer offsets must be read-only"
        for start in range(s["fileoff"], s["fileoff"] + s["size"], width):
            raw = struct.unpack_from("<I" if width == 4 else "<Q", data, start)[0]
            target = base + raw if width == 4 else raw
            targets = [t for t in text if t["address"] <= target < t["address"] + t["size"]]
            assert len(targets) == 1 and target % 4 == 0, "Initializer does not point to ARM64 executable text"
            t = targets[0]; target_file = t["fileoff"] + target - t["address"]
            assert target_file + 4 <= len(data), "Initializer code outside file"
            result.append({"format": "S_INIT_FUNC_OFFSETS" if width == 4 else "S_MOD_INIT_FUNC_POINTERS",
                           "section": f'{s["segment"]}/{s["name"]}', "target_address": hex(target),
                           "target_file_offset": hex(target_file), "target_section": f'{t["segment"]}/{t["name"]}'})
    assert result, "No valid constructor encoded in Mach-O"
    return result


def verify_empty_entitlements(output, binary_name, *, allow_absent=False):
    """Accept only empty XML entitlements, or truly absent entitlements for signed nested code.

    Some ad-hoc signed Mach-O dylibs have no entitlement blob, even when signing
    supplied an explicit empty plist. For those verified nested binaries, codesign
    can return successful status and zero stdout with --entitlements - --xml.
    The caller must separately verify the code signature and anonymous identity.
    Non-empty, malformed or unexpected entitlement output always fails.
    """
    if allow_absent and output == b"":
        return True
    xml = output.strip()
    if not xml or not xml.startswith((b"<?xml", b"<plist")):
        raise ValueError(f"Missing or non-XML signed entitlements: {binary_name}")
    try:
        value = plistlib.loads(xml)
    except Exception:
        raise ValueError(f"Unreadable XML signed entitlements: {binary_name}") from None
    if not isinstance(value, dict) or value:
        raise ValueError(f"Nonempty signed entitlements: {binary_name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ipa", type=Path)
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-codesign", action="store_true", help="Windows archive checks; cloud evidence must also verify signatures")
    args = parser.parse_args()
    assert digest(args.base) == BASE_SHA
    with zipfile.ZipFile(args.base) as baseline, zipfile.ZipFile(args.ipa) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert not any(n.endswith(".mobileprovision") for n in names)
        assert not any(n.endswith((".ndjson", ".p12", ".p8")) for n in names)
        assert "Payload/Discord.app/Frameworks/DroverDiagnostics.dylib" not in names
        info = plistlib.loads(archive.read("Payload/Discord.app/Info.plist"))
        old_info = plistlib.loads(baseline.read("Payload/Discord.app/Info.plist"))
        assert info["CFBundleIdentifier"] == old_info["CFBundleIdentifier"]
        assert info["CFBundleDisplayName"] == "Discord DVR" and info["DiscordDVRVersion"] == VERSION
        packet = archive.read("Payload/Discord.app/drover-packet.bin")
        assert len(packet) == 1200 and hashlib.sha256(packet).hexdigest() == PACKET_SHA
        loads, sections, minimum = image_details(archive.read("Payload/Discord.app/Discord"))
        _, old_sections, _ = image_details(baseline.read("Payload/Discord.app/Discord"))
        assert sections["__TEXT/__text"] == old_sections["__TEXT/__text"], "Discord code instructions changed"
        assert loads.count(LOAD_PATH) == 1
        dylib = archive.read("Payload/Discord.app/Frameworks/DiscordDVR.dylib")
        dependencies, lib_sections, lib_minimum = image_details(dylib)
        initializers = initializer_details(dylib)
        assert not any(any(x in d for x in ("UIKit", "AVFoundation", "QuartzCore")) for d in dependencies)
        for marker in (b"drover_prelude", b"session_start", b"flow_summary", b"dave_keychain", b"DroverDiagnostics", b"DTInstallVoiceControl"):
            assert marker not in dylib, f"Diagnostic content in release: {marker!r}"
    signed_count = 0
    if not args.skip_codesign:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); extract(args.ipa, root)
            app = root / "Payload/Discord.app"
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
            for file in app.rglob("*"):
                if file.is_file() and not file.is_symlink() and file.read_bytes()[:4] == b"\xcf\xfa\xed\xfe":
                    result = subprocess.run(["codesign", "--display", "--verbose=4", "--entitlements", "-", "--xml", str(file)], capture_output=True)
                    assert result.returncode == 0, f"Cannot inspect signature: {file.name}"
                    # A displayed ad-hoc signature is not enough: verify each Mach-O
                    # before allowing absent entitlement data on embedded binaries.
                    subprocess.run(["codesign", "--verify", "--strict", str(file)], check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    metadata = result.stdout + result.stderr
                    assert b"Signature=adhoc" in metadata and b"TeamIdentifier=not set" in metadata, f"Signature is not anonymous ad-hoc: {file.name}"
                    assert b"Authority=" not in metadata, f"Certificate authority present: {file.name}"
                    is_nested_binary = file != app / info["CFBundleExecutable"]
                    verify_empty_entitlements(result.stdout, file.name, allow_absent=is_nested_binary)
                    print(f"Signature privacy verified: {file.name} (ad-hoc, no team, no unexpected entitlements)")
                    signed_count += 1
    report = {"version": VERSION, "ipa_sha256": digest(args.ipa), "ipa_bytes": args.ipa.stat().st_size,
              "archive_crc_verified": True, "arm64_generic": True, "main_minimum_os_encoded": minimum,
              "library_minimum_os_encoded": lib_minimum, "main_text_unchanged": True,
              "packet_bytes": 1200, "packet_sha256": PACKET_SHA, "constructor_present": True,
              "constructor_details": initializers,
              "release_ui_logging_media_observers_absent": True, "bundle_identifier_unchanged": True,
              "embedded_provisioning_profiles": 0, "ad_hoc_empty_entitlement_binaries_verified": signed_count,
              "codesign_verified": not args.skip_codesign, "device_0_3_1_tested": False}
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
