from rpa_agent.tools.registry import ToolRegistry


def test_write_then_read(tmp_path):
    reg = ToolRegistry()
    p = str(tmp_path / "a.txt")
    reg.call("write_file", {"path": p, "content": "hi"})
    assert reg.call("read_file", {"path": p}) == "hi"


def test_unknown_tool():
    assert ToolRegistry().call("nope", {}).startswith("error")
