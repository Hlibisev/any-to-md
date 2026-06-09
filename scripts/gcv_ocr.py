"""OCR photos using Google Cloud Vision and produce markdown."""

import sys
from pathlib import Path

from google.cloud import vision


def ocr_image(client: vision.ImageAnnotatorClient, path: Path) -> str:
    content = path.read_bytes()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    if response.error.message:
        return f"[ERROR: {response.error.message}]"
    return response.full_text_annotation.text if response.full_text_annotation.text else "[no text detected]"


def process_folder(input_dir: Path, output_path: Path):
    client = vision.ImageAnnotatorClient()
    files = sorted(input_dir.glob("*.jpeg")) + sorted(input_dir.glob("*.jpg")) + sorted(input_dir.glob("*.png"))
    if not files:
        files = sorted(input_dir.glob("*.JPEG")) + sorted(input_dir.glob("*.JPG"))
    files = sorted(set(files), key=lambda p: p.name)

    sections = []
    for img_path in files:
        print(f"  {img_path.name} ... ", end="", flush=True)
        text = ocr_image(client, img_path)
        print(f"{len(text)} chars")
        sections.append(f"## {img_path.name}\n\n```\n{text}\n```")

    md = f"# {input_dir.name}\n\n" + "\n\n".join(sections) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"  → {output_path}")


if __name__ == "__main__":
    folders = [
        (
            Path("/Users/antonfonin/Downloads/31 больница, гипертония. Декабрь 2022 (левая рука, старался для военкомата)"),
            Path("/Users/antonfonin/docmd_graph/output/31bolnitsa-2022-12/gcv_ocr.md"),
        ),
        (
            Path("/Users/antonfonin/Downloads/Николаевская больница, гипертония. Июнь 2019 (левая рука, старался для военкомата)"),
            Path("/Users/antonfonin/docmd_graph/output/nikolaevskaya-2019-06/gcv_ocr.md"),
        ),
    ]

    for input_dir, output_path in folders:
        print(f"\n{'='*60}")
        print(f"Processing: {input_dir.name}")
        print(f"{'='*60}")
        if not input_dir.exists():
            print(f"  SKIP — folder not found")
            continue
        process_folder(input_dir, output_path)

    print("\nDone!")
