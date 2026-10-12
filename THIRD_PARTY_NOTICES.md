# Third-party notices and license boundaries

Reviewed on 2026-10-12. This inventory distinguishes our source from inputs used in private compatibility tests. A local build is not evidence of redistribution permission.

## Original Discord DVR contributions

The root MIT license covers original source, documentation, tests and build tools authored for Discord DVR. It does not relicense Discord, Bunny, Windows Drover, Apple's SDKs or upstream packet bytes. Changes incorporating another project's expression must retain its license and be reviewed before publication.

## Windows Drover — reference mechanism and packet

- Project: <https://github.com/hdrover/discord-drover>
- Reviewed revision: `f9e7131241d550bd2874c5e098d41bbc24494d1e`.
- Release inspected: `v0.9`.
- Exact `dist/drover-packet.bin`: 1200 bytes; SHA-256 `f4589c57749f956bb30538197a521d7005f8b0a8723b4707e72405e51ddac50a`.

No repository-level license or specific permission grant was found for `drover.dpr`, `SocketManager.pas`, the installer or this packet in the reviewed revision. Its public presence and inclusion in a release are not a clear license. Original Pascal files and packet bytes are excluded from the public source payload. Obtain permission from the appropriate holder before redistributing either. Private builds accept a separately supplied local packet and verify its exact hash.

The Windows tree includes DDetours/disassembly files with Mozilla Public License 2.0 headers and credits to the [DDetours project](https://github.com/MahdiSafsafi/DDetours). They were reviewed for context, but are not embedded, translated or shipped by the iOS library. Their MPL notice does not apply a blanket license to every other file in Drover. [MPL 2.0](https://www.mozilla.org/MPL/2.0/).

## fishhook — BSD 3-Clause

- Source: <https://github.com/facebook/fishhook>
- Build pin: `aadc161ac3b80db07a9908851839a17ba63a9eb1`.
- Copyright: Facebook, Inc., 2013.
- License: BSD 3-Clause, reproduced in full at [licenses/fishhook-LICENSE.txt](licenses/fishhook-LICENSE.txt).

Builds fetch this pinned source; source notices are preserved. A binary distribution of our DVR library must include the full notice and disclaimer. Facebook and its contributors do not endorse this project.

## BunnyTweak / Vendetta lineage — private test base

- Source: <https://github.com/bunny-mod/BunnyTweak>
- Historically tested package: Bunny/Discord `260.0`, SHA-256 `122306dc80a07370c7ed77588f5fa225c2954c0448a4322549374cd40f1a3136`.

The archived BunnyTweak repository identifies Open Software License 3.0 and explains in its README that an attempted retroactive additional restriction was removed. See its [license](https://github.com/bunny-mod/BunnyTweak/blob/main/LICENSE) and [licensing clarification](https://github.com/bunny-mod/BunnyTweak#important-clarification-regarding-licensing). This is a source-level statement; the exact source-to-binary relationship of every component in the historical IPA has not been established.

Bunny/Vendetta code, JavaScript bundles and compiled tweak libraries are not included in the proposed public source bundle. If redistributed in the future, their applicable licenses, source availability and notices require a separate inventory. Their licenses provide no rights to redistribute the proprietary Discord app enclosed with a release.

## Discord — proprietary client, separate from this project

Discord retains rights to its client, assets and services. The full modified IPA is a private test artifact, excluded from public source and public CI artifacts. No permission to publicly distribute it has been established. The [Discord terms](https://discord.com/terms), section “Software in Discord's services,” grant a personal client license and restrict copying, modification and distribution subject to consent or applicable law. This project's MIT license cannot override those terms or third-party rights.

The name is used to identify compatibility. Discord DVR is an unofficial community project and is not affiliated with or endorsed by Discord. No Discord logo, proprietary client asset or user media is included in this source repository.

## Apple and Sideloadly — external tools

Apple's SDKs, signing services and Sideloadly are not bundled or licensed by this project. Users obtain those tools directly and follow their applicable terms. This repository never supplies an Apple account, a personal certificate, a provisioning profile or an Apple signing bypass.
