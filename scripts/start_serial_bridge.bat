@echo off
REM Run the glove serial-to-UDP bridge.
REM Usage:
REM   start_serial_bridge.bat              -- defaults to COM5
REM   start_serial_bridge.bat COM5         -- explicit port
REM   start_serial_bridge.bat COM5 -v      -- verbose (print every packet)
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=COM5"
shift
"%PY%" "%ROOT%\scripts\serial_bridge.py" --port %PORT% %1 %2 %3 %4
