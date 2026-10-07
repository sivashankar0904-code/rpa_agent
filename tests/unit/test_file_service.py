from pathlib import Path

import pytest

from rpa_agent.core.errors import FileTooLargeError, WorkspaceAccessError
from rpa_agent.services.file_service import FileService


def test_write_then_read_roundtrip(file_service: FileService) -> None:
    result = file_service.write_text("notes/a.txt", "hello")

    assert result.path == "notes/a.txt"
    assert result.bytes_written == 5
    assert file_service.read_text("notes/a.txt") == "hello"


def test_list_dir(file_service: FileService) -> None:
    file_service.write_text("a.txt", "x")
    file_service.write_text("sub/b.txt", "yy")

    entries = {e.path: e for e in file_service.list_dir()}

    assert set(entries) == {"a.txt", "sub"}
    assert entries["sub"].is_dir
    assert entries["a.txt"].size == 1


@pytest.mark.parametrize("path", ["../escape.txt", "sub/../../escape.txt"])
def test_rejects_paths_outside_workspace(file_service: FileService, path: str) -> None:
    with pytest.raises(WorkspaceAccessError):
        file_service.write_text(path, "nope")


def test_rejects_absolute_path_outside_workspace(file_service: FileService, tmp_path: Path) -> None:
    with pytest.raises(WorkspaceAccessError):
        file_service.read_text(str(tmp_path / "outside.txt"))


def test_rejects_oversized_content(file_service: FileService) -> None:
    with pytest.raises(FileTooLargeError):
        file_service.write_text("big.txt", "x" * 2048)


def test_read_missing_file(file_service: FileService) -> None:
    with pytest.raises(FileNotFoundError):
        file_service.read_text("missing.txt")
