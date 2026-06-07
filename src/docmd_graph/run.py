from __future__ import annotations

from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.graph import build_graph, cleanup_workdir, prepare_initial_state
from docmd_graph.models import AuditReport, ConversionResult, ParserResult


def convert(inputs: list[Path], output_dir: Path, config: RunConfig | None = None) -> ConversionResult:
    """Run the LangGraph conversion pipeline."""
    cfg = config or RunConfig()
    output_dir = output_dir.resolve()
    input_paths = [Path(p).resolve() for p in inputs]
    state = prepare_initial_state(input_paths, output_dir, cfg)
    graph = build_graph()
    final_state = graph.invoke(state)

    parser_results = [ParserResult.model_validate(item) for item in final_state.get("parser_results", [])]
    audit_report = AuditReport.model_validate(final_state.get("audit_report", {}))
    result = ConversionResult(
        output_dir=str(output_dir),
        markdown_path=str(output_dir / cfg.output_name),
        media_dir=str(output_dir / "media"),
        parser_results=parser_results,
        audit_report=audit_report,
        fix_rounds=int(final_state.get("audit_round", 0)),
        work_dir=str(output_dir / "_work") if cfg.keep_workdir else None,
    )
    cleanup_workdir(final_state)
    return result
