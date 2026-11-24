# OTG PS2 Bridge

## Masalah

Converter PS2->USB (`Twin USB Joystick`, `0810:0001`) mengirim tombol sebagai `BTN_*` mentah (mis. `BTN_JOYSTICK` untuk △). Android/game tidak selalu memetakannya sebagai gamepad standar, dan event bisa bocor ke launcher/UI.

## Solusi

`otg/otg_bridge.c`:
- Scan `/dev/input/event0..31`.
- Deteksi device target by VID/PID `0810:0001` atau nama `Twin USB Joystick`.
- `EVIOCGRAB` node fisik: mencegah event bocor ke Android.
- Buat **satu virtual pad per stik fisik** lewat `/dev/uinput`.
- Identitas virtual pad: USB Xbox 360 `045e:028e`, keylayout `Vendor_045e_Product_028e.kl`.
- Nama: `PES Tuned Gamepad P1`, `P2`, ...
- Jika OTG dicabut, bridge tutup source, destroy pad virtual, lalu rescan otomatis.

## Mapping default

| Raw | Virtual |
|---|---|
| `BTN_JOYSTICK` | `BTN_Y` (△) |
| `BTN_THUMB` | `BTN_B` (○) |
| `BTN_THUMB2` | `BTN_A` (✕) |
| `BTN_TOP` | `BTN_X` (□) |
| `BTN_BASE` | `BTN_TL` (L1) |
| `BTN_BASE2` | `BTN_TR` (R1) |
| `BTN_TOP2` | `BTN_TL2` (L2) |
| `BTN_PINKIE` | `BTN_TR2` (R2) |
| `BTN_BASE3` | `BTN_SELECT` |
| `BTN_BASE4` | `BTN_START` |
| `BTN_BASE5` | `BTN_THUMBL` |
| `BTN_BASE6` | `BTN_THUMBR` |

Axis: `ABS_X/Y/Z/RZ/HAT0X/HAT0Y` dipass-through (analog diskala dari 0..255 ke -32768..32767).

## Build & run

```sh
clang -O2 -Wall -Wextra -o otg_bridge otg_bridge.c
adb push otg_bridge /data/local/tmp/otg_bridge
adb shell chmod 755 /data/local/tmp/otg_bridge
adb shell 'pkill -x otg_bridge 2>/dev/null || true; nohup /data/local/tmp/otg_bridge >/data/local/tmp/otg_bridge.log 2>&1 &'
adb shell cat /data/local/tmp/otg_bridge.log
```

Atau pakai script:
```sh
ADB_TARGET=10.x.x.x:PORT ./start_otg.sh
```

Log normal:
```text
created PES Tuned Gamepad P1
PES Tuned Gamepad P1 <- /dev/input/eventX (Twin USB Joystick)
```

## Tanpa ketergantungan Termux

- **Tanpa root**: binary bisa dijalankan via `adb shell`; Termux tidak diperlukan saat main. Setelah reboot butuh start ulang sekali via ADB.
- **Dengan Magisk/root**: pasang script di `/data/adb/service.d/otg-bridge.sh` agar auto-start saat boot.

Contoh Magisk service:
```sh
#!/system/bin/sh
BIN=/data/local/tmp/otg_bridge
LOG=/data/local/tmp/otg_bridge.log
until [ -e /dev/uinput ]; do sleep 1; done
pkill -x otg_bridge 2>/dev/null || true
nohup "$BIN" >"$LOG" 2>&1 &
```

## Kenapa PPSSPP bisa tapi PES recomp ini tidak?

PPSSPP membaca input via API app/gamepad Android dan punya mapping internal. PES 2018 recomp/Winlator path ini lebih sensitif ke bentuk device/key Android standar; converter mentah mengekspos `BTN_*` yang tidak dipetakan dengan benar dan bisa bocor ke UI. Bridge uinput membuat device yang terlihat seperti gamepad biasa oleh sistem.