# Changelog

## 0.3.1

- Rename the iOS adaptation to Discord DVR.
- Start the Direct behavior automatically; remove the Drover toggle and diagnostic interface from the release library.
- Preserve the tested UDP prelude sequence and the scoped DAVE Keychain compatibility retry.
- Separate release source, tests, build tools, and third-party notices from private IPA inputs.
- Correct ad-hoc signature verification for signed nested libraries with no entitlement blob.
- Build and package checks passed in private GitHub Actions.
- The maintainer reported that two-way voice, camera, and screen sharing worked on a newer iPhone; its exact model and iOS version were not recorded.

## 0.3.0

- Add the exact original 1200-byte upstream packet before `00`, `01`, approximately 50 ms, then the original send.
- Match the Windows reference's first outgoing socket-attempt behavior.
- Add the narrow DAVE Keychain signing compatibility retry.
- The maintainer reported working voice, video, and screen sharing on iPhone 7 / iOS 15.8.8 in the UAE.

Previous diagnostic builds remain in the private development repository rather than this clean source tree.
