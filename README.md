# Discord DVR

Discord DVR is an unofficial iOS adaptation of [Drover for Windows](https://github.com/hdrover/discord-drover). It runs an app-local library inside a modified Discord iOS client and sends a short UDP setup sequence before an eligible voice connection attempt. It is not a VPN and does not change traffic outside the app.

This repository contains the port's source code, tests, and build instructions. **It does not contain a downloadable Discord IPA.** There is no public, authorized full-IPA release at this time.

## Install on an iPhone

Use an IPA you are authorized to obtain and install. If a public download becomes available, check the [Releases page](https://github.com/V2sousf/Discord-DVR/releases). Do not download GitHub's **Source code (zip)** expecting an installable app.

1. Download the `.ipa` file to a Windows or macOS computer. Extract it first if it is inside a ZIP file.
2. Install [Sideloadly](https://sideloadly.io/) and any Apple components it requests.
3. Connect the unlocked iPhone to the computer with a USB cable and tap **Trust** if iOS asks whether to trust the computer.
4. Open Sideloadly. Select the iPhone and drag the IPA into the application.
5. Enter **your own Apple ID** into Sideloadly, then press **Start**. Complete any Apple verification prompts in Sideloadly.
6. If iOS blocks the app as an untrusted developer, open **Settings → General → VPN & Device Management**, select your signing profile, and trust it.
7. On iOS 16 or later, enable **Settings → Privacy & Security → Developer Mode** if requested. Restart the phone and confirm the setting.
8. Open Discord DVR, grant microphone/camera permissions as needed, and test a voice call in both directions. Test video and screen sharing separately.

No jailbreak is needed for this sideloading method. No in-app Drover switch is required in version 0.3.1; the adaptation runs automatically.

**Free Apple ID signing generally expires after seven days.** Renew the installation with Sideloadly to keep opening the app. Do not share your Apple password, verification codes, signing certificates, or provisioning profiles with this project.

See [INSTALLATION.md](INSTALLATION.md) for troubleshooting and more information.

## Confirmed tests

| Version | Result |
| --- | --- |
| 0.3.0 | The maintainer reported working two-way voice, video, and screen sharing on iPhone 7 / iOS 15.8.8 in the UAE. |
| 0.3.1 | The maintainer reported working voice, video, and screen sharing on a newer iPhone; the exact model and iOS version were not recorded. The private GitHub Actions build and package checks also passed. |

The code targets ARM64 and iOS 15.1 or later. This build target does **not** establish that all iPhones, iOS versions, Discord releases, or networks work. Discord updates may require changes to this adaptation.

## Build from source

- Run `bash ios/build_release.sh` on macOS with Xcode to build and test the standalone DVR library.
- Read [docs/BUILDING.md](docs/BUILDING.md) before preparing a local IPA.
- Read [ios/README.md](ios/README.md) for the network hook behavior and source layout.
- Report reproducible problems through [Issues](https://github.com/V2sousf/Discord-DVR/issues). Do not attach credentials, media, or private network logs.

The source build does not produce an installable Discord client. Local packaging requires separately obtained compatible inputs and appropriate authorization.

## Credits, licensing, and limitations

Credit the original [Drover project](https://github.com/hdrover/discord-drover), [fishhook](https://github.com/facebook/fishhook), and Bunny/Vendetta contributors associated with the historical test base. The iOS port was developed with AI-assisted tools, including OpenAI Codex, and tested by the maintainer.

Discord DVR is not affiliated with or endorsed by Discord. Using an unofficial modified client can pose security and account-policy risks.

The MIT license applies only to the original work in this repository. It does not grant rights to Discord's client, the upstream Drover packet, or other third-party components. Do not redistribute those files without the necessary permissions. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [SECURITY.md](SECURITY.md).
