# UI experiment (not in the stable build)

Branch `ui-experiment`. Stable build stays on `main` / tag `stable-2026-11-24`.

`apk/patches/patch_ui.py` runs **after** `patch_rc2_60.py` on the decoded tree
and changes:

- launcher strings to Indonesian, app label `[TUNED] PES 2018`;
- a static "PROFIL TUNED" panel on the launcher (MSAA off, render 75%, FPS 60,
  crowd/framegen off);
- pause menu from a single-column list to a 2-column `GridView` using a new
  `PauseGridListener` smali bridge to the existing click dispatcher;
- `autoLaunch` default off, so opening the app shows the launcher instead of
  jumping straight into the game (the black landscape loading screen).

Build:

```sh
apktool d rc2.apk -o rc2_60_out -f
python3 apk/patches/patch_rc2_60.py
python3 apk/patches/patch_ui.py
apktool b rc2_60_out -o ui-unsigned.apk
python3 tools/align_apk.py ui-unsigned.apk ui-aligned.apk
apksigner sign --ks tuned.keystore --ks-key-alias tuned \
  --ks-pass pass:123456 --key-pass pass:123456 \
  --out rc2-tuned-ui.apk ui-aligned.apk
```

Status: experimental. The stable device build is `main` (tag
`stable-2026-11-24`); the UI branch has not been verified end-to-end on the
device, and the graphics values are still forced at native level by
`patch_rc2_60.py` even though the settings screen allows changes.
