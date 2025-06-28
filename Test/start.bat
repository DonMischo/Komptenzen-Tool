@echo off
setlocal

echo Creating virtual environment in ".venv" ...
python -m venv .venv

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ERROR: Could not find activate.bat
    exit /b 1
)

echo.
echo Installing required Python packages...
pip install --upgrade pip

pip install ^
    weasyprint>=60.0 ^
    jinja2>=3.1 ^
    pydyf>=0.10.0 ^
    cffi>=0.6 ^
    tinycss2>=1.3.0 ^
    cssselect2>=0.8.0 ^
    pyphen>=0.9.1 ^
    pillow>=9.1.0 ^
    fonttools>=4.0.0 ^
    tinyhtml5>=2.0.0b1

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: One or more packages failed to install.
    exit /b 1
)

echo.
echo All packages installed successfully.
echo Python virtual environment ready in ".venv"
echo To activate later, run:
echo     call .venv\Scripts\activate.bat

endlocal
pause
