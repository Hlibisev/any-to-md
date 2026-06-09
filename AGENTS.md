# AGENTS.md

## Project purpose

This repository contains a Python library that converts documents and images into Markdown folders. The output contract is:

```text
output/
  blabla.md
  media/
```

## Development commands

```bash
uv sync --extra all --extra dev
uv run pytest
uv run ruff check .
uv run pyright
```

## Coding rules

- Keep prompts and documentation in English.
- Do not add network-only dependencies to the core path.
- Keep parsers best-effort and fail-soft: one broken parser should not fail the whole document if a fallback parser exists.
- Agents may edit only the final Markdown file and `media/` unless a human explicitly asks otherwise.
- Preserve source information. Do not summarize away lab values, table cells, references, captions, units, dates, or identifiers.
- Mark unreadable source content as `[unclear]` instead of guessing.
- This package must not provide medical advice when converting lab-result images.


## Usage

By default use opus-4.6-medium with cusror agent