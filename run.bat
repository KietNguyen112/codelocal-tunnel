@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
title CodeLocal Tunnel Gateway
cd /d "%~dp0"

echo ========================================================
echo             CODELOCAL TUNNEL GATEWAY
echo ========================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Khong tim thay Python tren he thong. Vui long cai dat Python 3.10+
    pause
    exit /b 1
)

:: 2. Check CustomTkinter
python -c "import customtkinter" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Dang cai dat thu vien giao dien CustomTkinter...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [!] Loi khi cai dat thu vien. Vui long kiem tra pip.
        pause
        exit /b 1
    )
)

:: 3. Launch App
echo [*] Dang khoi dong giao dien CodeLocal Tunnel...
python app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Ung dung ket thuc voi ma loi %ERRORLEVEL%.
    pause
)
