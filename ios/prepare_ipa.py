"""Private, local IPA preparation for subsequent user-owned Sideloadly signing.

Requires separately obtained inputs. This tool supplies no Discord code, proprietary
base client or upstream packet. No decryption, Apple credentials or network access.
"""
import argparse
import hashlib
import json
import os
import plistlib
import shutil
import stat
import struct
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

BASE_SHA = "122306dc80a07370c7ed77588f5fa225c2954c0448a4322549374cd40f1a3136"
LOAD_PATH = "@executable_path/Frameworks/DiscordDVR.dylib"
PACKET_SHA = "f4589c57749f956bb30538197a521d7005f8b0a8723b4707e72405e51ddac50a"
VERSION = "0.3.1"


def commands(data):
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from("<8I", data)
    if magic != 0xFEEDFACF or cpu != 0x0100000C:
        raise ValueError("Expected thin ARM64 Mach-O")
    cursor, end = 32, 32 + size
    if end > len(data) or count > 2048:
        raise ValueError("Invalid Mach-O command header")
    for _ in range(count):
        command, length = struct.unpack_from("<II", data, cursor)
        if length < 8 or length % 8 or cursor + length > end:
            raise ValueError("Invalid load command")
        yield cursor, command, length
        cursor += length
    if cursor != end:
        raise ValueError("Load command sizes do not match")


def inject(data):
    original = bytes(data)
    count, size = struct.unpack_from("<II", data, 16)
    first_section = len(data)
    for offset, command, length in commands(data):
        if command == 0x2C and struct.unpack_from("<I", data, offset + 16)[0] != 0:
            raise ValueError("Encrypted image rejected")
        if command in (0xC, 0x80000018):
            nameoff = struct.unpack_from("<I", data, offset + 8)[0]
            name = data[offset + nameoff:offset + length].split(b"\0", 1)[0].decode()
            if name == LOAD_PATH:
                raise ValueError("Discord DVR dylib already loaded")
        if command == 0x19:
            nsects = struct.unpack_from("<I", data, offset + 64)[0]
            if length != 72 + nsects * 80:
                raise ValueError("Malformed section count")
            for index in range(nsects):
                section = offset + 72 + index * 80
                sectsize = struct.unpack_from("<Q", data, section + 40)[0]
                fileoff = struct.unpack_from("<I", data, section + 48)[0]
                if fileoff and sectsize:
                    first_section = min(first_section, fileoff)
    name = LOAD_PATH.encode() + b"\0"
    cmdsize = (24 + len(name) + 7) & ~7
    insertion = 32 + size
    if insertion + cmdsize > first_section or any(data[insertion:insertion + cmdsize]):
        raise ValueError("Insufficient verified zero padding for load command")
    command = struct.pack("<6I", 0xC, cmdsize, 24, 0, 0, 0) + name
    command += b"\0" * (cmdsize - len(command))
    data[insertion:insertion + cmdsize] = command
    struct.pack_into("<II", data, 16, count + 1, size + cmdsize)
    # Payload locations, chained fixups and all data outside the header remain byte-identical.
    assert data[32:insertion] == original[32:insertion]
    assert data[insertion + cmdsize:] == original[insertion + cmdsize:]
    list(commands(data))
    return {"inserted_at": hex(insertion), "command_bytes": cmdsize, "load_path": LOAD_PATH}


def extract(ipa, destination):
    root = destination.resolve()
    with zipfile.ZipFile(ipa) as archive:
        infos = archive.infolist()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > 2 * 1024**3:
            raise ValueError("Archive exceeds limits")
        for info in infos:
            raw_name = info.orig_filename
            name = PurePosixPath(raw_name)
            if name.is_absolute() or ".." in name.parts or "\\" in raw_name or "\0" in raw_name:
                raise ValueError("Unsafe archive path")
            if not name.parts or name.parts[0] != "Payload":
                continue
            target = destination.joinpath(*name.parts)
            if not target.resolve().is_relative_to(root):
                raise ValueError("Archive path escapes output")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                link = archive.read(info).decode()
                if Path(link).is_absolute() or not (target.parent / link).resolve().is_relative_to(root):
                    raise ValueError("Unsafe archive symlink")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(link)
            elif info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod((mode & 0o777) or 0o644)


