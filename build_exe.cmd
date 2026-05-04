@echo off
chcp 65001 >nul
title JamoCombine EXE 빌드
cd /d "%~dp0"

python -m pip install -r "%~dp0requirements-build.txt" --quiet
if errorlevel 1 (
    echo [오류] pip 설치에 실패했습니다.
    pause
    exit /b 1
)

python -m PyInstaller --noconfirm "%~dp0JamoCombine.spec"
if errorlevel 1 (
    echo [오류] PyInstaller 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [완료] dist\JamoCombine.exe
echo GitHub Releases에 이 파일을 올리면 README의 다운로드 링크가 동작합니다.
pause
