from pathlib import Path

from docmd_graph import RunConfig, convert

result = convert(
    inputs=[Path("scan.pdf"), Path("photo.jpg")],
    output_dir=Path("output"),
    config=RunConfig(agent="none", output_name="blabla.md"),
)
print(result.markdown_path)
print(result.audit_report.ok)
