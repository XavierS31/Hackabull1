@echo off
REM Build the Glasses (Node A) firmware. Output: firmware/glasses/.pio/build/glasses/firmware.bin
pushd "%~dp0glasses"
pio run
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
