# PES 2018 Recomp - Tuned 60 FPS + OTG PS2 Bridge

Catatan kerja untuk build **tuned** PES 2018 recomp (Android) dengan fokus:
- stabil **60 FPS** di device low/mid,
- perbaikan dialog **"ANOTHER PATCH OPERATION IS RUNNING..."**,
- dukungan **2 stik PS2 via OTG USB converter** (`Twin USB Joystick`, VID/PID `0810:0001`) agar terbaca sebagai gamepad Android normal.

> Repo ini **tidak menyertakan APK game, data game, atau keystore**. Semua itu harus disiapkan lokal.

## Status yang sudah diverifikasi

| Area | Status | Catatan |
|---|---|---|
| Tuned build 60 FPS | OK | Package terpisah `com.pes2018.recomp.rc2.fps60`, original tetap utuh |
| FPS dalam pertandingan | OK | MSAA di-force OFF + scene scale 0.75; median 57 FPS (dulu 21). Sisa hitch kickoff dari upload tekstur — lihat [docs/PERFORMANCE-FIX.md](docs/PERFORMANCE-FIX.md) |
| Dialog patch lock | OK | `LS/H0;->u(Lf/j;)Z` dipaksa return false pada APK tuned; folder data game tidak disentuh |
| OTG 1 stik | OK | Tombol aksi tidak lagi bocor ke launcher setelah `EVIOCGRAB` |
| OTG 2 stik (P1/P2) | OK | Bridge membuat `PES Tuned Gamepad P1` dan `P2` terpisah; game melihat slot berbeda |

## Struktur

```text
apk/
  pes17-60.xml              # prefs tuned
  patches/
    patch_rc2_60.py         # patch smali untuk 60 FPS, grafis, OTG map, patch-lock fix
otg/
  otg_bridge.c              # jembatan raw HID -> uinput Xbox 360 virtual pad
  start_otg.sh              # rebuild/push/restart bridge via ADB
tools/
  align_apk.py
  debug_key.py              # eksperimen logging key; jangan dipakai untuk build final (VerifyError)
  run_ab.sh                 # A/B otomatis: macro -> MatchIdle -> statistik telemetri
docs/
  FINDINGS.md
  PERFORMANCE-FIX.md        # diagnosis + A/B + verifikasi perbaikan FPS
  OTG.md
```

## Build tuned APK (ringkas)

Prereq: `apktool`, `python`, `zipalign`/script align, `apksigner`, `adb`, Java/Android build tools sesuai lingkungan.

1. Ambil base `rc2.apk` dari upstream:
   - `https://github.com/sharifhidayatulloh/pes2018-recomp` release `0.3.2-rc2`
   - SHA-256 yang dipakai: `1af9ba3f6aba09e3f89c330e9ee1bb0760ba7c22134316c6ff55b4b6c85b1163`
2. Decode:
   ```sh
   apktool d rc2.apk -o rc2_60_out -f
   ```
3. Patch:
   ```sh
   python apk/patches/patch_rc2_60.py
   ```
4. Build/sign dengan **keystore lokal terpisah** (jangan pakai key original). Pasang sebagai package terpisah, debuggable.
5. Install:
   ```sh
   adb install -r rc2-tuned-60fps-otg-fix.apk
   ```

## Profil tuned final

- `fpsLimit=60`, `prefer60Hz=false`
- `sceneScale=0.75` — **di-force di smali**, mengabaikan pref UI
- `multisampling=false` → `PES17_NO_MSAA=1` — **di-force di smali**; MSAA ON adalah penyebab utama drop di match
- `crowd=false`, `fsr=false`, `frameGeneration=false` (stability profile)
- Native: `PES17_FORCE_LEGACY_RENDERING=1` dan `PES17_FORCE_BC_DECOMPRESS=1` **dipertahankan** (A/B: lebih cepat daripada dynamic rendering di Mali-G615)
- Native: `PES17_NO_DISPLAY_TABLE=1` **ditolak**; jangan pakai.
- Native: `PES17_FIRSTDRAW_SYNC=1` **ditolak**; jangan pakai.

## OTG bridge

Lihat [docs/OTG.md](docs/OTG.md).

Quick start:
```sh
cd otg
ADB_TARGET=IP:PORT ./start_otg.sh
```

## Batasan diketahui

- Menu/pause text bug: **ditunda**.
- Upstream rc2 goal replay crash: belum difix.
- `debug_key.py` menghasilkan `VerifyError` saat dipakai di `GameActivity.dispatchKeyEvent`; hanya eksperimen.
- Tanpa Magisk/root, start bridge setelah reboot butuh ADB sekali (lihat docs).

## Lisensi / atribusi

- Upstream project: [sharifhidayatulloh/pes2018-recomp](https://github.com/sharifhidayatulloh/pes2018-recomp).
- Repo ini hanya berisi script/patch/catatan kerja tuning & OTG bridge.
