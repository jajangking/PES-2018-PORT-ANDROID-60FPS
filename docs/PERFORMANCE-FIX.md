# Perbaikan FPS dalam pertandingan (cutscene stutter + "lock 30")

Status: **selesai**, terverifikasi di perangkat uji 2026-11-24.
Commit: `e0e2fd7`.

## Gejala

- Cutscene/intro pertandingan patah-patah, telemetri mencatat detik dengan 6–13 FPS.
- Begitu pertandingan mulai, FPS stabil di kisaran 21–29 dan terasa seperti di-lock 30.
- Menu tetap ~59–60 FPS, jadi masalahnya bukan pada peluncur atau VSync.

## Diagnosis

Sumber data: `files/telemetry.csv` (satu baris per detik) dan `game.log` dari
package tuned. Perangkat uji: TECNO LJ8k, Android 16, Dimensity 7300 (mt6878),
Mali-G615 MC2, layar aktif 60 Hz.

Yang **bukan** penyebabnya:

- **Bukan thermal throttling.** `Thermal Status: 0`, suhu CPU/GPU ~70 °C, column
  `thermal` di CSV 0. (HUD di layar bisa menunjukkan angka yang lebih tinggi; tetap
  di bawah ambang throttle.)
- **Bukan CPU recompiler.**
  `perf: 0.00 ms a frame waiting for the GPU` dari *ring consumer* menyesatkan;
  yang mengukur jalur kritis adalah `title fence waits` (~30 ms/frame) dan
  kolom `gpu_wait_ms` ~850 ms/detik.
- **Bukan "lock 30".** `fps_limit=60` di `# resolved` telemetri. 30 FPS itu
  hasil dari beban GPU, bukan batas yang disetel.

Yang menjadi penyebab: **MSAA dipaksa ON** oleh profil tuned lama
(`multisampling=true` → `PES17_NO_MSAA=0`) ditambah `sceneScale=0.85`. Di GPU
Mali-G615, MSAA adalah biaya terbesar; upstream `perf.cpp` sendiri menulis
"Multisampling is the single most expensive thing a mobile GPU can be asked for"
dan menjadikan `PES17_NO_MSAA=1` sebagai default Android.

Perhatian: angka "~59.2–59.9 FPS" yang lama di `FINDINGS.md` diukur di **menu**
(kolom `in_match=0`), bukan di pertandingan. Itu yang menyesatkan profil lama.

## A/B (cara mengukur)

Gunakan `tools/run_ab.sh`. Setiap konfigurasi dijalankan ulang dari launch,
macro `intromatch` dari upstream diputar sampai `Match/MatchIdle`, lalu 45 detik
telemetri diambil. `env_override` ditulis ke external files dan dibaca runtime
**setelah** opsi aplikasi, jadi menang atas nilai yang di-force di smali.

```sh
# sekali: siapkan macro dari checkout upstream
adb shell mkdir -p /sdcard/Android/data/com.pes2018.recomp.rc2.fps60/files/macros
adb push <upstream>/intromatch.macro /sdcard/Android/data/com.pes2018.recomp.rc2.fps60/files/macros/
adb shell touch /sdcard/Android/data/com.pes2018.recomp.rc2.fps60/files/macros/.remote_control

tools/run_ab.sh base
tools/run_ab.sh nomsaa PES17_NO_MSAA=1
tools/run_ab.sh s75 PES17_NO_MSAA=1 PES17_SCENE_SCALE=0.75
tools/run_ab.sh light PES17_NO_MSAA=1 PES17_SCENE_SCALE=0.75 \
  PES17_FORCE_LEGACY_RENDERING= PES17_FORCE_BC_DECOMPRESS=
```

Hasil (median FPS pertandingan; satu run bisa menyimpang ±15 FPS tergantung
suhu/adegan, jadi bandingkan median dan ulangi bila ragu):

| Konfigurasi | Median FPS | p50 frame | GPU wait |
|---|---:|---:|---:|
| baseline (MSAA ON, 0.85) | 21.5 | ~49 ms | ~850 ms/s |
| `NO_MSAA=1` | 45.0 | ~20 ms | ~190 ms/s |
| `NO_MSAA=1` + `SCENE_SCALE=0.75` | 37–54 | ~18 ms | ~200 ms/s |
| + legacy/BC decompress dinonaktifkan | 39.0 | ~21 ms | ~220 ms/s |

Kesimpulan: MSAA adalah akar masalah. `PES17_FORCE_LEGACY_RENDERING=1` dan
`PES17_FORCE_BC_DECOMPRESS=1` yang di-force patch **dipertahankan** karena
menonaktifkannya justru lebih lambat di chipset ini.

