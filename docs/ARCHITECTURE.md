# Architecture and update boundaries

## Direct core

The Direct mechanism is separate from Discord's UI. It tracks app-created sockets and consumes the first outgoing attempt. On the first eligible UDP `sendto`/`sendmsg` call with a first buffer of 74 bytes, it sends the exact locally supplied packet, `00`, `01`, waits about 50 ms and forwards the original call exactly once with unchanged arguments. A discovery-header match and total-iovec length are not prerequisites. Other send forms consume the first attempt without a prelude, matching the relevant Windows behavior.

The preserved successful configuration includes the 1200-byte packet. Its hash is checked during private packaging. Missing that input is not presented as equivalent to the working baseline.

The Windows DLL's loading and x86/x64 DDetours hooks cannot be copied literally to an unjailbroken iPhone. The iOS equivalent uses an embedded signed Mach-O library and fishhook symbol rebinding in app-owned images. It does not inject into another process, intercept system-wide traffic, rewrite DNS or set a TCP proxy. Direct syscalls, another network API or a future client implementation may evade these bindings.

## Release and debug

The release library starts from its constructor before application network use and applies Direct automatically. It does not read the diagnostic mode preference or require a user action. It contains no diagnostic panel, NDJSON writer, packet capture, voice-frame observer or AVAudioSession observer. Removing observers does not add audio-session setters or change Discord's encryption.

Diagnostic builds and investigation files remain in the private development repository. User logs must not be included in public source, releases or CI artifacts.

## DAVE Keychain compatibility

Retained Security.framework hooks call the original function first. A retry is allowed only when the query is recognized as DAVE-specific, the returned status is `errSecMissingEntitlement`, and an explicit access group is present. A copied query omits only that inaccessible group so the legitimate signed app's default private group can be used. Key algorithm, persistence, accessibility, original dictionaries and unrelated account operations remain unchanged. This does not disable DAVE/MLS, encryption or keychain authorization.

The successful baseline includes this conditional repair, but the historical logs did not prove it was the cause of failure. Keep it narrowly scoped rather than claiming a diagnosed universal Keychain problem.

## Updating the supported client

Treat a Discord update as a new compatibility target. Record input hash, source provenance, ARM64 slices, minimum OS, network/Security import changes and signing assumptions. Run the UDP and Keychain tests, check actual binding coverage in a private debug build if needed, then test audio, camera and screen sharing on a real device. A successful old client test cannot prove future compatibility.

Keep the previous working private artifact and manifest. Publish new compatibility claims only with their device/OS/client evidence and cleared distribution rights.
