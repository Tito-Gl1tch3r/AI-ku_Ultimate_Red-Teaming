#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
BUILD_DIR="${SCRIPT_DIR}/build"
KEYSTORE="${BUILD_DIR}/debug.keystore"

if [[ -z "$SDK_ROOT" || ! -d "$SDK_ROOT" ]]; then
  echo "set ANDROID_SDK_ROOT or ANDROID_HOME to an installed Android SDK" >&2
  exit 1
fi

find_sdk_file() {
  local name="$1"
  find "$SDK_ROOT" -maxdepth 4 -type f -name "$name" -print | sort -V | tail -n 1
}

ANDROID_JAR="${ANDROID_JAR:-$(find_sdk_file android.jar)}"
AAPT2="${AAPT2:-$(find_sdk_file aapt2)}"
D8="${D8:-$(find_sdk_file d8)}"
APKSIGNER="${APKSIGNER:-$(find_sdk_file apksigner)}"
ZIPALIGN="${ZIPALIGN:-$(find_sdk_file zipalign)}"

for required in "$ANDROID_JAR" "$AAPT2" "$D8" "$APKSIGNER"; do
  if [[ ! -f "$required" ]]; then
    echo "missing required Android build tool: $required" >&2
    exit 1
  fi
done

mkdir -p "$BUILD_DIR/outputs"

if [[ ! -f "$KEYSTORE" ]]; then
  keytool -genkeypair -noprompt \
    -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias androiddebugkey -dname "CN=Mobile Trust Lab,O=TAKU-ZE,C=JP" \
    -keyalg RSA -keysize 2048 -validity 10000 >/dev/null
fi

build_variant() {
  local variant="$1"
  local variant_dir="$BUILD_DIR/$variant"
  local classes_dir="$variant_dir/classes"
  local dex_dir="$variant_dir/dex"
  local unsigned_apk="$variant_dir/${variant}-unsigned.apk"
  local aligned_apk="$variant_dir/${variant}-aligned.apk"
  local output_apk="$BUILD_DIR/outputs/mobile-trust-lab-${variant}.apk"

  mkdir -p "$classes_dir" "$dex_dir"
  find "$classes_dir" "$dex_dir" -type f -delete

  mapfile -t sources < <(find "$SCRIPT_DIR/common/java" "$SCRIPT_DIR/$variant/java" -name '*.java' -type f | sort)
  javac -source 8 -target 8 -bootclasspath "$ANDROID_JAR" -d "$classes_dir" "${sources[@]}"
  mapfile -t class_files < <(find "$classes_dir" -name '*.class' -type f | sort)
  "$D8" --lib "$ANDROID_JAR" --min-api 23 --output "$dex_dir" "${class_files[@]}"
  "$AAPT2" link -I "$ANDROID_JAR" --manifest "$SCRIPT_DIR/$variant/AndroidManifest.xml" -o "$unsigned_apk"
  jar uf "$unsigned_apk" -C "$dex_dir" classes.dex

  local sign_input="$unsigned_apk"
  if [[ -x "$ZIPALIGN" ]]; then
    "$ZIPALIGN" -f 4 "$unsigned_apk" "$aligned_apk"
    sign_input="$aligned_apk"
  fi

  "$APKSIGNER" sign \
    --ks "$KEYSTORE" --ks-key-alias androiddebugkey \
    --ks-pass pass:android --key-pass pass:android \
    --out "$output_apk" "$sign_input"
  "$APKSIGNER" verify --verbose "$output_apk"
  echo "built $output_apk"
}

build_variant vulnerable
build_variant hardened
