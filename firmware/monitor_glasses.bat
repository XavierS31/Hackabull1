@echo off
REM Open the serial monitor for the Glasses (Node A). Ctrl+C to quit.
REM Pass a COM port as the first arg, e.g. "monitor_glasses.bat COM3".
pushd "%~dp0glasses"
if "%~1"=="" (
    pio device monitor
) else (
    pio device monitor --port %1
)
popd
