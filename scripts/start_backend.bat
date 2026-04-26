@echo off
REM Start the FastAPI backend using the project's .venv. Runs in the foreground.
REM Long-running -- pair with run_in_background when launching from Claude Code.
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [start_backend] venv not found at %PY%. Run scripts\ensure_setup.ps1 first.
    exit /b 1
)
pushd "%ROOT%\backend"
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
