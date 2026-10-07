"""Launch, monitor and terminate allowlisted applications started by this server."""

import subprocess
import threading
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import psutil

from rpa_agent.core.errors import (
    ApplicationLaunchError,
    ApplicationNotAllowedError,
    ApplicationNotFoundError,
)
from rpa_agent.schemas.applications import AppSpec, AppStatus

_ADOPT_TIMEOUT = 10.0
_ADOPT_SETTLE = 0.5


@dataclass
class _ManagedApp:
    app_id: str
    name: str
    pid: int
    started_at: datetime
    # Processes that make up the app. For launcher-stub apps these are the adopted real
    # processes; otherwise just the process we started.
    procs: list[psutil.Process]
    # Set only when the tracked process is our own child, which is what gives us an exit code.
    popen: subprocess.Popen[bytes] | None


def _alive(proc: psutil.Process) -> bool:
    try:
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def _family(procs: list[psutil.Process]) -> list[psutil.Process]:
    """`procs` plus all their living descendants, de-duplicated by pid."""
    seen: dict[int, psutil.Process] = {}
    for proc in procs:
        seen[proc.pid] = proc
        try:
            for child in proc.children(recursive=True):
                seen[child.pid] = child
        except psutil.NoSuchProcess:
            continue
    return list(seen.values())


def _find_new(process_name: str, before: set[int]) -> list[psutil.Process]:
    wanted = process_name.lower()
    return [
        p
        for p in psutil.process_iter(["name"])
        if p.pid not in before and (p.info["name"] or "").lower() == wanted
    ]


class ApplicationService:
    def __init__(self, allowed_apps: Mapping[str, AppSpec]) -> None:
        self._allowed = dict(allowed_apps)
        self._apps: dict[str, _ManagedApp] = {}
        self._lock = threading.Lock()

    def open(self, name: str, args: list[str] | None = None) -> AppStatus:
        """Start the allowlisted application `name` and return its initial status."""
        spec = self._allowed.get(name)
        if spec is None:
            allowed = ", ".join(sorted(self._allowed)) or "none configured"
            raise ApplicationNotAllowedError(
                f"application not allowed: {name} (allowed: {allowed})"
            )
        before = {p.pid for p in psutil.process_iter()} if spec.process_name else set()
        # No shell, and output is discarded so an unread pipe can never block the child.
        popen = subprocess.Popen(
            [spec.command, *(args or [])],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if spec.process_name:
            procs = self._adopt(spec.command, spec.process_name, before)
            app = _ManagedApp(
                uuid.uuid4().hex[:8], name, procs[0].pid, datetime.now(UTC), procs, None
            )
        else:
            try:
                procs = [psutil.Process(popen.pid)]
            except psutil.NoSuchProcess:  # exited before we could attach; popen has the exit code
                procs = []
            app = _ManagedApp(
                uuid.uuid4().hex[:8], name, popen.pid, datetime.now(UTC), procs, popen
            )
        with self._lock:
            self._apps[app.app_id] = app
        return self._status(app)

    def status(self, app_id: str) -> AppStatus:
        return self._status(self._get(app_id))

    def list_apps(self) -> list[AppStatus]:
        with self._lock:
            apps = list(self._apps.values())
        return [self._status(app) for app in apps]

    def terminate(self, app_id: str, timeout: float = 5.0) -> AppStatus:
        """Ask the app's processes to exit, killing any still alive after `timeout` seconds."""
        app = self._get(app_id)
        targets = [p for p in _family(app.procs) if _alive(p)]
        for proc in targets:
            try:
                proc.terminate()
            except psutil.NoSuchProcess:
                continue
        _, survivors = psutil.wait_procs(targets, timeout)
        for proc in survivors:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                continue
        psutil.wait_procs(survivors, timeout)
        return self._status(app)

    @staticmethod
    def _adopt(command: str, process_name: str, before: set[int]) -> list[psutil.Process]:
        """Wait for the real process behind a launcher stub to appear, and track it."""
        deadline = time.monotonic() + _ADOPT_TIMEOUT
        while time.monotonic() < deadline:
            if _find_new(process_name, before):
                # A moment later, pick up sibling processes the app spawned alongside.
                time.sleep(_ADOPT_SETTLE)
                return _find_new(process_name, before)
            time.sleep(0.1)
        raise ApplicationLaunchError(
            f"started {command} but no new {process_name} process appeared within "
            f"{_ADOPT_TIMEOUT:.0f}s; it may have reused an already-running instance, so it "
            "cannot be tracked or terminated by this server"
        )

    def _get(self, app_id: str) -> _ManagedApp:
        with self._lock:
            app = self._apps.get(app_id)
        if app is None:
            raise ApplicationNotFoundError(f"no such application: {app_id}")
        return app

    @staticmethod
    def _status(app: _ManagedApp) -> AppStatus:
        running = any(_alive(p) for p in _family(app.procs))
        # Read the exit code only after liveness, so a process that just exited isn't missed.
        exit_code = app.popen.poll() if app.popen and not running else None
        return AppStatus(
            app_id=app.app_id,
            name=app.name,
            pid=app.pid,
            state="running" if running else "exited",
            exit_code=None if running else exit_code,
            started_at=app.started_at,
        )
