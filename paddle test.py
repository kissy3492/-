# -*- coding: utf-8 -*-
"""
PaddleOCR 精度検証スクリプト（Step 1: Tesseract/Oculus との比較用）

使い方:
    python paddle_test.py 検証したい画像またはPDF

  ・初回実行時はモデルを自動ダウンロードする（要ネット接続・以後は不要）
  ・結果は画面表示に加えて ocr_result.tsv に保存（信頼度付き）
  ・PDFの場合は pip install pymupdf が追加で必要（画像ならそのままでよい）
"""

import sys
from pathlib import Path

OUT_TSV = "ocr_result.tsv"


def pdf_to_images(pdf_path: Path, dpi: int = 300):
    """PDFを1ページずつPNGに変換して画像パスのリストを返す"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PDFを読むには追加で:  pip install pymupdf")
        sys.exit(1)
    doc = fitz.open(pdf_path)
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        p = pdf_path.with_name(f"{pdf_path.stem}_p{i+1}.png")
        pix.save(p)
        paths.append(p)
        print(f"  ページ{i+1} -> {p.name} ({pix.width}x{pix.height}px)")
    doc.close()
    return paths


def extract_rows(res):
    """PaddleOCRの結果オブジェクトから (text, score) の列を取り出す。
    3.x(predict) / 2.x(ocr) どちらの形式にも対応"""
    rows = []
    # 3.x: dict風アクセスで rec_texts / rec_scores を持つ
    try:
        texts = res["rec_texts"]
        scores = res["rec_scores"]
        return list(zip(texts, scores))
    except (TypeError, KeyError, IndexError):
        pass
    # 2.x: [ [box, (text, score)], ... ]
    try:
        for line in res:
            box, (text, score) = line
            rows.append((text, score))
        return rows
    except (TypeError, ValueError):
        pass
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("使い方: python paddle_test.py 画像またはPDFのパス")
        return 1
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"ファイルが見つからない: {src}")
        return 1

    images = [src]
    if src.suffix.lower() == ".pdf":
        print("PDFを画像化中...")
        images = pdf_to_images(src)

    print("PaddleOCR を初期化中（初回はモデル自動ダウンロード）...")
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="japan")

    all_rows = []
    for img in images:
        print(f"\n=== {img.name} ===")
        # 3.x は predict、2.x は ocr
        if hasattr(ocr, "predict"):
            results = ocr.predict(str(img))
        else:
            results = ocr.ocr(str(img))
        for res in results:
            rows = extract_rows(res)
            for text, score in rows:
                mark = "" if score >= 0.90 else "  <= 要確認"
                print(f"  [{score:.3f}] {text}{mark}")
                all_rows.append((img.name, text, score))

    with open(OUT_TSV, "w", encoding="utf-8", newline="") as f:
        f.write("ファイル\t認識テキスト\t信頼度\n")
        for name, text, score in all_rows:
            text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
            f.write(f"{name}\t{text}\t{score:.4f}\n")

    n = len(all_rows)
    low = sum(1 for _, _, s in all_rows if s < 0.90)
    print(f"\n認識 {n} 行 / 信頼度0.90未満 {low} 行")
    print(f"結果を {OUT_TSV} に保存した。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
