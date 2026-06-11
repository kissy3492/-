# -*- coding: utf-8 -*-
"""
Oculus 起動スクリプト（Python 3.8+ / 標準ライブラリのみ・pip不要）

やること:
  1. lib/ 配下の必要ライブラリを点検し、不足分だけ公式配布元からダウンロード
  2. ローカルHTTPサーバを起動し、ブラウザで oculus.html を開く

使い方:
  oculus.html と同じフォルダに置いて
      python oculus_start.py
  （または同梱の 起動.bat をダブルクリック）

  2回目以降はダウンロード済みなのでサーバ起動だけが走る。
  終了はこのウィンドウで Ctrl+C、またはウィンドウを閉じる。
"""

import sys
import socket
import urllib.request
import urllib.error
import webbrowser
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE = Path(__file__).resolve().parent

# 取得対象: 相対パス -> (URL, 最低サイズbytes)
# 最低サイズは「プロキシのブロックページ等を誤保存していないか」の簡易検査用
FILES = {
    "lib/opencv.js":
        # 注意: 4.9以降のビルドは cv がPromiseになる新形式で、Oculusの
        # 初期化コード(onRuntimeInitialized待ち)と非互換。4.8.0を固定使用。
        ("https://docs.opencv.org/4.8.0/opencv.js", 1_000_000),
    "lib/pdf.min.js":
        ("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js", 100_000),
    "lib/pdf.worker.min.js":
        ("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js", 300_000),
    "lib/tesseract.min.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js", 30_000),
    "lib/worker.min.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/worker.min.js", 30_000),
    "lib/jpn.traineddata.gz":
        ("https://tessdata.projectnaptha.com/4.0.0/jpn.traineddata.gz", 1_000_000),
    "lib/eng.traineddata.gz":
        ("https://tessdata.projectnaptha.com/4.0.0/eng.traineddata.gz", 1_000_000),
    "lib/core/tesseract-core.wasm.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/tesseract-core.wasm.js", 1_000_000),
    "lib/core/tesseract-core-simd.wasm.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/tesseract-core-simd.wasm.js", 1_000_000),
    "lib/core/tesseract-core-lstm.wasm.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/tesseract-core-lstm.wasm.js", 1_000_000),
    "lib/core/tesseract-core-simd-lstm.wasm.js":
        ("https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/tesseract-core-simd-lstm.wasm.js", 1_000_000),
}

PORT_RANGE = range(8000, 8011)


def need_download(relpath: str, min_size: int) -> bool:
    p = BASE / relpath
    return not (p.is_file() and p.stat().st_size >= min_size)


def download(relpath: str, url: str, min_size: int) -> bool:
    """1ファイル取得。成功なら True"""
    dest = BASE / relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (oculus-setup)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else None
            done = 0
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {relpath}  {done//1024:,} KB / {total//1024:,} KB ({pct}%)",
                          end="", flush=True)
                else:
                    print(f"\r  {relpath}  {done//1024:,} KB", end="", flush=True)
        print()
        if tmp.stat().st_size < min_size:
            tmp.unlink(missing_ok=True)
            print(f"  ✗ サイズ異常（{min_size//1024}KB未満）。プロキシ等で中身が差し替わった可能性。")
            return False
        tmp.replace(dest)
        return True
    except urllib.error.URLError as e:
        print(f"\n  ✗ 取得失敗: {e.reason}")
        tmp.unlink(missing_ok=True)
        return False
    except OSError as e:
        print(f"\n  ✗ 取得失敗: {e}")
        tmp.unlink(missing_ok=True)
        return False


class NoCacheHandler(SimpleHTTPRequestHandler):
    """開発中の旧版キャッシュ事故を防ぐ"""
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # アクセスログは黙らせる


def pick_port() -> int:
    for port in PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("8000-8010 がすべて使用中。他のサーバを止めてから再実行。")


def main() -> int:
    print("=" * 60)
    print(" Oculus 起動スクリプト")
    print("=" * 60)

    if not (BASE / "oculus.html").is_file():
        print("✗ oculus.html がこのスクリプトと同じフォルダにありません。")
        print(f"  配置場所: {BASE}")
        return 1

    # --- 1. ライブラリ点検・取得 ---
    missing = [(rel, url, ms) for rel, (url, ms) in FILES.items()
               if need_download(rel, ms)]
    if missing:
        print(f"\n不足ライブラリ {len(missing)} 件をダウンロードします...\n")
        failed = []
        for rel, url, ms in missing:
            if not download(rel, url, ms):
                failed.append((rel, url))
        if failed:
            print("\n" + "-" * 60)
            print("以下の取得に失敗しました。ブラウザで手動ダウンロードして")
            print("指定の場所に保存してから再実行してください:")
            for rel, url in failed:
                print(f"  保存先: {rel}")
                print(f"  URL   : {url}")
            print("-" * 60)
            print("※ SSL証明書エラーの場合は社内プロキシが原因の可能性が高い。")
            print("  その場合もブラウザ手動ダウンロードなら通ることが多い。")
            return 1
        print("\n✓ ライブラリ取得完了")
    else:
        print("✓ ライブラリは揃っています（ダウンロード省略）")

    # --- 2. サーバ起動 ---
    port = pick_port()
    url = f"http://127.0.0.1:{port}/oculus.html"
    handler = partial(NoCacheHandler, directory=str(BASE))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"\nサーバ起動: {url}")
    print("終了するには Ctrl+C（またはこのウィンドウを閉じる）\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバを停止しました。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
