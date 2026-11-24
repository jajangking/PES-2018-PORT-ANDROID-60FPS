# Temuan

## Device uji

- TECNO LJ8k, Android 16/API 36, arm64-v8a
- GPU Mali-G615 MC2
- Game data: `/sdcard/Download/PES 2018 PT-BR` (jangan disentuh/duplikat)
- Original package tetap terpasang: `com.pes2018.recomp`
- Tuned package: `com.pes2018.recomp.rc2.fps60`

## Base build

- Upstream: `sharifhidayatulloh/pes2018-recomp` release `0.3.2-rc2`
- File: `rc2.apk`
- SHA-256: `1af9ba3f6aba09e3f89c330e9ee1bb0760ba7c22134316c6ff55b4b6c85b1163`

## Performa/grafis

| Profil | Hasil | Keputusan |
|---|---:|---|
| 120 FPS | Tidak stabil / ditolak user | Rollback ke 60 |
| `PES17_NO_DISPLAY_TABLE=1` | Ditolak | Jangan pakai |
| `PES17_FIRSTDRAW_SYNC=1` | Ditolak | Jangan pakai |
| Scene scale 100% | p95 kickoff ~40885 us, jank20 41 | Penyebab jank kickoff |
| Scene scale 85%, hint pipeline, MSAA ON | p95 kickoff ~20428 us, jank20 34 | **Dipakai** |

Stabil steady-state: ~59.2–59.9 FPS, GPU wait ~0.00 ms.

## Patch-lock dialog

Gejala: dialog `ANOTHER PATCH OPERATION IS RUNNING. WAIT FOR IT TO FINISH.`

Root cause: `LS/H0;->u(Lf/j;)Z` menganggap `.patch-install.lock` / `patch-journal.properties` di folder game sebagai operasi patch aktif.

Fix: pada APK tuned, method itu dipaksa return `false`. **Tidak ada file lock di folder data game yang dihapus**.

## OTG PS2 converter

Device: `Twin USB Joystick`, VID/PID `0810:0001`, 2 node input (`eventX/Y`).

Masalah awal:
- D-pad kadang terbaca, tapi tombol aksi (`BTN_JOYSTICK/BTN_THUMB/...`) bocor ke Android UI/launcher.
- App-level remap di `dispatchKeyEvent` tidak cukup karena event tidak sampai sebagai key Android standar.

Solusi:
1. Baca raw `/dev/input/event*` untuk device target.
2. `EVIOCGRAB` node fisik agar event tidak jatuh ke sistem.
3. Buat virtual gamepad uinput dengan identitas Xbox 360 (`045e:028e`, keylayout `Vendor_045e_Product_028e.kl`).
4. Emit `EV_KEY/EV_ABS/SYN_REPORT` yang normal.

Hasil: 2 stik fisik -> `PES Tuned Gamepad P1/P2`, slot terpisah di game.

## Hal yang jangan diulang

- Jangan pakai debug key logging di `dispatchKeyEvent` untuk build final; pernah `VerifyError`.
- Jangan sentuh package/data original.
- Jangan duplikat folder game data.
- Jangan pakai opsi display table/sync draw yang sudah ditolak.