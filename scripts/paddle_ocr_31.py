"""OCR 16 photos from 31 больница using PaddleOCR and produce markdown."""

import os
from pathlib import Path

from paddleocr import PaddleOCR

INPUT_DIR = Path(
    "/Users/antonfonin/Downloads/"
    "31 больница, гипертония. Декабрь 2022 (левая рука, старался для военкомата)"
)
OUTPUT_MD = Path("/Users/antonfonin/docmd_graph/output/31bolnitsa-2022-12/paddle_ocr.md")

ocr = PaddleOCR(
    lang="ru",
    device="cpu",
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=True,
)

files = sorted(INPUT_DIR.glob("*.jpeg"), key=lambda p: p.name)

sections = []
for img_path in files:
    print(f"Processing: {img_path.name}")
    texts = []
    for res in ocr.predict(str(img_path)):
        data = res.json.get("res", res.json)
        texts.extend(t for t in data.get("rec_texts", []) if t.strip())

    section = f"## {img_path.name}\n\n" + "\n".join(texts)
    sections.append(section)

md = "# 31 больница, гипертония. Декабрь 2022\n\n" + "\n\n".join(sections) + "\n"
OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_MD.write_text(md, encoding="utf-8")
print(f"\nDone → {OUTPUT_MD}")
