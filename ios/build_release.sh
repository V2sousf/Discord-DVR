#!/usr/bin/env bash
# Build only the open-source adaptation. Never downloads Discord or the upstream packet.
set -euo pipefail
mkdir -p build/vendor build/release
fishhook_commit=aadc161ac3b80db07a9908851839a17ba63a9eb1
for file in fishhook.c fishhook.h LICENSE; do
  curl --fail --location --retry 2 --proto '=https' --proto-redir '=https' --max-time 60 \
    "https://raw.githubusercontent.com/facebook/fishhook/$fishhook_commit/$file" -o "build/vendor/$file"
done
cp build/vendor/LICENSE build/release/fishhook-LICENSE.txt
clang -fobjc-arc -fblocks -Wall -Wextra -Werror -I ios -I build/vendor \
  ios/ReleaseTests.m -framework Foundation -framework Security -o build/release-tests
build/release-tests 2>&1 | tee build/release/network-test.txt
clang -fobjc-arc -fblocks -Wall -Wextra -Werror -I ios ios/DAVEKeychainTests.m \
  -framework Foundation -framework Security -o build/dave-keychain-tests
build/dave-keychain-tests 2>&1 | tee build/release/dave-keychain-test.txt
python3 ios/ReleaseSourceTests.py 2>&1 | tee build/release/release-source-test.txt
python3 ios/PackagingTests.py 2>&1 | tee build/release/packaging-test.txt
sdk=$(xcrun --sdk iphoneos --show-sdk-path)
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$sdk" -miphoneos-version-min=15.1 \
  -dynamiclib -fobjc-arc -fblocks -O2 -Wall -Wextra -Werror \
  -I ios -I build/vendor ios/DiscordDVR.m build/vendor/fishhook.c \
  -framework Foundation -framework Security \
  -Wl,-install_name,@rpath/DiscordDVR.dylib -o build/release/DiscordDVR.dylib \
  2>&1 | tee build/release/compile-log.txt
xcrun strip -x build/release/DiscordDVR.dylib
xcrun lipo -archs build/release/DiscordDVR.dylib | tee build/release/architecture.txt
xcrun otool -l build/release/DiscordDVR.dylib > build/release/dylib-load-commands.txt
xcrun nm -u build/release/DiscordDVR.dylib > build/release/dylib-imports.txt
if grep -E '_NSLog|_fopen|_fwrite|_recvmsg|_recvfrom|_AVAudioSession|_UIApplication|_UIButton|_DTControlEmit|_DTSession' build/release/dylib-imports.txt; then
  echo 'Diagnostic API unexpectedly imported by release' >&2
  exit 1
fi
cp ios/prepare_ipa.py ios/verify_package.py ios/README.md build/release/
for notice in LICENSE THIRD_PARTY_NOTICES.md; do
  if test -f "$notice"; then cp "$notice" build/release/; fi
done
shasum -a 256 ios/*.m ios/*.h ios/*.inc ios/*.py ios/*.sh ios/*.md > build/release/source-SHA256SUMS.txt
shasum -a 256 build/release/DiscordDVR.dylib > build/release/library-SHA256SUMS.txt
