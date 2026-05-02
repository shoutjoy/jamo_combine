@echo off
:: 한글 자모 결합기 실행 배치 파일
:: 작성자: Gemini
:: 목적: 파이썬 스크립트를 원클릭으로 실행

title 한글 자모 결합기 실행 도구

:: 파이썬 설치 여부 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 파이썬이 설치되어 있지 않거나 PATH 설정이 되어 있지 않습니다.
    echo python.org에서 파이썬을 설치하십시오.
    pause
    exit /b
)

:: 스크립트 실행
echo 프로그램을 실행 중입니다...
python "%~dp0korean_nfc_converter.py"

:: 오류 발생 시 창 유지
if %errorlevel% neq 0 (
    echo.
    echo [경고] 프로그램이 비정상적으로 종료되었습니다.
    pause
)