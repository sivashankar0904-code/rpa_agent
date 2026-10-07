import json

from fastmcp import Client


async def test_lists_components(client: Client) -> None:
    tools = {t.name for t in await client.list_tools()}
    resources = {str(r.uri) for r in await client.list_resources()}
    prompts = {p.name for p in await client.list_prompts()}

    assert tools == {"read_file", "write_file", "list_dir"}
    assert resources == {"config://server"}
    assert prompts == {"summarize_file"}


async def test_write_read_list_roundtrip(client: Client) -> None:
    written = await client.call_tool("write_file", {"path": "out/a.txt", "content": "hi"})
    assert written.structured_content == {"path": "out/a.txt", "bytes_written": 2}

    read = await client.call_tool("read_file", {"path": "out/a.txt"})
    assert read.data == "hi"

    listed = await client.call_tool("list_dir", {"path": "out"})
    assert listed.structured_content == {
        "result": [{"path": "out/a.txt", "is_dir": False, "size": 2}]
    }


async def test_sandbox_violation_is_tool_error(client: Client) -> None:
    result = await client.call_tool("read_file", {"path": "../secret.txt"}, raise_on_error=False)

    assert result.is_error
    assert "outside the workspace" in result.content[0].text  # type: ignore[union-attr]


async def test_server_config_resource(client: Client) -> None:
    contents = await client.read_resource("config://server")
    config = json.loads(contents[0].text)  # type: ignore[union-attr]

    assert config["name"] == "rpa-agent"
    assert config["max_file_bytes"] == 1024


async def test_summarize_prompt(client: Client) -> None:
    result = await client.get_prompt("summarize_file", {"path": "a.txt", "max_words": "50"})
    text = result.messages[0].content.text  # type: ignore[union-attr]

    assert "a.txt" in text
    assert "50 words" in text
