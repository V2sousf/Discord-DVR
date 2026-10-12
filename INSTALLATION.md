# Install Discord DVR on iPhone

Download [Discord DVR 0.3.1 IPA](https://github.com/V2sousf/Discord-DVR/releases/download/v0.3.1/Discord-DVR-0.3.1-260.0.ipa), or find it in [Release v0.3.1](https://github.com/V2sousf/Discord-DVR/releases/tag/v0.3.1) under **Assets**. Choose `Discord-DVR-0.3.1-260.0.ipa`; do not select **Source code (zip)**.

**SHA-256:** `dda1a637d48eea5f67364e6132e3a2faadedf3c8820d97a235ee517639e3a051`

## Requirements

- An iPhone compatible with the specific build you intend to install.
- A USB cable and a computer running Windows or macOS.
- [Sideloadly](https://sideloadly.io/) and its required Apple components.
- Your own Apple ID for device-specific signing.

## Installation

1. Download `Discord-DVR-0.3.1-260.0.ipa` from the release page to your computer.
2. Start Sideloadly and connect your unlocked iPhone using USB.
3. Approve **Trust This Computer** if the iPhone displays the prompt. Check that Sideloadly has selected the intended device.
4. Drag the IPA into Sideloadly. Do not add extra tweaks to the build; the release library is already included.
5. Sign in using your own Apple ID **inside Sideloadly**, then press **Start**. Wait for installation to complete.
6. If iOS displays **Untrusted Developer**, open **Settings → General → VPN & Device Management** and trust the profile matching the Apple ID used to sign the app.
7. If using iOS 16+, open **Settings → Privacy & Security → Developer Mode** when required. Enable it, restart, and confirm **Turn On**.
8. Launch Discord DVR and grant any requested microphone and camera permissions. Version 0.3.1 applies the DVR behavior automatically; there is no activation button.
9. Test both directions of a voice call, followed by camera video and screen sharing. Ask the other participant to confirm what they actually receive.

## Refresh the signature

A free Apple ID signing profile normally lasts **seven days**. Re-sign the app before expiry using Sideloadly. When supported, install over the existing app using the same Apple account and bundle identifier to avoid unnecessary loss of local data. Avoid deleting the app to refresh its signature.

## Troubleshooting

- **Sideloadly does not detect the iPhone:** Unlock the device, accept the trust prompt, try another USB cable, and follow Sideloadly's Apple-component setup instructions.
- **The app is blocked by Developer Mode:** Follow step 7. Developer Mode is a device setting, not a permission to use another person's Apple account.
- **The app stopped opening days later:** Check the signing profile's expiry and re-sign.
- **Voice, camera, or sharing fails:** Report the DVR version, iPhone model, iOS version, network type, and which direction failed. Do not post personal account details, tokens, raw logs, or call content.

Review the [Sideloadly FAQ](https://sideloadly.io/faq.html) for signing requirements. A sideloaded client is unofficial and may be subject to Discord's account policies.
