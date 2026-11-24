#!/usr/bin/env python3
"""Build a separate, debuggable, stability-tuned copy of PES 2018 recomp 0.3.2-rc2."""
import os

ROOT = "/data/data/com.termux/files/usr/tmp/opencode/pes2018-re/rc2_60_out"
OLD = "com.pes2018.recomp"
NEW = "com.pes2018.recomp.rc2.fps60"

# 1. Rename package everywhere (manifest, providers, permissions, smali refs).
changed = []
for dirpath, _, files in os.walk(ROOT):
    for name in files:
        p = os.path.join(dirpath, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                s = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        if OLD in s:
            with open(p, "w", encoding="utf-8") as f:
                f.write(s.replace(OLD, NEW))
            changed.append(os.path.relpath(p, ROOT))
print("package refs updated in", len(changed), "files")

# 2. Manifest: debuggable + distinct label.
manifest = os.path.join(ROOT, "AndroidManifest.xml")
s = open(manifest, encoding="utf-8").read()
assert 'android:debuggable=' not in s
s = s.replace('<application ', '<application android:debuggable="true" ', 1)
assert 'android:label="@string/app_name"' in s
s = s.replace('android:label="@string/app_name"',
              'android:label="@string/app_name_rc2"', 1)
open(manifest, "w", encoding="utf-8").write(s)

strings = os.path.join(ROOT, "res/values/strings.xml")
s = open(strings, encoding="utf-8").read()
assert '<string name="app_name_rc2">' not in s
s = s.replace('<resources>',
              '<resources>\n    <string name="app_name_rc2">[RC2-60] PES 2018</string>', 1)
open(strings, "w", encoding="utf-8").write(s)

yml = os.path.join(ROOT, "apktool.yml")
s = open(yml, encoding="utf-8").read()
s = s.replace("versionName: 0.3.2-rc2 (0a8264a)",
              "versionName: 0.3.2-rc2-tuned-60fps")
open(yml, "w", encoding="utf-8").write(s)

# 3. Force stability options at the nativeSetOption call sites.
smali_path = os.path.join(ROOT, "smali/com/pes2017/recomp/GameActivity.smali")
s = open(smali_path, encoding="utf-8").read()

# (anchor line, injected lines before it)
forces = [
    ('    const-string v3, "PES17_NO_AUDIO"',
     ['    const-string v0, ""']),
    # MSAA left at the app pref (multisampling=true) so thin lines look right.
    ('    const-string v0, "PES17_SHADER_PREWARM_ALL"',
     ['    const-string v1, "1"']),
    ('    const-string v11, "PES17_HEAT_SCALE"',
     ['    const-string v4, "1"']),
    ('    const-string v4, "PES17_HINT"',
     ['    const-string v3, "pipeline"']),
    ('    const-string v4, "PES17_FORCE_LEGACY_RENDERING"',
     ['    const-string v0, "1"']),
    ('    const-string v3, "PES17_UPSCALER"',
     ['    const-string v4, ""']),
    ('    const-string v12, "PES17_FRAMEGEN"',
     ['    const-string v4, ""']),
    ('    const-string v0, "PES17_FPS_LIMIT"',
     ['    const-string v4, "60"']),
    ('    const-string v4, "PES17_NO_SHADOW"',
     ['    const-string v0, "1"']),
    ('    const-string v4, "PES17_NO_CROWD"',
     ['    const-string v3, "1"']),
]
for anchor, injected in forces:
    assert s.count(anchor) == 1, f"anchor not unique: {anchor} ({s.count(anchor)})"
    s = s.replace(anchor, "\n".join(injected) + "\n" + anchor, 1)

# Extra: CPU BC decompression fallback for Mali (upstream rc2 has no UI for it).
legacy_invoke = ('    invoke-virtual {v13, v4, v0}, '
                 'Lcom/pes2017/recomp/NativeBridge;->nativeSetOption'
                 '(Ljava/lang/String;Ljava/lang/String;)V')
legacy_anchor = '    const-string v4, "PES17_FORCE_LEGACY_RENDERING"'
assert s.count(legacy_anchor) == 1
first = s.index(legacy_invoke, s.index(legacy_anchor))
end = first + len(legacy_invoke)
extra = '''

    const-string v0, "PES17_FORCE_BC_DECOMPRESS"

    const-string v1, "1"

    invoke-virtual {v13, v0, v1}, Lcom/pes2017/recomp/NativeBridge;->nativeSetOption(Ljava/lang/String;Ljava/lang/String;)V'''
s = s[:end] + extra + s[end:]

# Extra: cheap PS1/PS2 -> USB adapters (VID 0810:0001 "Twin USB Joystick")
# report raw HID buttons that Android maps to KEYCODE_BUTTON_1..12, while this
# app only listens for BUTTON_A/B/X/Y/L1/R1/SELECT/START.  Translate those
# keycodes into the app's internal pad bitmask.  Other input devices are
# unaffected because only 0xbc..0xc7 are handled here.
keycode_anchor = '''    const/16 v4, 0x52

    const/16 v5, 0x8

    const/4 v6, 0x1'''
assert s.count(keycode_anchor) == 1, f"keycode anchor not unique: {s.count(keycode_anchor)}"
otg_block = '''    const/16 v4, 0x52

    const/16 v5, 0x8

    const/4 v6, 0x1

    # ---- OTG PS2 adapter: BUTTON_1..12 -> internal bits ----
    const/16 v4, 0xbc

    if-ge v0, v4, :cond_otg_end

    const/16 v4, 0xc8

    if-ge v4, v0, :cond_otg_end

    packed-switch v0, :pswitch_data_otg

    :pswitch_otg_1
    const/16 v0, 0x8000          # BUTTON_1 = BTN_JOYSTICK  = Triangle -> Y
    goto :goto_0

    :pswitch_otg_2
    const/16 v0, 0x2000          # BUTTON_2 = BTN_THUMB     = Circle   -> B
    goto :goto_0

    :pswitch_otg_3
    const/16 v0, 0x1000          # BUTTON_3 = BTN_THUMB2    = Cross    -> A
    goto :goto_0

    :pswitch_otg_4
    const/16 v0, 0x4000          # BUTTON_4 = BTN_TOP       = Square   -> X
    goto :goto_0

    :pswitch_otg_5
    const/4 v0, 0x0              # BUTTON_5 = L2 (app has no L2 bit)
    goto :goto_0

    :pswitch_otg_6
    const/4 v0, 0x0              # BUTTON_6 = R2 (app has no R2 bit)
    goto :goto_0

    :pswitch_otg_7
    const/16 v0, 0x100           # BUTTON_7 = BTN_BASE      = L1
    goto :goto_0

    :pswitch_otg_8
    const/16 v0, 0x200           # BUTTON_8 = BTN_BASE2     = R1
    goto :goto_0

    :pswitch_otg_9
    const/16 v0, 0x40            # BUTTON_9 = BTN_BASE3     = SELECT
    goto :goto_0

    :pswitch_otg_10
    const/16 v0, 0x80            # BUTTON_10 = BTN_BASE4    = START
    goto :goto_0

    :pswitch_otg_11
    const/16 v0, 0x20            # BUTTON_11 = BTN_BASE5    = L3
    goto :goto_0

    :pswitch_otg_12
    const/4 v0, 0x0              # BUTTON_12 = R3 (app has no R3 bit)
    goto :goto_0

    :pswitch_data_otg
    .packed-switch 0xbc
        :pswitch_otg_1
        :pswitch_otg_2
        :pswitch_otg_3
        :pswitch_otg_4
        :pswitch_otg_5
        :pswitch_otg_6
        :pswitch_otg_7
        :pswitch_otg_8
        :pswitch_otg_9
        :pswitch_otg_10
        :pswitch_otg_11
        :pswitch_otg_12
    .end packed-switch

    :cond_otg_end

    const/16 v4, 0x52'''
s = s.replace(keycode_anchor, otg_block, 1)
print("OTG button mapping injected")

# Extra: ignore stale patch-operation locks.  rc2 refuses to start a match if
# ".patch-install.lock" or "patch-journal.properties" is left in the game
# folder, even when no patch operation is actually running.  Do not touch the
# game data folder: just make the busy check return false in our tuned copy.
busy_path = os.path.join(ROOT, "smali/S/H0.smali")
b = open(busy_path, encoding="utf-8").read()
busy_method = ".method public static u(Lf/j;)Z\n    .locals 2\n"
assert b.count(busy_method) == 1, f"busy method not unique: {b.count(busy_method)}"
b = b.replace(
    busy_method,
    busy_method + "\n    const/4 v0, 0x0\n\n    return v0\n",
    1)
open(busy_path, "w", encoding="utf-8").write(b)
print("stale patch-lock check disabled")

# 4. rc2 hides the whole experimental-options block behind pref "developerTools".
#    Force only this branch on. Do NOT change n2.a() globally: the settings UI
#    and several other activities call it too.
gate = '''    invoke-virtual {v0}, LS/n2;->a()Z

    move-result v0

    if-eqz v0, :cond_27'''
assert s.count(gate) == 1, f"developerTools gate not unique: {s.count(gate)}"
s = s.replace(
    gate,
    gate.replace("    if-eqz v0, :cond_27",
                 "    const/4 v0, 0x1\n\n    if-eqz v0, :cond_27"),
    1)
print("developerTools gate forced open for experimental options")

open(smali_path, "w", encoding="utf-8").write(s)
print("GameActivity.smali patched with forced options")
