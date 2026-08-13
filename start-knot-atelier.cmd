@echo off
setlocal
title Knot Atelier

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0frontend\start-knot-atelier.ps1" %*
set "KNOT_ATELIER_EXIT=%ERRORLEVEL%"

echo.
if not "%KNOT_ATELIER_EXIT%"=="0" echo Knot Atelier failed. Read the error message above.
echo Press any key to close this window.
pause >nul
exit /b %KNOT_ATELIER_EXIT%
