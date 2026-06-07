from docmd_graph.utils.json_tools import extract_json_object


def test_extract_plain_json() -> None:
    assert extract_json_object('{"ok": true}') == {"ok": True}


def test_extract_fenced_json() -> None:
    text = 'Here:\n```json\n{"ok": false, "issues": []}\n```'
    assert extract_json_object(text) == {"ok": False, "issues": []}
