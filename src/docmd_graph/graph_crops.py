"""Agent-guided deterministic graph cropping.

Flow:
1. An agent visually inspects page screenshots and returns JSON with text anchors.
2. This module finds those anchors in the reference PDF via PyMuPDF text search.
3. Crops are saved to media/ at a fixed DPI — no agent pixel-guessing needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docmd_graph.utils.filesystem import safe_relative
from docmd_graph.utils.json_tools import extract_json_object


@dataclass(frozen=True)
class CropSpec:
    filename: str
    page: int
    top_anchor: str
    bottom_anchor: str
    title: str


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower().replace("ё", "е")


def _find_anchor(page: Any, anchor: str) -> Any | None:
    """Find a text block whose normalised content contains *anchor*."""
    import fitz  # type: ignore[import-not-found]

    needle = _norm(anchor)
    best: Any = None
    best_len = float("inf")
    for item in page.get_text("blocks"):
        x0, y0, x1, y1, block_text = item[:5]
        normed = _norm(str(block_text))
        if needle in normed and len(normed) < best_len:
            best = fitz.Rect(x0, y0, x1, y1)
            best_len = len(normed)
    return best


def _clamp(rect: Any, page: Any) -> Any:
    import fitz  # type: ignore[import-not-found]

    return fitz.Rect(
        max(0, rect.x0),
        max(0, rect.y0),
        min(page.rect.x1, rect.x1),
        min(page.rect.y1, rect.y1),
    )


def crop_by_anchors(
    specs: list[CropSpec],
    work_dir: Path,
    media_dir: Path,
    *,
    dpi: int = 200,
    margin_pt: float = 8,
) -> tuple[list[str], list[str]]:
    """Crop regions from reference PDFs using text anchors.

    Returns (list of relative media paths, list of diagnostics).
    """
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return [], ["PyMuPDF not available; skipped anchor-based graph cropping."]

    screenshots_dir = work_dir / "screenshots"
    pdfs = sorted(p for p in screenshots_dir.glob("*.pdf") if p.is_file())
    if not pdfs:
        return [], ["No reference PDFs found for anchor-based cropping."]

    made: list[str] = []
    diagnostics: list[str] = []

    for pdf_path in pdfs:
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(f"Could not open {pdf_path.name}: {exc}")
            continue

        try:
            for spec in specs:
                page_idx = spec.page - 1
                if page_idx < 0 or page_idx >= len(doc):
                    diagnostics.append(f"{spec.filename}: page {spec.page} out of range (PDF has {len(doc)} pages).")
                    continue

                page = doc[page_idx]

                if spec.top_anchor == "__PAGE_TOP__":
                    top_y = 0
                else:
                    top_rect = _find_anchor(page, spec.top_anchor)
                    if not top_rect:
                        diagnostics.append(f"{spec.filename}: top anchor '{spec.top_anchor}' not found on page {spec.page}.")
                        continue
                    top_y = top_rect.y0 - margin_pt

                if spec.bottom_anchor == "__PAGE_BOTTOM__":
                    bottom_y = page.rect.y1
                else:
                    bottom_rect = _find_anchor(page, spec.bottom_anchor)
                    if not bottom_rect:
                        diagnostics.append(
                            f"{spec.filename}: bottom anchor '{spec.bottom_anchor}' not found on page {spec.page}."
                        )
                        continue
                    bottom_y = bottom_rect.y0 - margin_pt

                if bottom_y <= top_y + 20:
                    diagnostics.append(f"{spec.filename}: anchors too close (top_y={top_y:.0f}, bottom_y={bottom_y:.0f}).")
                    continue

                crop_rect = fitz.Rect(0, top_y, page.rect.x1, bottom_y)
                crop_rect = _clamp(crop_rect, page)

                zoom = dpi / 72
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=crop_rect, alpha=False)
                out_path = media_dir / spec.filename
                out_path.parent.mkdir(parents=True, exist_ok=True)
                pix.save(str(out_path))

                rel = safe_relative(out_path, media_dir.parent)
                made.append(rel)
                diagnostics.append(
                    f"Cropped {spec.filename} from page {spec.page} "
                    f"(top='{spec.top_anchor}' bottom='{spec.bottom_anchor}' "
                    f"rect={tuple(round(v, 1) for v in crop_rect)})"
                )
        finally:
            doc.close()

    return made, diagnostics


def parse_agent_crop_specs(agent_output: str) -> list[CropSpec]:
    """Parse agent JSON output into CropSpec list."""
    data = extract_json_object(agent_output)
    if not data or "crops" not in data:
        return []
    specs: list[CropSpec] = []
    for item in data["crops"]:
        try:
            specs.append(
                CropSpec(
                    filename=item["filename"],
                    page=int(item["page"]),
                    top_anchor=item["top_anchor"],
                    bottom_anchor=item["bottom_anchor"],
                    title=item.get("title", item["filename"]),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return specs


def crops_markdown(specs: list[CropSpec], media_rels: list[str]) -> str:
    """Build a Markdown snippet referencing the cropped images."""
    if not specs or not media_rels:
        return ""
    rel_by_name = {Path(r).name: r for r in media_rels}
    lines: list[str] = []
    for spec in specs:
        rel = rel_by_name.get(spec.filename)
        if rel:
            lines.append(f"![{spec.title}]({rel})")
            lines.append("")
    return "\n".join(lines)
