import hashlib
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import Browser, Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
PASS_SCREENSHOTS = ARTIFACTS / "pass" / "screenshots"
PASS_VIDEOS = ARTIFACTS / "pass" / "videos"
FAIL_SCREENSHOTS = ARTIFACTS / "fail" / "screenshots"
FAIL_VIDEOS = ARTIFACTS / "fail" / "videos"
RECORDINGS = ARTIFACTS / ".recordings"
PENDING_SCREENSHOTS = ARTIFACTS / ".pending-screenshots"
LOGS = ARTIFACTS / "logs"
for directory in (
    PASS_SCREENSHOTS,
    PASS_VIDEOS,
    FAIL_SCREENSHOTS,
    FAIL_VIDEOS,
    RECORDINGS,
    PENDING_SCREENSHOTS,
    LOGS,
):
    directory.mkdir(parents=True, exist_ok=True)

TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"tracker-tests-{secrets.token_hex(8)}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)

from backend.app import models  # noqa: E402,F401
from backend.app.db.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Transaction, User  # noqa: E402


def _artifact_name(nodeid: str, stage: str) -> str:
    test_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", nodeid).strip("-").lower()
    stage_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", stage).strip("-").lower()
    digest = hashlib.sha1(nodeid.encode("utf-8")).hexdigest()[:8]
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}_{stage_name[:32]}_{test_name[-55:]}-{digest}"


def _result_banner(page: Page, passed: bool, label: str, details: str = "") -> None:
    page.evaluate(
        """({passed, label, details}) => {
            document.querySelector('[data-test-result]')?.remove();
            const banner = document.createElement('aside');
            banner.setAttribute('data-test-result', 'true');
            banner.style.cssText = [
                'position:fixed', 'z-index:2147483647', 'top:12px', 'left:12px',
                'right:12px', 'padding:14px 18px', 'border-radius:8px',
                'box-shadow:0 3px 14px #0005', 'font:16px/1.45 Arial,sans-serif',
                'color:white', 'background:' + (passed ? '#18794e' : '#b42318'),
                'white-space:pre-wrap', 'overflow-wrap:anywhere', 'max-height:35vh',
                'overflow:auto'
            ].join(';');
            const heading = document.createElement('strong');
            heading.textContent = `${passed ? 'PASS' : 'FAIL'} — ${label}`;
            banner.appendChild(heading);
            if (details) {
                const result = document.createElement('div');
                result.textContent = details;
                result.style.marginTop = '4px';
                banner.appendChild(result);
            }
            document.body.appendChild(banner);
        }""",
        {"passed": passed, "label": label, "details": details},
    )


def _capture_page(
    page: Page,
    nodeid: str,
    stage: str,
    passed: bool = True,
    details: str = "",
) -> Path:
    name = _artifact_name(nodeid, stage)
    path = PENDING_SCREENSHOTS / f"{name}.png"
    _result_banner(page, passed, stage, details[:2500])
    page.screenshot(path=str(path), full_page=True)
    page.locator("[data-test-result]").evaluate("(banner) => banner.remove()")
    return path


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
        instance = playwright.chromium.launch(headless=headless, slow_mo=250)
        yield instance
        instance.close()


