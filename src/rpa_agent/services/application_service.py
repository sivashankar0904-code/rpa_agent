"""Launch, monitor and terminate installed applications started by this server."""

import os
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath

import psutil

from rpa_agent.core.errors import (
    ApplicationBlockedError,
    ApplicationLaunchError,
    ApplicationNotFoundError,
    ApplicationNotInstalledError,
    ApplicationNotLaunchableError,
)
from rpa_agent.schemas.applications import AppStatus, InstalledApp
from rpa_agent.services import installed_apps

Catalog = Callable[[str | None], list[InstalledApp]]

_ADOPT_TIMEOUT = 10.0
_ADOPT_SETTLE = 0.5
_MAX_SUGGESTIONS = 10


@dataclass
class _ManagedApp:
    app_id: str
    name: str
    pid: int
    started_at: datetime
    # Processes that make up the app: the process we started, or for Store apps the processes
    # adopted from their package after launch.
    procs: list[psutil.Process]
    # Set only when the tracked process is our own child, which is what gives us an exit code.
    popen: subprocess.Popen[bytes] | None


# Set by Electron hosts (VS Code, Claude Desktop) for the processes they spawn, such as this
# server. If launched apps inherited it, every Electron app would start as plain Node and exit.
_STRIPPED_ENV = ("ELECTRON_RUN_AS_NODE",)


def _child_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k.upper() not in _STRIPPED_ENV}


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


def _store_procs(package: str, publisher: str, before: set[int]) -> list[psutil.Process]:
    """New processes whose executable lives in the Store package `package` (by publisher id)."""
    prefix, suffix = f"{package}_".lower(), f"__{publisher}".lower()
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(["exe"]):
        exe = proc.info["exe"]
        if proc.pid in before or not exe:
            continue
        parts = [p.lower() for p in PurePath(exe).parts]
        if "windowsapps" in parts:
            folder = parts[parts.index("windowsapps") + 1 : parts.index("windowsapps") + 2]
            if folder and folder[0].startswith(prefix) and folder[0].endswith(suffix):
                found.append(proc)
    return found


class ApplicationService:
    def __init__(
        self,
        blocked_apps: Iterable[str] = (),
        catalog: Catalog = installed_apps.list_installed,
    ) -> None:
        self._blocked = {b.strip().lower() for b in blocked_apps if b.strip()}
        self._catalog = catalog
        self._apps: dict[str, _ManagedApp] = {}
        self._lock = threading.Lock()

    def open(self, name: str, args: list[str] | None = None) -> AppStatus:
        """Launch the installed application matching `name` and return its initial status."""
        target = self._resolve(name)
        if self._is_blocked(target):
            raise ApplicationBlockedError(f"application is blocked: {target.name}")
        if not target.launchable or target.app_id is None:
            raise ApplicationNotLaunchableError(
                f"{target.name} is installed but cannot be launched and tracked by this server"
            )

        package = installed_apps.store_package(target.app_id)
        if package:
            if args:
                raise ApplicationLaunchError("arguments are not supported for Store apps")
            return self._register(target.name, self._launch_store(target.app_id, package), None)

        exe = installed_apps.resolve_exe(target.app_id)
        if exe is None:  # launchable was true a moment ago; the file has since gone
            raise ApplicationNotLaunchableError(f"executable for {target.name} no longer exists")
        # No shell, and output is discarded so an unread pipe can never block the child.
        popen = subprocess.Popen(
            [str(exe), *(args or [])],
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            procs = [psutil.Process(popen.pid)]
        except psutil.NoSuchProcess:  # exited before we could attach; popen has the exit code
            procs = []
        return self._register(target.name, procs, popen, pid=popen.pid)

    def list_installed(self, query: str | None = None) -> list[InstalledApp]:
        """Applications installed on this machine, optionally filtered by name substring."""
        return self._catalog(query)

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

    def _resolve(self, name: str) -> InstalledApp:
        """Find the installed app for `name`: an exact name match, else a unique substring."""
        matches = self._catalog(name)
        exact = [a for a in matches if a.name.lower() == name.strip().lower()]
        if len(exact) == 1:
            return exact[0]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ApplicationNotInstalledError(f"no installed application matches: {name}")
        shown = ", ".join(a.name for a in matches[:_MAX_SUGGESTIONS])
        more = (
            f" (+{len(matches) - _MAX_SUGGESTIONS} more)" if len(matches) > _MAX_SUGGESTIONS else ""
        )
        raise ApplicationNotInstalledError(f"{name!r} is ambiguous; matches: {shown}{more}")

    def _is_blocked(self, app: InstalledApp) -> bool:
        candidates = {app.name.lower()}
        if app.app_id:
            if package := installed_apps.store_package(app.app_id):
                candidates.add(package[0].lower())
            if exe := installed_apps.resolve_exe(app.app_id):
                candidates |= {exe.name.lower(), exe.stem.lower()}
        return not self._blocked.isdisjoint(candidates)

    @staticmethod
    def _launch_store(app_id: str, package: tuple[str, str]) -> list[psutil.Process]:
        """Start a Store app through the shell, then adopt its processes for tracking."""
        before = {p.pid for p in psutil.process_iter()}
        subprocess.Popen(
            ["explorer.exe", rf"shell:AppsFolder\{app_id}"],
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + _ADOPT_TIMEOUT
        while time.monotonic() < deadline:
            if _store_procs(*package, before):
                # A moment later, pick up sibling processes the app spawned alongside.
                time.sleep(_ADOPT_SETTLE)
                return _store_procs(*package, before)
            time.sleep(0.1)
        raise ApplicationLaunchError(
            f"started {package[0]} but no new process appeared within {_ADOPT_TIMEOUT:.0f}s; "
            "it may have reused an already-running instance, so it cannot be tracked or "
            "terminated by this server"
        )

    def _register(
        self,
        name: str,
        procs: list[psutil.Process],
        popen: subprocess.Popen[bytes] | None,
        pid: int | None = None,
    ) -> AppStatus:
        app = _ManagedApp(
            uuid.uuid4().hex[:8],
            name,
            pid if pid is not None else procs[0].pid,
            datetime.now(UTC),
            procs,
            popen,
        )
        with self._lock:
            self._apps[app.app_id] = app
        return self._status(app)

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
            exit_code=exit_code,
            started_at=app.started_at,
        )
