@echo off
REM Build + flash the Glove (Node B) firmware over USB.
REM Pass a COM port as the first arg, e.g. "upload_glove.bat COM4".
pushd "%~dp0node_b_glove"
if "%~1"=="" (
    pio run -t upload
) else (
    pio run -t upload --upload-port %1
)
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
