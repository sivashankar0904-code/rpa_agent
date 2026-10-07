"""Structured outputs for file tools."""

from pydantic import BaseModel


class FileInfo(BaseModel):
    path: str
    is_dir: bool
    size: int


class WriteResult(BaseModel):
    path: str
    bytes_written: int
