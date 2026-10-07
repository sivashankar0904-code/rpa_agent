import time

import pytest

from rpa_agent.core.errors import ApplicationNotAllowedError, ApplicationNotFoundError
from rpa_agent.services.application_service import ApplicationService

SLEEP = ["-c", "import time; time.sleep(60)"]


def test_open_reports_running(application_service: ApplicationService) -> None:
    app = application_service.open("python", SLEEP)

    assert app.state == "running"
    assert app.exit_code is None
    assert application_service.status(app.app_id).pid == app.pid


def test_status_reports_exit_code_after_process_ends(
    application_service: ApplicationService,
) -> None:
    app = application_service.open("python", ["-c", "raise SystemExit(3)"])

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
    app = application_service.open("python", SLEEP)

    result = application_service.terminate(app.app_id)

    assert result.state == "exited"
    assert application_service.status(app.app_id).state == "exited"


def test_list_includes_launched_apps(application_service: ApplicationService) -> None:
    first = application_service.open("python", SLEEP)
    second = application_service.open("python", SLEEP)

    assert {a.app_id for a in application_service.list_apps()} == {first.app_id, second.app_id}


def test_rejects_unlisted_application(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationNotAllowedError):
        application_service.open("powershell")


def test_unknown_app_id(application_service: ApplicationService) -> None:
    with pytest.raises(ApplicationNotFoundError):
        application_service.status("nope")
    with pytest.raises(ApplicationNotFoundError):
        application_service.terminate("nope")
