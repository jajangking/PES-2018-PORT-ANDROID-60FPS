#!/usr/bin/env python3
"""EXPERIMENTAL UI overhaul: Indonesian launcher strings, tuned profile panel,
2-column pause grid, and launcher-first startup (autoLaunch off by default).

Run this AFTER patch_rc2_60.py on the decoded tree. Not part of the stable
build. Rebuild/sign normally after running it.
"""
import os
import re
import xml.dom.minidom

ROOT = "/data/data/com.termux/files/usr/tmp/opencode/pes2018-re/rc2_60_out"

# ---------------------------------------------------------------- launcher text
strings = os.path.join(ROOT, "res/values/strings.xml")
s = open(strings, encoding="utf-8").read()
tr = {
    "app_name_rc2": "[TUNED] PES 2018",
    "detail_default_text": "Pilih menu: detailnya muncul di sini, dan pilihannya langsung dijalankan.",
    "detail_default_title": "MENU UTAMA",
    "direct_launch": "Langsung kick off saat aplikasi dibuka",
    "disable_gamepad": "Abaikan gamepad fisik",
    "edit_controls": "Ubah kontrol",
    "enable_gamepad": "Pakai gamepad fisik",
    "entry_patches": "PATCH",
    "entry_settings": "PENGATURAN",
    "graphics_driver": "Driver grafis",
    "hide_touch_controls": "Sembunyikan kontrol layar",
    "hud_menu": "HUD performa",
    "macro_play": "Putar macro",
    "paused": "Jeda",
    "play": "KICK OFF",
    "qg_menu": "Grafis &amp; performa",
    "quit": "Keluar",
    "quit_launcher": "KELUAR",
    "resume": "Lanjut",
    "show_touch_controls": "Tampilkan kontrol layar",
    "view_log": "Log",
    "wordmark": "PES18 Recompiled for Android — TUNED",
    "settings_hint": "Gambar, performa, kontrol, dan file game untuk port ini. Semua bisa diubah.",
    "settings_help_strip": "Perubahan tersimpan langsung dan berlaku saat pertandingan berikutnya. Tekan Kembali untuk kembali ke menu.",
    "scene_scale_hint": "Ukuran adegan 3D sebelum diregangkan ke layar. 75% adalah profil tuned; naikkan di HP kuat (risiko FPS turun).",
    "fps_limit_hint": "Batas frame per detik. 60 = pacing konsol. 30 paling stabil di layar 60 Hz; 35–55 bisa judder.",
}
for key, value in tr.items():
    pattern = re.compile(r'(<string name="' + re.escape(key) + r'")[^>]*>.*?</string>', re.S)
    assert pattern.search(s), "missing string " + key
    s = pattern.sub(lambda m: m.group(1) + ">" + value + "</string>", s, count=1)
extra = """
    <string name="tuned_profile_title">PROFIL TUNED</string>
    <string name="tuned_profile_lines">MSAA MATI · Render 75%\\nFPS 60 · Crowd mati · Framegen mati\\nSemua grafis bisa diubah di PENGATURAN</string>
"""
s = s.replace("</resources>", extra + "</resources>")
xml.dom.minidom.parseString(s)
open(strings, "w", encoding="utf-8").write(s)
print("launcher strings translated")

# ------------------------------------------------------------- tuned info panel
layout = os.path.join(ROOT, "res/layout/activity_main.xml")
s = open(layout, encoding="utf-8").read()
needle = '                <TextView android:textSize="14.0sp" android:textStyle="bold|italic"'
panel = (
    '                <TextView android:textSize="10.0sp" android:textStyle="bold" '
    'android:textColor="@color/pes_blue" android:id="@+id/tuned_profile_title" '
    'android:background="@drawable/bg_panel_title" android:paddingTop="4.0dp" '
    'android:paddingBottom="3.0dp" android:layout_width="match_parent" '
    'android:layout_height="wrap_content" android:text="@string/tuned_profile_title" '
    'android:fontFamily="sans-serif-condensed" android:paddingStart="10.0dp" />\n'
    '                <TextView android:textSize="10.0sp" android:textColor="@color/pes_text" '
    'android:layout_width="match_parent" android:layout_height="wrap_content" '
    'android:text="@string/tuned_profile_lines" android:paddingStart="10.0dp" '
    'android:paddingEnd="10.0dp" android:paddingTop="4.0dp" '
    'android:lineSpacingExtra="2.0dp" android:fontFamily="sans-serif" />\n'
)
assert needle in s
s = s.replace(needle, panel + needle, 1)
open(layout, "w", encoding="utf-8").write(s)
print("tuned profile panel added")

