import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from rpa_agent.core.errors import (
    ApplicationBlockedError,
    ApplicationLaunchError,
    ApplicationNotFoundError,
    ApplicationNotInstalledError,
    ApplicationNotLaunchableError,
    UnsupportedPlatformError,
)
from rpa_agent.schemas.applications import InstalledApp
from rpa_agent.services import installed_apps
from rpa_agent.services.application_service import ApplicationService

SLEEP = ["-c", "import time; time.sleep(60)"]


def test_open_reports_running(application_service: ApplicationService) -> None:
    app = application_service.open("Test Python", SLEEP)

    assert app.state == "running"
    assert app.exit_code is None
    assert app.name == "Test Python"
    assert application_service.status(app.app_id).pid == app.pid


def test_open_matches_unique_substring_case_insensitively(
    application_service: ApplicationService,
) -> None:
    assert application_service.open("python tools", SLEEP).name == "Test Python Tools"


def test_exact_name_wins_over_longer_matches(application_service: ApplicationService) -> None:
    # "Test Python" also matches "Test Python Tools", but is an exact match for the first.
    assert application_service.open("test python", SLEEP).name == "Test Python"


def test_status_reports_exit_code_after_process_ends(
    application_service: ApplicationService,
) -> None:
    app = application_service.open("Test Python", ["-c", "raise SystemExit(3)"])

    deadline = time.monotonic() + 10
    status = application_service.status(app.app_id)
    while status.state == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        status = application_service.status(app.app_id)

    assert status.state == "exited"
    assert status.exit_code == 3

    # Terminating an already-finished process is a no-op that keeps the real exit code.
    assert application_service.terminate(app.app_id).exit_code == 3


def test_terminate_stops_running_process(application_service: ApplicationService) -> None:
    app = application_service.open("Test Python", SLEEP)

    result = application_service.terminate(app.app_id)

    assert result.state == "exited"
    assert application_service.status(app.app_id).state == "exited"


def test_list_includes_launched_apps(application_service: ApplicationService) -> None:
    first = application_service.open("Test Python", SLEEP)
    second = application_service.open("Test Python", SLEEP)

    assert {a.app_id for a in application_service.list_apps()} == {first.app_id, second.app_id}


def test_blocked_by_display_name(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationBlockedError):
        application_service.open("Shell Thing")


@pytest.mark.skipif(sys.platform != "win32", reason="relies on Windows executable naming")
@pytest.mark.parametrize("entry", ["python.exe", "PYTHON", "Python.EXE"])
def test_blocked_by_executable_name(
    make_application_service: Callable[[list[str]], ApplicationService], entry: str
) -> None:
    # The executable name blocks every app that runs it, whatever its display name, with or
    # without ".exe".
    service = make_application_service([entry])

    with pytest.raises(ApplicationBlockedError):
        service.open("Test Python", SLEEP)


def test_unlaunchable_app_is_refused(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationNotLaunchableError):
        application_service.open("Docs Only")


def test_unknown_and_ambiguous_names(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationNotInstalledError, match="no installed"):
        application_service.open("nothing like this")
    with pytest.raises(ApplicationNotInstalledError, match="ambiguous"):
        application_service.open("Test")


def test_store_package_parsing() -> None:
    assert installed_apps.store_package("Contoso.App_abc123!App") == ("Contoso.App", "abc123")
    assert installed_apps.store_package("Chrome") is None
    assert installed_apps.store_package("NoPublisher!App") is None


def _store_app(name: str, app_id: str) -> InstalledApp:
    return InstalledApp(
        name=name, version=None, publisher=None, source="store", app_id=app_id, launchable=True
    )


def test_store_apps_reject_args() -> None:
    service = ApplicationService([], lambda _: [_store_app("Contoso", "Contoso.App_abc123!App")])

    with pytest.raises(ApplicationLaunchError, match="arguments"):
        service.open("Contoso", ["--x"])


def test_store_apps_are_blocked_by_package_name() -> None:
    terminal = _store_app("Terminal", "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App")
    service = ApplicationService(["Microsoft.WindowsTerminal"], lambda _: [terminal])

    with pytest.raises(ApplicationBlockedError):
        service.open("Terminal")


def test_unknown_app_id(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationNotFoundError):
        application_service.status("nope")
    with pytest.raises(ApplicationNotFoundError):
        application_service.terminate("nope")


