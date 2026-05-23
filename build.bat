@echo off
REM ============================================================
REM  Chema Steel Weight Report — Windows Build + Installer
REM ============================================================

SET APP_NAME=ChemaSteelWeightReport

REM ── Step 1: Install / upgrade dependencies ──────────────────
echo [1/5] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip install failed.
    pause & exit /b 1
)
pip install pyinstaller
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller install failed.
    pause & exit /b 1
)

REM ── Step 2: Clean previous build artefacts ──────────────────
echo [2/5] Cleaning previous build...
if exist dist           rmdir /s /q dist
if exist build          rmdir /s /q build
if exist installer_output rmdir /s /q installer_output
if exist %APP_NAME%.spec del /q %APP_NAME%.spec

REM ── Step 3: Build the executable with PyInstaller ───────────
echo [3/5] Building executable (this takes a few minutes)...
pyinstaller --noconfirm --onedir --noconsole ^
    --name "%APP_NAME%" ^
    --collect-data pdfplumber ^
    --collect-data openpyxl ^
    --hidden-import reportlab.graphics.renderPM ^
    --hidden-import pdfplumber ^
    --hidden-import fitz ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed. See messages above.
    pause & exit /b 1
)

REM ── Step 4: Compile the installer with Inno Setup ───────────
echo [4/5] Creating installer...

REM Try the default Inno Setup install locations
SET ISCC=""
IF EXIST "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    SET ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
IF EXIST "C:\Program Files\Inno Setup 6\ISCC.exe" (
    SET ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

IF %ISCC%=="" (
    echo.
    echo WARNING: Inno Setup not found.
    echo Download and install it from: https://jrsoftware.org/isdl.php
    echo Then re-run this script, or compile installer.iss manually.
    echo.
    echo The portable app is still available at:
    echo   dist\%APP_NAME%\%APP_NAME%.exe
    pause & exit /b 0
)

%ISCC% installer.iss
if %ERRORLEVEL% neq 0 (
    echo ERROR: Inno Setup compilation failed.
    pause & exit /b 1
)

REM ── Step 5: Done ────────────────────────────────────────────
echo [5/5] Done!
echo.
echo ============================================================
echo  Installer : installer_output\ChemaSteelWeightReport_Setup_v2.0.exe
echo  Portable  : dist\%APP_NAME%\%APP_NAME%.exe
echo ============================================================
pause
