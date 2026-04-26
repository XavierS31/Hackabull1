@echo off
REM Open the serial monitor for the Glove (Node B). Ctrl+C to quit.
REM Pass a COM port as the first arg, e.g. "monitor_glove.bat COM4".
pushd "%~dp0node_b_glove"
if "%~1"=="" (
    pio device monitor
) else (
    pio device monitor --port %1
)
popd
