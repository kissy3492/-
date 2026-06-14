# -*- coding: utf-8 -*-
"""
黒猫 機能追加 前提検証 (kuroneko_probe.py)  v2.0  ―― 記録・転記を足す前の診断
============================================================================

黒猫（既存のトレイ常駐ランチャー）に、グローバルフック／UIA取得／クリップ
ボード取得に依存する機能 ―― 主に ManualRecorder（②§9）・項目転記（②§7） ――
を追加する前に、それらが職場PCで本当に成り立つかを1回で確かめる診断ツール。

【このprobeの位置づけ】
  黒猫は既に動いているので、tkinter・トレイ・最前面・DPI 等の基礎は確認済み
  （動いている＝通っている）。よって本v2は、既存では未確認で、かつ記録・転記の
  成否を分ける「3つの核心」に絞って検証する:

    [A] グローバルフック   … 記録・ホットキーの中核（pynput）          【最重要】
    [B] UIAでの値の取得    … 業務システムの入力欄/表の値が読めるか
    [C] クリップボード取得 … 業務システムで選択→Ctrl+Cした値を拾えるか（転記の前提）

  併せて、これらに必要なライブラリ（pynput / uiautomation / Pillow）の有無を確認し、
  不足はオンライン前提で自動インストールを試みる（入らないものは弾かれる）。

【いつ使うか】
  - 記録（ManualRecorder）や項目転記を足す前に1回。
  - 検索・履歴・付箋・パレットだけを足すなら不要（フック等に依存しないため）。

【使い方】
  1) 職場PC（フル版Python）で:  python kuroneko_probe.py
  2) 画面の ★ 指示に従って操作（キー入力・業務アプリにカーソル・選択コピー）。
  3) 末尾の【総合判定】と kuroneko_probe_result.txt を共有。

【結果の読み方（記録・転記の生死）】
  [A]× → ホットキー・記録・転記が動かない。セキュリティ/ポリシーの除外申請が前提。
  [B]○ → 記録の手順文が人間可読（T1）／将来の自動取得も射程。
  [B]△ → 記録は動くが手順文はT0(赤丸)寄り。致命ではない（②§9.4の縮退）。
  [C]○ → 項目転記が成立（②§7の前提クリア）。
  [C]× → その画面は選択/コピー不可。UIA([B])で読めるなら経路を変える。

  ※ 外部通信は一切しない（ライブラリ自動インストールのpipを除く）。
    結果はローカルtxtに書くだけ。フック検証は内容を記録せず回数のみ数える。
"""

import sys
import os
import time
import platform
import datetime
import subprocess

# ----------------------------------------------------------------------
RESULTS = []
LOG_LINES = []
MARK = {"ok": "○ OK", "ng": "× NG", "warn": "△ 注意"}

def log(msg=""):
    print(msg); LOG_LINES.append(str(msg))

def record(tag, name, verdict, detail=""):
    RESULTS.append((tag, name, verdict, detail))

def section(title):
    log(""); log("=" * 64); log(title); log("-" * 64)

# ----------------------------------------------------------------------
# 0. 環境ひとことサマリ（重い検証はしない＝既存が動いている前提）
# ----------------------------------------------------------------------
def check_env():
    section("[0] 環境（既存の黒猫が動いている前提・参考表示）")
    log(f"  Python {sys.version.split()[0]} / {platform.platform()}")
    if sys.platform != "win32":
        log("  ※ Windows以外。本probeはWindows前提（一部検証は意味を持たない）。")
    base = os.path.dirname(sys.executable)
    try:
        if any(f.endswith("._pth") for f in os.listdir(base)):
            log("  △ embeddable版の可能性（tkinter非同梱の恐れ）。フル版推奨。")
    except Exception:
        pass

