#!/usr/bin/env bash
set -euo pipefail
# Run on Ubuntu 24.04 or WSL2 Ubuntu, not in PowerShell or Pydroid 3.
cd "$(dirname "$0")"
if ! command -v buildozer >/dev/null 2>&1; then
  echo "Missing Buildozer. Install according to BUILD_APK_README.md" >&2
  exit 1
fi
buildozer -v android debug
printf 'APK output: %s/bin/\n' "$PWD"
ls -lh bin/*.apk
