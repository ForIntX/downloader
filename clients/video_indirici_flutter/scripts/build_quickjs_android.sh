#!/usr/bin/env bash
set -euo pipefail

# QuickJS-NG yalnız geliştirici tarafından yeni APK/AAB hazırlanırken yenilenir.
# Uygulama çalışma zamanında kod veya çalıştırılabilir bileşen indirmez.
readonly QJS_TAG="v0.15.0"
readonly QJS_COMMIT="433941b99fb3c5e7f98b7ebd78727972bcf467ee"
readonly NDK_VERSION="28.2.13676358"
readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly BUILD_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "${BUILD_ROOT}"
}
trap cleanup EXIT

if [[ -z "${ANDROID_SDK_ROOT:-}" ]]; then
  echo "ANDROID_SDK_ROOT tanımlı değil." >&2
  exit 1
fi

readonly NDK_ROOT="${ANDROID_SDK_ROOT}/ndk/${NDK_VERSION}"
readonly TOOLCHAIN="${NDK_ROOT}/build/cmake/android.toolchain.cmake"
readonly STRIP="${NDK_ROOT}/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"

git clone --depth 1 --branch "${QJS_TAG}" \
  https://github.com/quickjs-ng/quickjs.git "${BUILD_ROOT}/quickjs"
test "$(git -C "${BUILD_ROOT}/quickjs" rev-parse HEAD)" = "${QJS_COMMIT}"

build_abi() {
  local abi="$1"
  local build_dir="${BUILD_ROOT}/build-${abi}"
  local destination="${PROJECT_DIR}/android/app/src/main/jniLibs/${abi}/libqjs.so"
  cmake -S "${BUILD_ROOT}/quickjs" -B "${build_dir}" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="${TOOLCHAIN}" \
    -DANDROID_ABI="${abi}" \
    -DANDROID_PLATFORM=26 \
    -DCMAKE_BUILD_TYPE=Release \
    -DQJS_ENABLE_INSTALL=OFF \
    -DQJS_BUILD_EXAMPLES=OFF
  cmake --build "${build_dir}" --target qjs_exe --parallel
  mkdir -p "$(dirname "${destination}")"
  "${STRIP}" --strip-unneeded -o "${destination}" "${build_dir}/qjs"
  chmod 755 "${destination}"
}

build_abi arm64-v8a
build_abi x86_64
sha256sum \
  "${PROJECT_DIR}/android/app/src/main/jniLibs/arm64-v8a/libqjs.so" \
  "${PROJECT_DIR}/android/app/src/main/jniLibs/x86_64/libqjs.so"
