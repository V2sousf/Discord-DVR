# Discord DVR

An unofficial iOS adaptation of [Drover](https://github.com/hdrover/discord-drover) for Discord voice calls, video calls, and screen sharing on restricted networks. Version 0.3.1 runs automatically; there is no switch to enable.

## 1. Download the IPA

**Public IPA: Not available yet.** The [Releases page](https://github.com/V2sousf/Discord-DVR/releases) currently has no downloadable app. Do not select **Source code (zip)**; source archives cannot be installed on an iPhone.

**Private 0.3.1 test build (repository access required):** Open the [successful GitHub Actions run](https://github.com/V2sousf/Drover-ios-research/actions/runs/38256674504), scroll to **Artifacts**, and download `discord-dvr-private-test-0.3.1`. Extract the ZIP and use `Discord-DVR-0.3.1-260.0.ipa`. GitHub may remove temporary artifacts after their retention period.

If a public IPA release is authorized in the future, download its `.ipa` attachment from **Releases** and follow the steps below.

## 2. Install the IPA with Sideloadly

1. Download and install [Sideloadly](https://sideloadly.io/) on a **Windows PC or Mac**. Install any Apple components it requests.
2. Connect the iPhone using a USB cable, unlock it, and select **Trust This Computer** if prompted.
3. Open Sideloadly. Choose your iPhone and drag the `.ipa` file into the window.
4. Enter **your own Apple ID in Sideloadly** and click **Start**. Complete any verification prompts. Do not send your password or verification code to anyone.
5. Wait for Sideloadly to finish installing Discord DVR.

No jailbreak or source-code compilation is required to install an existing IPA.

## 3. Allow the app to open

- **Untrusted Developer:** On the iPhone, open **Settings → General → VPN & Device Management** and trust the profile associated with the Apple ID used for signing.
- **Developer Mode Required (iOS 16+):** Open **Settings → Privacy & Security → Developer Mode**, turn it on, restart the iPhone, and confirm **Turn On**.
- Open **Discord DVR**. Sign in and grant microphone/camera permissions when prompted. **Do not look for a Drover button:** the 0.3.1 release build enables the adaptation automatically.

## 4. Test it

Start a voice call and confirm that **both people can hear each other**. Then test the camera and screen sharing. A speaking indicator is not proof that audio reached the other person.

**Important:** Free Apple ID signing typically expires after **7 days**. Refresh or re-sign the app using Sideloadly to keep it working. Use the same signing account when refreshing an existing installation where possible.

For installation errors, read [the troubleshooting guide](INSTALLATION.md).

## Tested devices

| Version | Reported result |
| --- | --- |
| 0.3.0 | Voice, camera, and screen sharing worked on **iPhone 7 / iOS 15.8.8** in the UAE. |
| 0.3.1 | Voice, camera, and screen sharing worked on a **newer iPhone**. The exact model and iOS version were not recorded. |

These are maintainer-reported device tests, not a guarantee for every iPhone or Discord version. The code targets ARM64 and iOS 15.1 or later.

## Source code and credits

The [`ios/` directory](ios/) contains the iOS adaptation, tests, and build tools. To compile the standalone library on macOS with Xcode, follow [the build instructions](docs/BUILDING.md).

The port was developed from the publicly documented behavior of [Windows Drover](https://github.com/hdrover/discord-drover) with AI-assisted tools, including OpenAI Codex. Credit also goes to [fishhook](https://github.com/facebook/fishhook) and the Bunny/Vendetta contributors associated with the historical test base.

This project is not affiliated with or endorsed by Discord. Using a modified client may carry security and account-policy risks. The repository's MIT license covers only its original contributions; it does not provide permission to redistribute Discord's client or the upstream Drover packet. See [third-party notices](THIRD_PARTY_NOTICES.md).

[Report an issue](https://github.com/V2sousf/Discord-DVR/issues) without posting Apple account credentials, private logs, or call content.
