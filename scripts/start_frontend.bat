@echo off
REM Start the Vite dev server. Long-running -- pair with run_in_background.
setlocal
set "ROOT=%~dp0.."
if not exist "%ROOT%\frontend\node_modules" (
    echo [start_frontend] node_modules missing. Run scripts\ensure_setup.ps1 first.
    exit /b 1
)
pushd "%ROOT%\frontend"
call npm run dev
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
