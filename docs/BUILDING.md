# Build and test the iOS adaptation

Run the source build on **macOS with Xcode and Python 3**. The iOS SDK and Clang are required for an ARM64 dynamic library. This repository contains only the original DVR adaptation and its build tools, not a complete Discord app.

## Build the library

```sh
bash ios/build_release.sh
```

The script obtains pinned fishhook source and runs the release network, DAVE Keychain, source, and packaging unit tests. If they pass, it compiles `build/release/DiscordDVR.dylib` for iOS 15.1+ on ARM64. The generated library is **not an iPhone app**.

[The GitHub Actions source workflow](../.github/workflows/build-release.yml) runs a source-only build. Do not mistake its generated source/library artifact for a ready-to-install Discord IPA.

## Package a local test IPA

Use `ios/prepare_ipa.py` only with inputs you have permission to use. The tool checks exact version and SHA-256 values and will refuse different inputs. It does not decrypt the client or grant permission to distribute it.

```sh
python3 ios/prepare_ipa.py /path/to/authorized-base.ipa \
  build/release/DiscordDVR.dylib /path/to/new-package-directory \
  --packet-path /path/to/authorized-drover-packet.bin
```

The tool creates an ad-hoc-signed local IPA that still needs signing for your own device using Sideloadly. A separate verifier is available:

```sh
python3 ios/verify_package.py /path/to/new-package-directory/Discord-DVR-0.3.1-260.0.ipa \
  /path/to/authorized-base.ipa /path/to/new-package-directory/package-verification.json
```

Packaging requires the locally supplied upstream 1200-byte packet. The public source deliberately excludes the packet, Discord client binaries, Apple signing credentials, personal profiles, and private debug data.

## Verification and compatibility

Only physical tests on known devices establish actual call success. The maintainer reported working voice, video and screen sharing with 0.3.0 on iPhone 7 (iOS 15.8.8) and with 0.3.1 on a newer iPhone (OS/model not recorded). The repository's tests do not prove universal network compatibility.

See [the architecture description](ARCHITECTURE.md) and [third-party notices](../THIRD_PARTY_NOTICES.md) before changing how network packets or licensed components are handled.
