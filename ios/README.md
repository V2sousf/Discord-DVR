# iOS source

`DiscordDVR.m` implements the 0.3.1 always-on adaptation. It uses app-local fishhook bindings, not a VPN or system-wide network hook.

On the first eligible outgoing UDP `sendto` or `sendmsg` attempt whose first buffer has length 74, the adaptation sends the locally supplied 1200-byte packet, then `00` and `01`, waits about 50 ms, and forwards the original send. Eligibility is tracked per socket; ineligible first attempts are consumed without injecting the prelude. See [the architecture notes](../docs/ARCHITECTURE.md).

The implementation also includes a narrowly scoped DAVE Keychain compatibility retry. It does not disable Discord voice encryption. Release mode includes no diagnostic UI, packet capture, or continuous NDJSON logs.

## Commands

Build and run tests with Xcode on macOS:

```sh
bash ios/build_release.sh
```

To package a local IPA using separately obtained, authorized inputs, follow [docs/BUILDING.md](../docs/BUILDING.md). This directory does not include the Discord client, Drover packet, or a device signing identity.

The maintainer reports two-way voice, video, and screen sharing working in the 0.3.0 baseline on iPhone 7/iOS 15.8.8 and in 0.3.1 on a newer iPhone whose model/OS was not recorded. Do not infer compatibility with every iOS or Discord version.
