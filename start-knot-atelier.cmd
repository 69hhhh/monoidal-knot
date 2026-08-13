@echo off
chcp 65001 >nul
title Knot Atelier

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0frontend\start-knot-atelier.ps1" %*
set "KNOT_ATELIER_EXIT=%ERRORLEVEL%"

if not "%KNOT_ATELIER_EXIT%"=="0" (
  echo.
  echo Knot Atelier 启动失败，请查看上面的错误信息。
)

echo.
echo 按任意键关闭此窗口。
pause >nul
exit /b %KNOT_ATELIER_EXIT%
