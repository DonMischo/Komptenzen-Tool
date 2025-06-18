@echo off
REM ------------------------------------------------------------------
REM setup_and_run.bat - Windows helper
REM   - creates/updates a local Python venv (.venv)
REM   - installs or upgrades streamlit, pandas, pyyaml
REM   - launches the Streamlit app competence_selector.py
REM ------------------------------------------------------------------

setlocal enabledelayedexpansion

REM ===== Config =====
set "APP=KompetenzenTool.py"
set "ENV_DIR=.venv"

REM ===== Check Python =====
where python >nul 2>&1
if errorlevel 1 (
    echo ^> Python is not in PATH. Please install Python 3.9+ and tick "Add to PATH".
    pause
    exit /b 1
)

REM ===== Create virtual environment if it does not exist =====
if not exist "%ENV_DIR%" (
    echo Creating virtual environment in %ENV_DIR% ...
    python -m venv "%ENV_DIR%"
)

REM ===== Activate virtual environment =====
call "%ENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ^> Could not activate virtual environment.
    pause
    exit /b 1
)

REM ===== Upgrade pip and install dependencies =====
echo Installing / upgrading required packages ...
python -m pip install --upgrade pip
python -m pip install --upgrade streamlit pandas pyyaml
python -m pip install --upgrade filelock

REM ===== Run the Streamlit app =====
echo Launching Streamlit app ...
streamlit run "%APP%"

REM Keep the window open after exit
pause
