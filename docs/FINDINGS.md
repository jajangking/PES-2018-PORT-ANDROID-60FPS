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

Angka ~59 FPS itu **di menu**, bukan di dalam pertandingan. Telemetri pertandingan
(CSV, kolom `in_match`) dengan profil lama (MSAA ON, scale 0.85) menunjukkan
~21–29 FPS dan `gpu_wait_ms` ~850/detik — jadi beban ada di GPU, bukan di panas
(thermal status 0, CPU/GPU ~70 °C) dan bukan di CPU recompiler.

### A/B di TECNO LJ8k (Mali-G615 MC2), macro `intromatch`, 45 detik pertandingan

| Konfigurasi (`env_override`) | FPS median | p50 frame | gpu wait |
|---|---:|---:|---:|
| baseline (MSAA ON, scale 0.85) | 21.5 | ~49 ms | ~850 ms/s |
| `PES17_NO_MSAA=1` | 45.0 | ~20 ms | ~190 ms/s |
| `PES17_NO_MSAA=1` + `PES17_SCENE_SCALE=0.75` | 37–54 | ~18 ms | ~200 ms/s |
| `...` + `PES17_FORCE_LEGACY_RENDERING=` + `PES17_FORCE_BC_DECOMPRESS=` | 39.0 | ~21 ms | ~220 ms/s |

Kesimpulan: **MSAA adalah akar masalahnya.** Legacy rendering dan software BC
decompress yang di-force oleh patch justru lebih cepat, jadi dipertahankan.
Run-to-run bisa beda ±15 FPS tergantung suhu/adegan; gunakan median, bukan satu run.

Perbaikan final ditanam di `apk/patches/patch_rc2_60.py`: `PES17_NO_MSAA=1` dan
`PES17_SCENE_SCALE=0.75` di-force sebelum `nativeSetOption`, jadi tidak perlu
`env_override` lagi.

### Verifikasi build final (tanpa env_override)

APK: `rc2-tuned-60fps-fpsfix.apk` (dibangun ulang dari `rc2.apk` dengan patch
terbaru, keystore `tuned`, terpasang di perangkat 2026-11-24 20:32).

- `# resolved`: `msaa=0, scene_scale=0.75, fps_limit=60`
- pertandingan: **median 57 FPS**, mean 49.8, p50 16.9 ms, gpu wait 224 ms/s
- tidak ada satu pun detik dengan FPS < 15 saat intro/cutscene (sebelumnya 14 detik)

Catatan A/B: jalankan `tools/run_ab.sh` di tmp dengan macro `intromatch` yang
di-push ke `files/macros/`; `env_override` ditulis ke external files dan
didahulukan oleh `perf::ApplyMemoryDefaults` setelah `applyOptions()`.

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