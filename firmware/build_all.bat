@echo off
REM Build both firmware images.
call "%~dp0build_glasses.bat"
if errorlevel 1 exit /b 1
call "%~dp0build_glove.bat"
if errorlevel 1 exit /b 1
echo.
echo === Both firmware builds OK ===
echo Glasses: firmware\glasses\.pio\build\glasses\firmware.bin
echo Glove:   firmware\node_b_glove\.pio\build\node_b_glove\firmware.bin