@pytest.mark.skipif(sys.platform != "win32", reason="installed-app listing is Windows-only")
def test_list_installed_finds_apps_and_filters() -> None:
    everything = installed_apps.list_installed()

    assert everything
    assert {a.source for a in everything} <= {"registry", "store", "desktop"}
    assert [a.name.lower() for a in everything] == sorted(a.name.lower() for a in everything)
    assert all(a.app_id for a in everything if a.launchable)

    needle = everything[0].name[:4].lower()
    filtered = installed_apps.list_installed(needle)
    assert filtered
    assert all(needle in a.name.lower() for a in filtered)


def test_list_installed_unsupported_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(UnsupportedPlatformError):
        installed_apps.list_installed()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths")
def test_resolve_exe_handles_known_folder_prefix_and_rejects_non_exe() -> None:
    assert installed_apps.resolve_exe(r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\cmd.exe")
    assert installed_apps.resolve_exe(r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\comexp.msc") is None
    assert installed_apps.resolve_exe("Microsoft.AutoGenerated.{46DE7A2A}") is None
    assert installed_apps.resolve_exe("https://example.com") is None


def _app(name: str, app_id: str | None, **kw: object) -> InstalledApp:
    fields: dict[str, object] = {
        "name": name,
        "version": None,
        "publisher": None,
        "source": "desktop",
        "app_id": app_id,
        "launchable": False,
    }
    return InstalledApp(**{**fields, **kw})  # type: ignore[arg-type]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths")
@pytest.mark.parametrize("suffix", ["", ",0", ",-12"])
@pytest.mark.parametrize("quoted", [False, True])
def test_icon_exe_parses_registry_display_icon(quoted: bool, suffix: str) -> None:
    exe = sys.executable
    raw = f'"{exe}"{suffix}' if quoted else f"{exe}{suffix}"

    assert str(installed_apps._icon_exe(raw)) == exe


def test_icon_exe_rejects_missing_non_exe_and_uninstallers(tmp_path: Path) -> None:
    uninstaller = tmp_path / "unins000.exe"
    uninstaller.write_bytes(b"")
    document = tmp_path / "readme.txt"
    document.write_bytes(b"")

    assert installed_apps._icon_exe(None) is None
    assert installed_apps._icon_exe(str(tmp_path / "missing.exe")) is None
    assert installed_apps._icon_exe(str(document)) is None
    assert installed_apps._icon_exe(f"{uninstaller},0") is None


def test_versioned_registry_entry_gives_opaque_start_app_its_exe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exe = Path(sys.executable)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        installed_apps,
        "_start_apps",
        lambda: [_app("Bruno", "com.usebruno.app"), _app("Other", "com.other.app")],
    )
    registry = [
        (_app("Bruno 4.1.0", None, source="registry", version="4.1.0"), exe),
        (_app("Other 1.0", None, source="registry"), exe),
        (_app("Other 2.0", None, source="registry"), exe),  # ambiguous: must not be guessed
    ]
    monkeypatch.setattr(installed_apps, "_registry_apps", lambda: registry)

    by_name = {a.name: a for a in installed_apps.list_installed()}

    bruno = by_name["Bruno"]
    assert bruno.launchable
    assert bruno.app_id == str(exe)
    assert bruno.version == "4.1.0"
    assert "Bruno 4.1.0" not in by_name  # merged, not listed twice
    assert not by_name["Other"].launchable  # two candidates: left alone


def test_launched_apps_do_not_inherit_electron_run_as_node(
    application_service: ApplicationService,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # An Electron host sets this for its children; if passed on, launched Electron apps run as Node.
    monkeypatch.setenv("ELECTRON_RUN_AS_NODE", "1")
    monkeypatch.setenv("KEEP_ME", "yes")
    out = tmp_path / "env.txt"
    code = (
        "import os, pathlib; "
        f"pathlib.Path({str(out)!r}).write_text("
        "repr((os.environ.get('ELECTRON_RUN_AS_NODE'), os.environ.get('KEEP_ME'))))"
    )

    app = application_service.open("Test Python", ["-c", code])
    deadline = time.monotonic() + 10
    while application_service.status(app.app_id).state == "running" and time.monotonic() < deadline:
        time.sleep(0.05)

    assert out.read_text() == "(None, 'yes')"