## Perbaikan

Di `apk/patches/patch_rc2_60.py`, dua baris disuntikkan sebelum pemanggilan
`nativeSetOption` di `GameActivity.smali`:

```smali
const-string v0, "1"
const-string v4, "PES17_NO_MSAA"
invoke-virtual {v13, v4, v0}, Lcom/pes2017/recomp/NativeBridge;->nativeSetOption(...)

const-string v4, "0.75"
const-string v11, "PES17_SCENE_SCALE"
invoke-virtual {v13, v11, v4}, Lcom/pes2017/recomp/NativeBridge;->nativeSetOption(...)
```

Ini mengabaikan preferensi UI (`multisampling`, `sceneScale`) yang tersimpan di
perangkat, jadi perbaikan berlaku tanpa pengguna mengubah setting apa pun.

Build & pasang:

```sh
apktool d rc2.apk -o rc2_60_out -f
python3 apk/patches/patch_rc2_60.py
apktool b rc2_60_out -o rc2-fpsfix-unsigned.apk
python3 tools/align_apk.py rc2-fpsfix-unsigned.apk rc2-fpsfix-aligned.apk
apksigner sign --ks tuned.keystore --ks-key-alias tuned \
  --ks-pass pass:123456 --key-pass pass:123456 \
  --out rc2-tuned-60fps-fpsfix.apk rc2-fpsfix-aligned.apk
adb install -r rc2-tuned-60fps-fpsfix.apk
```

## Verifikasi build final

Tanpa `env_override` sama sekali:

- `# resolved`: `msaa=0, scene_scale=0.75, fps_limit=60`
- Pertandingan: **median 57 FPS**, mean 49.8, p50 16.9 ms, GPU wait 224 ms/s
- Detik dengan FPS < 15 saat intro/cutscene: **0** (sebelumnya 14 detik)

## Sisa frame drop (56 → 20 FPS)

Masih ada, tapi penyebabnya berbeda dan sudah terukur dari `telemetry.csv`
kolom `decode_ms / stage_ms / read_ms / pipe_n`:

1. **Kickoff / aset baru masuk (paling sering).** Di detik ±101 (awal
   pertandingan) dan kadang saat reveal baru, ~55–90 tekstur baru di-upload:
   `decode_ms` 100–147 ms, `stage_ms` 40–50 ms, `read_ms` 30–40 ms. Total
   ±190–230 ms kerja pada thread yang sama, sehingga FPS turun ke 12–23 selama
   beberapa detik. Ini **bukan GPU** (`gpu_wait_ms` ≈ 0 saat drop) dan bukan
   thermal. Tekstur sudah memakai `texture_store.bin` + BC→ASTC; mematikan ASTC
   justru membuatnya lebih parah (store miss, FPS median 34). Tidak ada switch
   runtime untuk mengupload tekstur ini secara async, jadi hitch ini melekat.
2. **Kompilasi pipeline saat warmup (jarang).** Pernah tercatat `warmup:
   precompiled pipeline ... in 479 ms / 204 ms` di tengah pertandingan. Default
   tier cuma 40 pipeline / 600 ms saat boot, sisanya dikompilasi background.
   Patch sekarang menaikkan budget ke **500 pipeline / 30000 ms**, jadi seed
   shader-cache (~470 pipeline) selesai sebelum pertandingan. Boot tidak
   terukur lebih lama dengan cache hangat.

A/B yang sudah dicoba dan **ditolak**:

| Percobaan | Hasil |
|---|---|
| `PES17_NO_BC_ASTC=1` | median 34 FPS, store miss, decode lebih lama — jangan dipakai |
| `PES17_PREWARM_MAX=500 PES17_PREWARM_MS=30000` | dipakai; menghilangkan stall pipeline, tidak menyentuh hitch tekstur |

Perhatian: menjalankan macro A/B menghasilkan variasi median 34–58 FPS antar
run (suhu, adegan, dan waktu sampling relatif terhadap kickoff beda-beda).
Bandingkan dengan median beberapa run, bukan satu angka.

## Batasan

- Frame generation sengaja tetap mati (stability profile). Kalau menginginkan
  tampilan 60 FPS dengan game berjalan di 30 FPS, aktifkan
  `PES17_FRAMEGEN=1` + `PES17_FPS_LIMIT=30`, tapi itu bukan perbaikan latency.
- Jika HP sudah sangat panas, FPS tetap bisa turun karena thermal; itu di luar
  cakupan perbaikan ini.
- Macro `intromatch.macro` berasal dari upstream (GPL-3.0) dan **tidak**
  disertakan di repo MIT ini; ambil dari checkout upstream saat ingin A/B.
