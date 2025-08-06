@echo off
REM ===== Config =====
set "APP=KompetenzenTool.py"
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
@echo off

python -m populate_random_reports --db db/reports_2024-2025_ej.db
REM python check_grades.py
REM Keep the window open after exit
pause
