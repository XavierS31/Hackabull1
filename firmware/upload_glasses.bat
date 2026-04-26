@echo off
REM Build + flash the Glasses (Node A) firmware over USB.
REM Pass a COM port as the first arg, e.g. "upload_glasses.bat COM3".
REM Without an arg PlatformIO will auto-detect.
pushd "%~dp0glasses"
if "%~1"=="" (
    pio run -t upload
) else (
    pio run -t upload --upload-port %1
)
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
