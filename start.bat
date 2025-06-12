@echo off
setlocal enabledelayedexpansion

REM --- Set the virtual environment directory (relative to this script) ---
set "VENV_DIR=%~dp0.venv"
set "ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat"

REM --- Step 1: Ensure Python is in PATH ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM --- Step 2: Check if the venv exists and is valid, or create it ---
if exist "%ACTIVATE_SCRIPT%" (
    call "%ACTIVATE_SCRIPT%" >nul 2>&1
    python -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Existing venv appears corrupted. Recreating...
        rmdir /s /q "%VENV_DIR%"
        goto :create_venv
    )
) else (
    goto :create_venv
)

goto :ask_input

:create_venv
echo [INFO] Creating virtual environment...
python -m venv "%VENV_DIR%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
call "%ACTIVATE_SCRIPT%"
echo [INFO] Installing dependencies...
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:ask_input
REM --- Step 3: Prompt for inputs ---
call "%ACTIVATE_SCRIPT%" >nul 2>&1
set /p "LOCAL_FOLDER=Enter local folder path to upload: "
set /p "GDRIVE_ID=Enter Google Drive folder ID to upload to: "

REM --- Step 4: Run the uploader script ---
echo [INFO] Starting upload...
python gdrive_uploader.py "%LOCAL_FOLDER%" "%GDRIVE_ID%" --chunk-size 256M
if errorlevel 1 (
    echo [ERROR] Upload failed.
    pause
    exit /b 1
)

echo [INFO] Upload complete.
pause
