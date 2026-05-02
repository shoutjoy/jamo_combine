@echo off
chcp 65001 >nul
title JamoCombine 제거
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
