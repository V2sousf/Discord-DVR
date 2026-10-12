# Security

Discord DVR is an unofficial modification of the Discord iOS client. Do not treat its source code, an IPA, or an automated build result as proof that the client is safe. Use your own judgment when installing unofficial applications.

## Report a vulnerability

Use GitHub's **Security → Report a vulnerability** for this repository if private reporting is enabled. If it is unavailable, open a regular issue that asks for a private reporting channel **without including confidential details**.

Never post Apple ID credentials, authorization tokens, private keys, provisioning profiles, user media, or raw network logs in issues or pull requests.

## Privacy notes

The 0.3.1 release-mode library does not add its own network telemetry endpoint, continuous logging, packet capture, or diagnostic UI. This statement does not describe or guarantee the behavior of Discord, Sideloadly, the operating system, or other installed tweaks.

Installers must sign the app using their own Apple ID through their chosen signing tool. Do not publish personally signed IPAs, provisioning profiles, or screenshots revealing the email address used for signing.

See [docs/PRIVACY.md](docs/PRIVACY.md) for details and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party code boundaries.
