@echo off
chcp 65001 >nul
title JamoCombine 설치
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 exit /b 1
echo.
pause
