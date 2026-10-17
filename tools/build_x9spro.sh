#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${JAVA_HOME:?Set JAVA_HOME to JDK 21 or newer}"
: "${ANDROID_HOME:?Set ANDROID_HOME to SDK 37}"
MUSE_PYTHON=${MUSE_PYTHON:-python3}
export GRADLE_USER_HOME=${GRADLE_USER_HOME:-$PWD/tools/gradle-home}
export MUSE_BUILD_DIR=${MUSE_BUILD_DIR:-/private/tmp/omnicam-muse-x9spro-build}
if [ -f evidence/signing.env ] && [ -z "${OMNICAM_STORE_PASSWORD:-}" ]; then
    set -a
    . ./evidence/signing.env
    set +a
fi
"$MUSE_PYTHON" tools/prepare_x9spro.py
"$MUSE_PYTHON" tools/verify_x9spro.py
"$MUSE_PYTHON" tools/mastercolor/check_catalog.py
sh tools/gradle_port.sh --no-daemon "-PmuseBuildDir=$MUSE_BUILD_DIR" :app:assembleRelease :app:lintRelease --console=plain
"$MUSE_PYTHON" tools/run_offline_tests.py
"$MUSE_PYTHON" tools/package_x9spro.py
