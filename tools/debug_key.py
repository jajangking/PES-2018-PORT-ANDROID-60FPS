#!/usr/bin/env python3
"""Temporary: log every keycode reaching GameActivity.dispatchKeyEvent."""
p = "/data/data/com.termux/files/usr/tmp/opencode/pes2018-re/rc2_60_out/smali/com/pes2017/recomp/GameActivity.smali"
s = open(p, encoding="utf-8").read()
method = ".method public final dispatchKeyEvent(Landroid/view/KeyEvent;)Z"
assert s.count(method) == 1
start = s.index(method)
# widen locals inside this method only
old_locals = ".locals 9"
assert s[start:start+200].count(old_locals) == 1
s = s[:start] + s[start:].replace(old_locals, ".locals 11", 1)

anchor = '''    # ---- OTG PS2 adapter: BUTTON_1..12 -> internal bits ----'''
assert s.count(anchor) == 1
inject = '''    const-string v9, "OTGKEY"

    invoke-static {v0}, Ljava/lang/Integer;->toString(I)Ljava/lang/String;

    move-result v10

    invoke-static {v9, v10}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

''' + anchor
s = s.replace(anchor, inject, 1)
open(p, "w", encoding="utf-8").write(s)
print("debug key logging injected")