@pytest.fixture(autouse=True)
def browser_page(
    request: pytest.FixtureRequest, browser: Browser, e2e_services
):
    context = browser.new_context(
        record_video_dir=str(RECORDINGS),
        record_video_size={"width": 1280, "height": 800},
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()
    video = page.video
    page.goto(e2e_services["frontend_url"], wait_until="domcontentloaded")
    page.get_by_role(
        "heading", name="💰 Personal Income & Expense Tracker"
    ).wait_for(timeout=15_000)
    yield page

    report = getattr(request.node, "rep_call", None) or getattr(
        request.node, "rep_teardown", None
    ) or getattr(
        request.node, "rep_setup", None
    )
    passed = report is not None and report.passed
    outcome = "PASSED" if passed else "FAILED"
    details = ""
    if report is not None and report.failed:
        crash = getattr(getattr(report, "longrepr", None), "reprcrash", None)
        details = getattr(crash, "message", "") or report.longreprtext
    details = str(details)[:2500]
    name = _artifact_name(request.node.nodeid, f"final-{outcome.lower()}")
    screenshot_dir = PASS_SCREENSHOTS if passed else FAIL_SCREENSHOTS
    video_dir = PASS_VIDEOS if passed else FAIL_VIDEOS
    captured_paths = getattr(request.node, "_page_capture_paths", [])

    try:
        captured_paths.append(
            _capture_page(
                page,
                request.node.nodeid,
                f"final-{outcome.lower()}",
                passed=passed,
                details=details,
            )
        )
        page.wait_for_timeout(500)
    except Exception as exc:
        print(f"Could not capture screenshot for {request.node.nodeid}: {exc}")
    finally:
        context.close()
        for screenshot_path in captured_paths:
            if screenshot_path.exists():
                screenshot_path.replace(screenshot_dir / screenshot_path.name)
        if video is not None:
            try:
                recorded_video = Path(video.path())
                output_video = video_dir / f"{name}.mp4"
                ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
                conversion = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-i",
                        str(recorded_video),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        str(output_video),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if conversion.returncode != 0:
                    raise RuntimeError(
                        f"MP4 conversion failed: {conversion.stderr[-1000:]}"
                    )
                recorded_video.unlink(missing_ok=True)
            except Exception as exc:
                print(f"Could not save video for {request.node.nodeid}: {exc}")


@pytest.fixture
def capture_page(request: pytest.FixtureRequest, browser_page: Page):
    def capture(stage: str) -> Path:
        screenshot = _capture_page(
            browser_page, request.node.nodeid, stage, passed=True
        )
        paths = getattr(request.node, "_page_capture_paths", [])
        paths.append(screenshot)
        request.node._page_capture_paths = paths
        return screenshot

    return capture


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        with SessionLocal() as db:
            db.query(Transaction).delete()
            db.query(User).delete()
            db.commit()
        yield test_client


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_for_service(process: subprocess.Popen, url: str, label: str) -> None:
    deadline = time.monotonic() + 60
    last_error = "service did not respond"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{label} exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"{label} did not become ready: {last_error}")


@pytest.fixture(scope="session")
def e2e_services(tmp_path_factory):
    service_dir = tmp_path_factory.mktemp("tracker-e2e")
    api_database = service_dir / "e2e.db"
    api_port = _unused_port()
    frontend_port = _unused_port()
    api_url = f"http://127.0.0.1:{api_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{api_database.as_posix()}",
            "SECRET_KEY": secrets.token_urlsafe(32),
            "API_BASE_URL": api_url,
            "PYTHONPATH": os.pathsep.join(
                part for part in (str(ROOT), environment.get("PYTHONPATH", "")) if part
            ),
        }
    )

    backend_log = (LOGS / "e2e-backend.log").open("w", encoding="utf-8")
    frontend_log = (LOGS / "e2e-frontend.log").open("w", encoding="utf-8")
    backend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        cwd=ROOT,
        env=environment,
        stdout=backend_log,
        stderr=subprocess.STDOUT,
    )
    frontend_process = None

    try:
        _wait_for_service(backend_process, f"{api_url}/", "E2E backend")
        frontend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "frontend/app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(frontend_port),
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=ROOT,
            env=environment,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )
        _wait_for_service(
            frontend_process, f"{frontend_url}/_stcore/health", "E2E frontend"
        )
        yield {"api_url": api_url, "frontend_url": frontend_url}
    finally:
        for process in (frontend_process, backend_process):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        backend_log.close()
        frontend_log.close()


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    try:
        TEST_DATABASE_PATH.unlink(missing_ok=True)
    except PermissionError:
        print(f"Temporary test database is still in use: {TEST_DATABASE_PATH}")