# ----------------------------------------------------------------------
# 1. 必要ライブラリ（記録・転記に要るものだけ）＋不足は自動インストール
# ----------------------------------------------------------------------
PIP_NAME = {"PIL": "pillow"}
NEEDED = {
    "pynput":       "グローバルフック・ホットキー・キー送出【記録/転記に必須】",
    "uiautomation": "UIAでの部品名/値の取得【記録の質・自動取得に必要】",
    "PIL":          "Pillow＝スクリーンショット【記録のスクショに必要】",
    "comtypes":     "uiautomation の依存",
}

def _imp(mod):
    try:
        m = __import__(mod); return True, getattr(m, "__version__", "?")
    except Exception:
        return False, None

def _pip_install(pkgs):
    cmd = [sys.executable, "-m", "pip", "install", *pkgs]
    log("  実行: " + " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        for line in (p.stdout or "").strip().splitlines()[-3:]:
            log("    | " + line)
        if p.returncode != 0:
            for line in (p.stderr or "").strip().splitlines()[-2:]:
                log("    ! " + line)
        return p.returncode == 0
    except Exception as e:
        log(f"    ! pip実行失敗: {e}"); return False

def check_libs():
    section("[1] 必要ライブラリ（記録・転記用）・不足は自動インストール")
    found, missing = {}, []
    for mod, desc in NEEDED.items():
        ok, ver = _imp(mod)
        log(f"  {MARK['ok'] if ok else MARK['ng']}  {mod:13s} {str(ver or ''):10s} … {desc}")
        found[mod] = ok
        if not ok:
            missing.append(mod)
    if missing:
        pkgs = [PIP_NAME.get(m, m) for m in missing]
        log("")
        log(f"  不足 {len(missing)} 件を自動インストール（オンライン前提）: {', '.join(pkgs)}")
        _pip_install(pkgs)
        log("  再チェック:")
        for mod in missing:
            ok, ver = _imp(mod)
            log(f"    {MARK['ok'] if ok else MARK['ng']}  {mod:13s} "
                f"{'導入できました' if ok else '導入できず（弾かれた可能性）'}")
            found[mod] = ok
    record("lib", "必要ライブラリ", "ok" if found.get("pynput") else "ng",
           "/".join(k for k, val in found.items() if val) or "なし")
    return found

# ----------------------------------------------------------------------
# [A] グローバルフック（最重要）
# ----------------------------------------------------------------------
def check_hook(found):
    section("[A] グローバルフック ―― 記録・ホットキーの中核【最重要】")
    if not found.get("pynput"):
        log("  pynput が無いため検証不可"); record("A", "グローバルフック", "ng", "pynput未導入"); return
    log("  5秒間、キー入力とマウスクリックを監視します（内容は記録せず回数のみ）。")
    log("  ★ 何かキーを押す・どこかをクリックしてください…")
    try:
        from pynput import keyboard, mouse
        c = {"k": 0, "m": 0}
        kl = keyboard.Listener(on_press=lambda k: c.update(k=c["k"] + 1))
        ml = mouse.Listener(on_click=lambda x, y, b, p: c.update(m=c["m"] + 1) if p else None)
        kl.start(); ml.start()
        t0 = time.time()
        while time.time() - t0 < 5.0:
            time.sleep(0.1)
        kl.stop(); ml.stop()
        log(f"  検出: キー {c['k']} 回 / クリック {c['m']} 回")
        if c["k"] + c["m"] > 0:
            log("  → フック有効。記録・ホットキー・転記の中核前提クリア。")
            record("A", "グローバルフック", "ok", f"key{c['k']}/click{c['m']}")
        else:
            log("  → 未検出。(a)操作忘れなら再試行 / (b)遮断なら除外申請が必要【重要】")
            record("A", "グローバルフック", "warn", "未検出（再試行 or 遮断の可能性）")
    except Exception as e:
        log(f"  例外（フック登録が拒否された可能性＝遮断）→ {e}")
        record("A", "グローバルフック", "ng", f"例外: {e}")

# ----------------------------------------------------------------------
# [B] UIAでの値の取得（業務システムの中身が読めるか）
# ----------------------------------------------------------------------
def check_uia(found):
    section("[B] UIA取得 ―― 業務システムの入力欄/表の『値』が読めるか")
    if not found.get("uiautomation"):
        log("  uiautomation が無いため検証不可（記録はT0固定で縮退・②§9.4）")
        record("B", "UIA取得", "warn", "未導入→T0固定で動作は可"); return
    if sys.platform != "win32":
        log("  Windowsでないため検証不可"); record("B", "UIA取得", "warn", "非Windows"); return
    try:
        import uiautomation as auto
        log("  3秒後、カーソル下の部品の『種別・名前・値・親子構造』を調べます。")
        log("  ★ 業務システムの入力欄・表のセル・金額や氏名の上にカーソルを置いてください…")
        for i in (3, 2, 1):
            log(f"     {i}…"); time.sleep(1)
        ctrl = auto.ControlFromCursor()
        if ctrl is None:
            log("  取得不可（この画面はUIAで読めない＝T0相当・赤丸位置のみ）")
            record("B", "UIA取得", "warn", "取得不可→T0相当"); return
        name = (getattr(ctrl, "Name", "") or "").strip()
        ctype = getattr(ctrl, "ControlTypeName", "")
        log(f"  種別: {ctype} / Name: '{name}'")
        value = None
        try:
            value = ctrl.GetValuePattern().Value
            log(f"  ValuePattern.Value: '{value}'  ← 入力欄の値が取れた")
        except Exception:
            log("  ValuePattern: 非対応（入力欄でないか値非公開）")
        if value is None:
            try:
                value = ctrl.GetTextPattern().DocumentRange.GetText(80)
                log(f"  TextPattern: '{value[:80]}'  ← テキストが取れた")
            except Exception:
                log("  TextPattern: 非対応")
        chain, cur = [], ctrl
        for _ in range(4):
            if cur is None:
                break
            chain.append(f"{getattr(cur,'ControlTypeName','')}:'{(getattr(cur,'Name','') or '')[:20]}'")
            try:
                cur = cur.GetParentControl()
            except Exception:
                break
        log("  親子構造: " + " ← ".join(chain))
        if value:
            log("  → 値が取得できた。記録に加え将来の自動取得も射程。")
            record("B", "UIA取得", "ok", "値の取得に成功")
        elif name:
            log("  → 名前は取れる（T1相当）。値は要素により取れたり取れなかったり。")
            record("B", "UIA取得", "ok", "名前取得OK・値は要素次第")
        else:
            log("  → 名前/値が空（T2〜T4寄り）。記録は動くが手順文は弱め。")
            record("B", "UIA取得", "warn", "名前/値が空・構造のみ")
    except Exception as e:
        log(f"  例外 → {e}"); record("B", "UIA取得", "warn", f"例外: {e}")

# ----------------------------------------------------------------------
# [C] クリップボード取得（項目転記の前提）
# ----------------------------------------------------------------------
def check_clipboard_acquire(found):
    section("[C] クリップボード取得 ―― 業務システムで選択→Ctrl+Cした値を拾えるか")
    try:
        import tkinter as tk
    except Exception as e:
        log(f"  tkinter不可のため検証不可: {e}")
        record("C", "クリップボード取得", "warn", "tkinter不可"); return
    log("  項目転記(②§7)の大前提＝『読み元で選択→Ctrl+Cした値を拾えるか』を試します。")
    log("  ★ 10秒以内に、業務システム等で文字を選択して Ctrl+C してください…")
    log("    （機微な値は避け、画面の見出し等で試すと安全）")
    try:
        root = tk.Tk(); root.withdraw()
        try:
            saved = root.clipboard_get()
        except Exception:
            saved = None
        sentinel = "KURONEKO_WAIT_" + str(int(time.time()))
        root.clipboard_clear(); root.clipboard_append(sentinel); root.update()
        got, t0 = None, time.time()
        while time.time() - t0 < 10.0:
            root.update()
            try:
                cur = root.clipboard_get()
            except Exception:
                cur = None
            if cur is not None and cur != sentinel:
                got = cur; break
            time.sleep(0.15)
        if got is not None:
            prev = got if len(got) <= 60 else got[:60] + "…"
            log(f"  取得できた内容: '{prev}'（{len(got)}文字）")
            log("  → コピー取得に成功。項目転記の前提クリア（②§7.2）。")
            record("C", "クリップボード取得", "ok", f"{len(got)}文字を取得")
        else:
            log("  → 未検出。(a)操作忘れなら再試行 /")
            log("     (b)その画面が選択/コピー不可なら、UIA([B])で読める経路に切替（②§7 vs §9）")
            record("C", "クリップボード取得", "warn", "未検出（再試行 or 選択不可画面）")
        try:
            root.clipboard_clear()
            if saved is not None:
                root.clipboard_append(saved)
            root.update()
        except Exception:
            pass
        root.destroy()
    except Exception as e:
        log(f"  例外 → {e}"); record("C", "クリップボード取得", "warn", f"例外: {e}")

# ----------------------------------------------------------------------
# 総合判定
# ----------------------------------------------------------------------
def summary():
    log(""); log("=" * 64); log("【総合判定】"); log("-" * 64)
    for tag, name, verdict, detail in RESULTS:
        log(f"  {MARK.get(verdict,'?'):6s} [{tag}] {name}: {detail}")

    def v(tag):
        for t, _, ver, _ in RESULTS:
            if t == tag:
                return ver
        return None

    log(""); log("-" * 64); log("【記録・転記を足せるかの判定】")
    a, b, c = v("A"), v("B"), v("C")
    if a == "ok":
        log("  ○★ フック有効 → 記録・ホットキー・転記の中核前提クリア。")
    elif a == "warn":
        log("  △★ フック未検出 → 操作忘れなら再試行。本当に遮断なら除外申請が必要。")
    else:
        log("  ×★ フック不可 → 記録・転記は動かない。除外申請が成立の絶対条件。")
    if b == "ok":
        log("  ○ UIAで名前/値が取れる → 記録が人間可読・自動取得も射程。")
    elif b == "warn":
        log("  △ UIAが弱い/無し → 記録はT0(赤丸)寄りで動く。致命でない（②§9.4）。")
    if c == "ok":
        log("  ○ コピー取得できる → 項目転記が成立（②§7）。")
    elif c == "warn":
        log("  △ コピー取得できず → 選択/コピー不可画面かも。UIA([B])で読めるなら経路変更。")
    if b == "warn" and c == "warn":
        log("  ×★ UIA・コピーの両方で取得不可な画面 → その画面からの情報取得は困難。")
        log("     対象画面を変えるか別アプローチが要る（重要な発見）。")
    log("")
    log("  ※ 結果を kuroneko_probe_result.txt ごと共有してください。")

# ----------------------------------------------------------------------
def main():
    log("黒猫 機能追加 前提検証 v2.0（記録・転記を足す前の診断）")
    log("実行時刻: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log("（外部通信はしません。ライブラリ自動インストールのpipを除く）")
    check_env()
    found = check_libs()
    check_hook(found)
    check_uia(found)
    check_clipboard_acquire(found)
    summary()
    try:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "kuroneko_probe_result.txt")
    except Exception:
        out = "kuroneko_probe_result.txt"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(LOG_LINES))
        log(""); log(f"結果を書き出しました: {out}")
    except Exception as e:
        log(f"結果ファイル書き出し失敗: {e}")
    try:
        if sys.platform == "win32":
            input("\nEnterキーで終了します…")
    except Exception:
        pass

if __name__ == "__main__":
    main()