def sign(path, entitlements):
    subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none",
                    "--entitlements", str(entitlements), str(path)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ipa", type=Path)
    parser.add_argument("dylib", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--packet-path", type=Path, help="Separately obtained, authorized pinned upstream 1200-byte packet")
    args = parser.parse_args()
    with args.ipa.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != BASE_SHA:
        raise ValueError("Base IPA SHA-256 does not match inspected version")
    if args.preflight:
        with zipfile.ZipFile(args.ipa) as archive:
            patch = inject(bytearray(archive.read("Payload/Discord.app/Discord")))
        print(json.dumps(patch))
        return
    if args.packet_path is None:
        raise ValueError("--packet-path is required for private IPA packaging")
    packet = args.packet_path.read_bytes()
    packet_sha = hashlib.sha256(packet).hexdigest()
    if len(packet) != 1200 or packet_sha != PACKET_SHA:
        raise ValueError("Upstream packet bytes differ from tested baseline")
    if args.out.exists():
        raise ValueError("Output directory must be new")
    args.out.mkdir(parents=True)
    entitlements = args.out / "ad-hoc-empty-entitlements.plist"
    entitlements.write_bytes(plistlib.dumps({}))
    stage = args.out / "stage"
    stage.mkdir()
    extract(args.ipa, stage)
    apps = list((stage / "Payload").glob("*.app"))
    if len(apps) != 1:
        raise ValueError("Expected one app")
    app = apps[0]
    metadata_path = app / "Info.plist"
    metadata = plistlib.loads(metadata_path.read_bytes())
    if metadata.get("CFBundleShortVersionString") != "260.0" or metadata.get("CFBundleVersion") != "69233":
        raise ValueError("Unexpected Discord version")
    executable = app / metadata["CFBundleExecutable"]
    data = bytearray(executable.read_bytes())
    patch = inject(data)
    executable.write_bytes(data)
    executable.chmod(0o755)
    framework = app / "Frameworks" / "DiscordDVR.dylib"
    shutil.copy2(args.dylib, framework)
    framework.chmod(0o755)
    license_path = args.dylib.parent / "fishhook-LICENSE.txt"
    shutil.copy2(license_path, app / "DiscordDVR-fishhook-LICENSE.txt")
    metadata["CFBundleDisplayName"] = "Discord DVR"
    metadata["CFBundleName"] = "Discord DVR"
    metadata.pop("DroverDiagnosticVersion", None)
    metadata["DiscordDVRVersion"] = VERSION
    shutil.copy2(args.packet_path, app / "drover-packet.bin")
    metadata_path.write_bytes(plistlib.dumps(metadata, fmt=plistlib.FMT_BINARY))
    for profile in app.rglob("embedded.mobileprovision"):
        profile.unlink()  # Sideloadly supplies a new device-specific profile.
    # Discard old resource signatures; create fresh ad-hoc signatures below.
    for signature in sorted(app.rglob("_CodeSignature"), key=lambda p: len(p.parts), reverse=True):
        if signature.is_dir() and not signature.is_symlink():
            shutil.rmtree(signature)
    binaries = []
    for path in app.rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as source:
                if source.read(4) == b"\xcf\xfa\xed\xfe":
                    binaries.append(path)
    for path in sorted(binaries, key=lambda p: len(p.parts), reverse=True):
        signed = subprocess.run(["codesign", "--display", str(path)], capture_output=True)
        if signed.returncode == 0:
            subprocess.run(["codesign", "--remove-signature", str(path)], check=True)
        sign(path, entitlements)
    for bundle in sorted(list(app.rglob("*.framework")) + list(app.rglob("*.appex")), key=lambda p: len(p.parts), reverse=True):
        sign(bundle, entitlements)
    sign(app, entitlements)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    subprocess.run(["xcrun", "otool", "-L", str(executable)], check=True)
    output = args.out / f"Discord-DVR-{VERSION}-260.0.ipa"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted((stage / "Payload").rglob("*")):
            relative = path.relative_to(stage).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(relative)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, os.readlink(path))
            elif path.is_file():
                archive.write(path, relative)
    with output.open("rb") as source:
        output_sha = hashlib.file_digest(source, "sha256").hexdigest()
    build = {"release_version": VERSION, "mode": "always-on Direct from constructor; no mode preference or diagnostic recording", "base_ipa_sha256": actual,
             "upstream_packet_sha256": packet_sha, "upstream_packet_bytes": len(packet),
             "ipa_sha256": output_sha, "ipa_bytes": output.stat().st_size,
             "signature": "ad-hoc; requires Sideloadly signing for installation", "patch": patch,
             "architecture": "arm64", "minimum_os": "15.1", "device_runtime_tested": False,
             "baseline_0_3_0_user_tested": "iPhone 7 / iOS 15.8.8 / UAE: voice, video and screen sharing",
             "bundle_identifier_changed": False, "embedded_provisioning_removed": True,
             "apple_identity_embedded": False, "distribution": "private test only; proprietary input redistribution not cleared"}
    (args.out / "build-details.json").write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
    (args.out / "SHA256SUMS.txt").write_text(output_sha + "  " + output.name + "\n", encoding="utf-8")
    print(json.dumps(build))


if __name__ == "__main__":
    main()
