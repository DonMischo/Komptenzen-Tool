@echo off
REM ===== Config =====
set "APP=print.py"
set "ENV_DIR=.venv"

REM ===== Activate virtual environment =====
call "%ENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ^> Could not activate virtual environment.
    pause
    exit /b 1
)

REM ===== Run the Streamlit app =====
echo Launching Streamlit app ...
py "%APP%"

REM Keep the window open after exit
pause