# --------------------------------------------------------- pause grid listener
listener = os.path.join(ROOT, "smali/com/pes2017/recomp/PauseGridListener.smali")
open(listener, "w", encoding="utf-8").write('''\
.class public Lcom/pes2017/recomp/PauseGridListener;
.super Ljava/lang/Object;
.source "PauseGridListener"


# interfaces
.implements Landroid/widget/AdapterView$OnItemClickListener;


# instance fields
.field public final a:Landroid/content/DialogInterface$OnClickListener;

.field public final b:Landroid/content/DialogInterface;


# direct methods
.method public constructor <init>(Landroid/content/DialogInterface$OnClickListener;Landroid/content/DialogInterface;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/pes2017/recomp/PauseGridListener;->a:Landroid/content/DialogInterface$OnClickListener;

    iput-object p2, p0, Lcom/pes2017/recomp/PauseGridListener;->b:Landroid/content/DialogInterface;

    return-void
.end method


# virtual methods
.method public onItemClick(Landroid/widget/AdapterView;Landroid/view/View;IJ)V
    .locals 2

    iget-object v0, p0, Lcom/pes2017/recomp/PauseGridListener;->a:Landroid/content/DialogInterface$OnClickListener;

    iget-object v1, p0, Lcom/pes2017/recomp/PauseGridListener;->b:Landroid/content/DialogInterface;

    invoke-interface {v0, v1, p3}, Landroid/content/DialogInterface$OnClickListener;->onClick(Landroid/content/DialogInterface;I)V

    return-void
.end method
''')

# -------------------------------------------------------------- pause grid swap
game = os.path.join(ROOT, "smali/com/pes2017/recomp/GameActivity.smali")
s = open(game, encoding="utf-8").read()
old = """    new-instance v5, LS/q;

    invoke-direct {v5, v1, v3}, LS/q;-><init>(ILjava/lang/Object;)V

    invoke-virtual {v2, v4, v5}, Lf/g;->b([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)V

    new-instance v1, LS/z0;

    invoke-direct {v1, v0, p0}, LS/z0;-><init>(ILjava/lang/Object;)V

    iget-object v0, v2, Lf/g;->b:Ljava/lang/Object;

    check-cast v0, Lf/c;

    iput-object v1, v0, Lf/c;->o:Landroid/content/DialogInterface$OnDismissListener;

    invoke-virtual {v2}, Lf/g;->h()V

    return-void"""
new = """    # ---- tuned grid pause menu -------------------------------------------
    new-instance v6, Landroid/widget/GridView;

    invoke-direct {v6, p0}, Landroid/widget/GridView;-><init>(Landroid/content/Context;)V

    const/4 v7, 0x2

    invoke-virtual {v6, v7}, Landroid/widget/GridView;->setNumColumns(I)V

    const/16 v7, 0x8

    invoke-virtual {v6, v7, v7, v7, v7}, Landroid/widget/GridView;->setPadding(IIII)V

    new-instance v8, Landroid/widget/ArrayAdapter;

    const v7, 0x01090001

    invoke-direct {v8, p0, v7, v4}, Landroid/widget/ArrayAdapter;-><init>(Landroid/content/Context;I[Ljava/lang/CharSequence;)V

    invoke-virtual {v6, v8}, Landroid/widget/GridView;->setAdapter(Landroid/widget/ListAdapter;)V

    new-instance v1, LS/z0;

    const/4 v0, 0x0

    invoke-direct {v1, v0, p0}, LS/z0;-><init>(ILjava/lang/Object;)V

    iget-object v0, v2, Lf/g;->b:Ljava/lang/Object;

    check-cast v0, Lf/c;

    iput-object v1, v0, Lf/c;->o:Landroid/content/DialogInterface$OnDismissListener;

    iput-object v6, v0, Lf/c;->e:Landroid/view/View;

    invoke-virtual {v2}, Lf/g;->a()Lf/h;

    move-result-object v7

    new-instance v8, Lcom/pes2017/recomp/PauseGridListener;

    invoke-direct {v8, v5, v7}, Lcom/pes2017/recomp/PauseGridListener;-><init>(Landroid/content/DialogInterface$OnClickListener;Landroid/content/DialogInterface;)V

    invoke-virtual {v6, v8}, Landroid/widget/GridView;->setOnItemClickListener(Landroid/widget/AdapterView$OnItemClickListener;)V

    invoke-virtual {v7}, Landroid/app/Dialog;->show()V

    return-void"""
assert s.count(old) == 1, "showMenu tail not found"
s = s.replace(old, new, 1)
open(game, "w", encoding="utf-8").write(s)
print("pause menu converted to 2-column grid")

# ------------------------------------------------------ launcher-first startup
main = os.path.join(ROOT, "smali/com/pes2017/recomp/MainActivity.smali")
s = open(main, encoding="utf-8").read()
old1 = """    :cond_1c
    const/4 v1, 0x1

    iget-object v2, v0, Lcom/pes2017/recomp/MainActivity;->z:LS/n2;"""
new1 = old1.replace("const/4 v1, 0x1", "const/4 v1, 0x0")
assert s.count(old1) == 1
s = s.replace(old1, new1, 1)
old2 = """    const-string v12, "autoLaunch"

    iget-object v11, v11, LS/n2;->a:Landroid/content/SharedPreferences;

    invoke-interface {v11, v12, v4}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z"""
new2 = old2.replace("    invoke-interface", "    const/4 v4, 0x0\n\n    invoke-interface")
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)
open(main, "w", encoding="utf-8").write(s)
print("autoLaunch default -> false")
