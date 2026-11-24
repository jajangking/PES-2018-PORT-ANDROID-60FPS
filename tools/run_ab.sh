#!/data/data/com.termux/files/usr/bin/bash
# tools/run_ab.sh <label> [PES17_X=value ...]
#
# A state-driven A/B run on the device: launch the tuned app, replay the
# `intromatch` pad macro until Match/MatchIdle, then sample WINDOW seconds of
# telemetry and print the in-match FPS statistics.
#
# Any PES17_* argument is written to files/env_override, which the runtime
# reads after the app's own options (perf::ApplyMemoryDefaults), so it wins
# over the values forced in GameActivity.smali. No arguments = baseline.
#
# Environment:
#   PKG       package to test          (default com.pes2018.recomp.rc2.fps60)
#   MACRO     macro name               (default intromatch)
#   WINDOW    sampling seconds         (default 45)
#   OUT       CSV output directory     (default /tmp/pes2018_ab)
#   ANDROID_SERIAL / adb -s: standard adb device selection applies.
#
# Prereq (once): push the macro from upstream and enable remote control:
#   adb shell mkdir -p /sdcard/Android/data/$PKG/files/macros
#   adb push <upstream>/intromatch.macro /sdcard/Android/data/$PKG/files/macros/
#   adb shell touch /sdcard/Android/data/$PKG/files/macros/.remote_control
#
# Example:
#   tools/run_ab.sh base
#   tools/run_ab.sh nomsaa PES17_NO_MSAA=1
#   tools/run_ab.sh s75 PES17_NO_MSAA=1 PES17_SCENE_SCALE=0.75

set -e
LABEL=${1:?usage: run_ab.sh <label> [PES17_X=value ...]}
shift
PKG=${PKG:-com.pes2018.recomp.rc2.fps60}
ACT=${ACT:-$PKG/com.pes2017.recomp.MainActivity}
MACRO=${MACRO:-intromatch}
WINDOW=${WINDOW:-45}
F=/sdcard/Android/data/$PKG/files
OUT=${OUT:-/tmp/pes2018_ab}
mkdir -p "$OUT"

adb shell "mkdir -p $F/macros"
adb shell "touch $F/macros/.remote_control"
adb shell "rm -f $F/env_override $F/game.log"
if [ $# -gt 0 ]; then
  printf '%s\n' "$@" | adb shell "cat > $F/env_override"
fi

adb shell am force-stop "$PKG"
adb shell am start -n "$ACT" >/dev/null
for i in $(seq 1 90); do
  adb shell "grep -q PreStartup $F/game.log" 2>/dev/null && break
  sleep 1
done
adb shell am broadcast -a com.pes2017.recomp.MACRO -p "$PKG" \
  --es cmd play --es name "$MACRO" >/dev/null
for i in $(seq 1 110); do
  adb shell "grep -q 'Match/MatchIdle' $F/game.log" 2>/dev/null && break
  sleep 1
done
sleep "$WINDOW"
CSV=$OUT/$LABEL.csv
adb shell "run-as $PKG cat files/telemetry.csv" > "$CSV"

python3 - "$LABEL" "$CSV" <<'PY'
import statistics as st
import sys

label, path = sys.argv[1:3]
rows, resolved = [], ''
for line in open(path, errors='replace'):
    if line.startswith('# resolved'):
        resolved = line.strip().replace('# resolved: ', '')
    if line.startswith('#'):
        continue
    rows.append(line.strip().split(','))
if len(rows) < 2:
    print(label, 'NO TELEMETRY ROWS')
    raise SystemExit(1)
idx = {n: k for k, n in enumerate(rows[0])}
match = [r for r in rows[1:] if float(r[idx['in_match']] or 0) > 0]
if not match:
    print(label, 'NO MATCH ROWS (macro did not reach a match)')
    raise SystemExit(1)
print('%s: n=%d fps=%.1f/%.1f (mean/median) p50=%.1fms gpu=%.0fms/s cpu=%.0fms/s thermal=%.1f' % (
    label, len(match),
    st.mean(float(r[idx['frames']]) for r in match),
    st.median(float(r[idx['frames']]) for r in match),
    st.mean(float(r[idx['ft_p50_us']]) for r in match) / 1000,
    st.mean(float(r[idx['gpu_wait_ms']]) for r in match),
    st.mean(float(r[idx['cpu_proc_ms']]) for r in match),
    st.mean(float(r[idx['thermal']] or 0) for r in match)))
print('  ' + resolved)
PY
