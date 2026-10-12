# Contributing

Work on source code that you have the right to share. Keep Discord's proprietary app binaries, upstream Drover packet, private IPA artifacts, signing credentials, personal emails, and user logs out of pull requests.

1. Open an issue describing the observed behavior, the Discord DVR version, iPhone model, iOS version, and network type.
2. Create a branch with one focused change.
3. Preserve the tested UDP prelude order and the unchanged original send unless the change explicitly addresses compatibility.
4. Run the tests with `bash ios/build_release.sh` on macOS. Include test results and any physical-device verification in the pull request.
5. Preserve notices for third-party dependencies and explain the source/permission status of new assets.
6. Use a GitHub-provided private `noreply` commit email if you want to keep your personal email out of Git history.

Do not include user audio, call screenshots, access tokens, Apple IDs, or private debugging files. For security issues, follow [SECURITY.md](SECURITY.md).

The project may use AI-assisted tools in development. Review generated code and verify provenance and behavior before contributing it.
