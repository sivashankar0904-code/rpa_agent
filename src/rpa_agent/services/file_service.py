"""Sandboxed file operations rooted at a workspace directory."""

from pathlib import Path

from rpa_agent.core.errors import FileTooLargeError, WorkspaceAccessError
from rpa_agent.schemas.files import FileInfo, WriteResult


class FileService:
    def __init__(self, workspace_dir: Path, max_file_bytes: int = 1_000_000) -> None:
        self.root = workspace_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def safe_resolve(self, path: str) -> Path:
        """Resolve `path` relative to the workspace, rejecting anything that escapes it."""
        resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise WorkspaceAccessError(f"path is outside the workspace: {path}")
        return resolved

    def _relative(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix() or "."

    def read_text(self, path: str) -> str:
        p = self.safe_resolve(path)
        if not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        if p.stat().st_size > self.max_file_bytes:
            raise FileTooLargeError(f"file exceeds {self.max_file_bytes} bytes: {path}")
        return p.read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> WriteResult:
        data = content.encode("utf-8")
        if len(data) > self.max_file_bytes:
            raise FileTooLargeError(f"content exceeds {self.max_file_bytes} bytes")
        p = self.safe_resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return WriteResult(path=self._relative(p), bytes_written=len(data))

    def list_dir(self, path: str = ".") -> list[FileInfo]:
        p = self.safe_resolve(path)
        if not p.is_dir():
            raise NotADirectoryError(f"not a directory: {path}")
        return [
            FileInfo(
                path=self._relative(child),
                is_dir=child.is_dir(),
                size=0 if child.is_dir() else child.stat().st_size,
            )
            for child in sorted(p.iterdir())
        ]
