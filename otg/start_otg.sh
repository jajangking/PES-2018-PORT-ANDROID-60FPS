#!/data/data/com.termux/files/usr/bin/bash
# Rebuild, push, and restart the PES OTG uinput bridge.
# Usage:
#   ./start_otg.sh                       # uses current adb device or default IP
#   ADB_TARGET=10.x.x.x:PORT ./start_otg.sh
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/otg_bridge.c"
BIN="$DIR/otg_bridge"
REMOTE=/data/local/tmp/otg_bridge
LOG=${REMOTE}.log
DEFAULT_TARGET=${ADB_TARGET:-127.0.0.1:5555}

have_device() {
    adb devices | awk 'NR > 1 && $2 == "device" { found = 1 } END { exit !found }'
}

if ! have_device; then
    target="$DEFAULT_TARGET"
    echo "No adb device; connecting to $target"
    adb connect "$target" >/dev/null
fi

if ! have_device; then
    echo "adb device not ready. Set ADB_TARGET=IP:PORT and retry." >&2
    exit 1
fi

clang -O2 -Wall -Wextra -o "$BIN" "$SRC"
adb push "$BIN" "$REMOTE"
adb shell chmod 755 "$REMOTE"

adb shell 'pkill -x otg_bridge 2>/dev/null || true'
sleep 1
adb shell "nohup $REMOTE >$LOG 2>&1 &"
sleep 3

echo "--- bridge log ---"
adb shell cat "$LOG"
echo "--- bridge process ---"
adb shell "ps -A | grep '[o]tg_bridge' || true"
