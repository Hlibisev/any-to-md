from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def slugify(value: str, default: str = "document") -> str:
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"[^\w\-.]+", "-", value, flags=re.UNICODE).strip("-_.")
    value = re.sub(r"-+", "-", value)
    return value[:80] or default


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for idx in range(1, 10000):
        candidate = parent / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate unique path near {path}")


def copy_file_unique(src: Path, dest_dir: Path, name: str | None = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = name or src.name
    dest = unique_path(dest_dir / filename)
    shutil.copy2(src, dest)
    return dest


def safe_relative(path: Path, start: Path) -> str:
    try:
        return path.resolve().relative_to(start.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def walk_inputs(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and not child.name.startswith("."):
                    files.append(child)
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"Input path does not exist: {path}")
    return files
