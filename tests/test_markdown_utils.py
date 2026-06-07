from pathlib import Path

from docmd_graph.audit.heuristics import audit_markdown
from docmd_graph.utils.markdown import find_image_refs, normalize_markdown_text, rewrite_absolute_media_links


def test_find_image_refs() -> None:
    md = "![a](media/a.png) ![b](https://example.com/b.png) [x](media/c.png)"
    assert find_image_refs(md) == ["media/a.png"]


def test_rewrite_absolute_media_links(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    img = output / "media" / "x.png"
    img.parent.mkdir()
    img.write_bytes(b"x")
    md = f"![x]({img})"
    assert rewrite_absolute_media_links(md, output) == "![x](media/x.png)"


def test_normalize_markdown_text() -> None:
    assert normalize_markdown_text("a\r\n\r\n\r\n\r\nb").endswith("\n")


def test_audit_missing_media(tmp_path: Path) -> None:
    output = tmp_path / "blabla.md"
    media = tmp_path / "media"
    media.mkdir()
    output.write_text("# X\n\n![missing](media/missing.png)\n", encoding="utf-8")
    report = audit_markdown(output, media)
    assert not report.ok
    assert report.media_problems == ["media/missing.png"]
