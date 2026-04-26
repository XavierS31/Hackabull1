@echo off
REM Build the Glove (Node B) firmware. Output: firmware/node_b_glove/.pio/build/node_b_glove/firmware.bin
pushd "%~dp0node_b_glove"
pio run
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
