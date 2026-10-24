import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")


@pytest.mark.parametrize(
    "failure,expected", [("", ["admin", "demo", "start"]), ("admin", ["admin"]), ("demo", ["admin", "demo"])]
)
def test_first_launch_checks_current_command_status(tmp_path, failure, expected):
    root = tmp_path / "project with spaces"
    tools = root / "tools"
    tools.mkdir(parents=True)
    source = (Path(__file__).resolve().parents[1] / "tools" / "kitafenster-starten.bat").read_text()
    # Run the real control flow, replacing only external Python commands with a stub.
    source = source.replace('"%ROOT%\\.venv\\Scripts\\python.exe"', 'call "%ROOT%\\python-stub.bat"')
    launcher = tools / "start.bat"
    launcher.write_text(source)
    (root / "python-stub.bat").write_text(
        "@echo off\n"
        'if "%~1"=="-c" exit /b 1\n'
        'if "%~2"=="uvicorn" (\n'
        '  echo start>>"%TEST_TRACE%"\n'
        '  echo %CD%>"%TEST_CWD%"\n'
        "  exit /b 0\n"
        ")\n"
        'echo %~3>>"%TEST_TRACE%"\n'
        'if "%~3"=="%TEST_FAILURE%" exit /b 1\n'
        "exit /b 0\n"
    )
    trace, cwd = tmp_path / "trace", tmp_path / "cwd"
    result = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)],
        cwd=tmp_path,
        env={**os.environ, "TEST_TRACE": str(trace), "TEST_CWD": str(cwd), "TEST_FAILURE": failure},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert trace.read_text().splitlines() == expected, result.stdout + result.stderr
    if not failure:
        assert Path(cwd.read_text().strip()) == root
