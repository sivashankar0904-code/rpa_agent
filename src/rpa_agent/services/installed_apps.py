"""Enumerate applications installed on this Windows machine and work out how to launch them.

Launchable apps come from the Start menu (`Get-StartApps`); registry "Uninstall" entries add
version/publisher metadata and list installed software that has no Start-menu entry.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from rpa_agent.core.errors import CatalogUnavailableError, UnsupportedPlatformError
from rpa_agent.schemas.applications import InstalledApp

_UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
_START_APPS_TIMEOUT = 20.0

# Known-folder GUIDs that Start-menu AppIDs use as a path prefix, e.g. `{GUID}\Git\cmd\git-gui.exe`.
_KNOWN_FOLDERS = {
    "6D809377-6AF0-444B-8957-A3773F02200E": lambda: os.environ.get("PROGRAMW6432"),
    "7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E": lambda: os.environ.get("PROGRAMFILES(X86)"),
    "905E63B6-C1BF-494E-B29C-65B732D3D21A": lambda: os.environ.get("PROGRAMFILES"),
    "62AB5D82-FDC1-4DC3-A9DD-070D1D495D97": lambda: os.environ.get("PROGRAMDATA"),
    "F1B32785-6FBA-4FCF-9D55-7B8E7F157091": lambda: os.environ.get("LOCALAPPDATA"),
    "3EB685DB-65F9-4CF6-A03A-E3EF65729F3D": lambda: os.environ.get("APPDATA"),
    "F38BF404-1D43-42F2-9305-67DE0B28FC23": lambda: os.environ.get("SYSTEMROOT"),
    "1AC14E77-02E7-4E5D-B744-2EB1AE5198B7": lambda: _under_system_root("System32"),
    "D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27": lambda: _under_system_root("SysWOW64"),
}


def list_installed(query: str | None = None) -> list[InstalledApp]:
    """Installed apps sorted by name, optionally filtered by a case-insensitive name substring."""
    if sys.platform != "win32":
        raise UnsupportedPlatformError(
            "listing installed applications is only supported on Windows"
        )
    registry: dict[str, tuple[InstalledApp, Path | None]] = {}
    for app, exe in _registry_apps():
        registry.setdefault(app.name.lower(), (app, exe))

    apps: dict[str, InstalledApp] = {}
    for app in _start_apps():
        key = app.name.lower()
        match = registry.pop(key, None)
        if match is None and not app.launchable:
            match = _pop_versioned(registry, key)
        if match:
            meta, exe = match
            update: dict[str, Any] = {"version": meta.version, "publisher": meta.publisher}
            if not app.launchable and exe:
                # The Start entry has only an opaque app id (e.g. Electron apps); the registry
                # entry for the same product knows the real executable.
                update |= {"app_id": str(exe), "launchable": True}
            app = app.model_copy(update=update)
        apps.setdefault(app.name.lower(), app)
    for app, _ in registry.values():
        apps.setdefault(app.name.lower(), app)

    needle = (query or "").strip().lower()
    return sorted(
        (a for a in apps.values() if needle in a.name.lower()), key=lambda a: a.name.lower()
    )


def _pop_versioned(
    registry: dict[str, tuple[InstalledApp, Path | None]], start_name: str
) -> tuple[InstalledApp, Path | None] | None:
    """Pop the one registry entry named like "<start_name> <version>" that has an executable."""
    candidates = [
        key for key, (_, exe) in registry.items() if key.startswith(f"{start_name} ") and exe
    ]
    return registry.pop(candidates[0]) if len(candidates) == 1 else None


def resolve_exe(app_id: str) -> Path | None:
    """The `.exe` a desktop Start-menu AppID points at, or None if it isn't a plain executable."""
    path: Path | None
    if app_id.startswith("{") and "}\\" in app_id:
        guid, rest = app_id[1:].split("}\\", 1)
        resolver = _KNOWN_FOLDERS.get(guid.upper())
        base = resolver() if resolver else None
        path = Path(base) / rest if base else None
    else:
        path = Path(app_id)
    if path is not None and path.suffix.lower() == ".exe" and path.is_file():
        return path
    return None


def store_package(app_id: str) -> tuple[str, str] | None:
    """(package name, publisher id) for a Store AppID `<Name>_<publisherId>!<App>`, else None."""
    family, sep, _ = app_id.partition("!")
    name, _, publisher = family.rpartition("_")
    return (name, publisher) if sep and name and publisher else None


def _under_system_root(folder: str) -> str | None:
    root = os.environ.get("SYSTEMROOT")
    return str(Path(root) / folder) if root else None


def _start_apps() -> list[InstalledApp]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-StartApps | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=_START_APPS_TIMEOUT,
            check=True,
        )
        data = json.loads(result.stdout or "[]")
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        raise CatalogUnavailableError(f"could not read the Start menu app list: {e}") from e

    apps: list[InstalledApp] = []
    for entry in [data] if isinstance(data, dict) else data:
        name, app_id = entry.get("Name"), entry.get("AppID")
        if not name or not app_id:
            continue
        source: Literal["store", "desktop"]
        if "!" in app_id:
            source, launchable = "store", store_package(app_id) is not None
        else:
            source, launchable = "desktop", resolve_exe(app_id) is not None
        apps.append(
            InstalledApp(
                name=name,
                version=None,
                publisher=None,
                source=source,
                app_id=app_id,
                launchable=launchable,
            )
        )
    return apps


def _registry_apps() -> list[tuple[InstalledApp, Path | None]]:
    import winreg

    def value(key: Any, name: str) -> Any:
        try:
            return winreg.QueryValueEx(key, name)[0]
        except OSError:
            return None

    found: list[tuple[InstalledApp, Path | None]] = []
    for hive, view in (
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    ):
        try:
            root = winreg.OpenKey(hive, _UNINSTALL, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                try:
                    sub = winreg.OpenKey(root, winreg.EnumKey(root, i))
                except OSError:
                    continue
                with sub:
                    name = value(sub, "DisplayName")
                    # Skip hidden system components and patches/updates of other products.
                    if (
                        not name
                        or value(sub, "SystemComponent") == 1
                        or value(sub, "ParentKeyName")
                    ):
                        continue
                    app = InstalledApp(
                        name=str(name),
                        version=_text(value(sub, "DisplayVersion")),
                        publisher=_text(value(sub, "Publisher")),
                        source="registry",
                        app_id=None,
                        launchable=False,
                    )
                    found.append((app, _icon_exe(value(sub, "DisplayIcon"))))
    return found


def _icon_exe(raw: Any) -> Path | None:
    """The executable named by a registry DisplayIcon (a quoted path plus icon index), if real.

    Uninstallers and installers are rejected so they can never be mistaken for the app itself.
    """
    if not raw:
        return None
    path = re.sub(r",\s*-?\d+$", "", str(raw).strip()).strip().strip('"')
    exe = Path(os.path.expandvars(path))
    stem = exe.stem.lower()
    if exe.suffix.lower() != ".exe" or not exe.is_file():
        return None
    if stem.startswith(("unins", "setup", "install")) or "uninstall" in stem:
        return None
    return exe


def _text(raw: Any) -> str | None:
    return str(raw) if raw else None
