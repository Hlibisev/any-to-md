from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from docmd_graph.config import AgentName, ParserName, RunConfig
from docmd_graph.parsers.router import get_available_parsers
from docmd_graph.run import convert as run_convert

app = typer.Typer(help="Convert documents/images into a Markdown folder with media and audit/fix loops.")
console = Console()


@app.command("parsers")
def parsers() -> None:
    """Show parser availability in the current environment."""
    table = Table(title="Parser availability")
    table.add_column("Parser")
    table.add_column("Available")
    for name, available in get_available_parsers().items():
        table.add_row(name, "yes" if available else "no")
    console.print(table)


@app.command("convert")
def convert_cmd(
    inputs: Annotated[list[Path], typer.Argument(help="Input files or folders.")],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output folder.")],
    output_name: Annotated[str, typer.Option(help="Markdown filename inside output folder.")] = "blabla.md",
    parser: Annotated[ParserName, typer.Option(help="Parser backend or auto router.")] = "auto",
    agent: Annotated[AgentName, typer.Option(help="Agent backend: none, codex, or cursor.")] = "none",
    max_fix_rounds: Annotated[int, typer.Option(help="Maximum audit/fix loop count.")] = 2,
    keep_workdir: Annotated[bool, typer.Option(help="Keep _work/ with raw parser output and logs.")] = False,
    fail_on_audit: Annotated[bool, typer.Option(help="Exit non-zero when final audit is not OK.")] = False,
    ocr: Annotated[bool, typer.Option("--ocr/--no-ocr", help="Enable Google Cloud Vision OCR for standalone images.")] = False,
    ocr_languages: Annotated[str, typer.Option(help="OCR language hints (unused by GCV, kept for compat).")] = "eng+rus",
    model: Annotated[str | None, typer.Option(help="Agent model override.")] = None,
    codex_bin: Annotated[str, typer.Option(help="Codex CLI executable.")] = "codex",
    cursor_bin: Annotated[str, typer.Option(help="Cursor Agent executable.")] = "cursor-agent",
    clean: Annotated[bool, typer.Option("--clean/--no-clean", help="Clean known output files before running.")] = True,
) -> None:
    """Run conversion."""
    config = RunConfig(
        parser=parser,
        agent=agent,
        output_name=output_name,
        max_fix_rounds=max_fix_rounds,
        keep_workdir=keep_workdir,
        fail_on_audit=fail_on_audit,
        enable_ocr=ocr,
        ocr_languages=ocr_languages,
        model=model,
        codex_bin=codex_bin,
        cursor_bin=cursor_bin,
        clean_existing_output=clean,
    )
    result = run_convert(list(inputs), out, config)

    console.print(f"[bold green]Markdown:[/bold green] {result.markdown_path}")
    console.print(f"[bold green]Media:[/bold green] {result.media_dir}")
    console.print(f"[bold]Audit OK:[/bold] {result.audit_report.ok}  score={result.audit_report.score:.2f}")
    if result.work_dir:
        console.print(f"[bold]Work dir:[/bold] {result.work_dir}")
    if result.audit_report.issues:
        table = Table(title="Audit issues")
        table.add_column("Severity")
        table.add_column("Location")
        table.add_column("Problem")
        for issue in result.audit_report.issues:
            table.add_row(issue.severity, issue.location, issue.problem)
        console.print(table)

    summary_path = Path(result.output_dir) / "conversion_result.json"
    if keep_workdir:
        summary_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[bold]Result JSON:[/bold] {summary_path}")
    else:
        # Keep stdout parsable without adding files to the two-item output contract.
        console.print_json(json.dumps(result.model_dump(), ensure_ascii=False))

    if fail_on_audit and not result.audit_report.ok:
        raise typer.Exit(code=2)

if __name__ == "__main__":
    app()
