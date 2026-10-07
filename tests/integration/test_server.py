import json

from fastmcp import Client


async def test_lists_components(client: Client) -> None:
    tools = {t.name for t in await client.list_tools()}
    resources = {str(r.uri) for r in await client.list_resources()}
    prompts = {p.name for p in await client.list_prompts()}

    assert tools == {
        "read_file",
        "write_file",
        "list_dir",
        "open_application",
        "get_application_status",
        "list_applications",
        "list_installed_applications",
        "terminate_application",
    }
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


async def test_application_open_status_terminate(client: Client) -> None:
    opened = await client.call_tool(
        "open_application", {"name": "Test Python", "args": ["-c", "import time; time.sleep(60)"]}
    )
    app_id = opened.structured_content["app_id"]  # type: ignore[index]
    assert opened.structured_content["state"] == "running"  # type: ignore[index]

    status = await client.call_tool("get_application_status", {"app_id": app_id})
    assert status.structured_content["state"] == "running"  # type: ignore[index]

    terminated = await client.call_tool("terminate_application", {"app_id": app_id})
    assert terminated.structured_content["state"] == "exited"  # type: ignore[index]


async def test_list_installed_applications(client: Client) -> None:
    result = await client.call_tool("list_installed_applications", {"query": "docs"})

    apps = result.structured_content["result"]  # type: ignore[index]
    assert [a["name"] for a in apps] == ["Docs Only"]
    assert apps[0]["launchable"] is False


async def test_blocked_application_is_tool_error(client: Client) -> None:
    result = await client.call_tool(
        "open_application", {"name": "Shell Thing"}, raise_on_error=False
    )

    assert result.is_error
    assert "blocked" in result.content[0].text  # type: ignore[union-attr]


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
