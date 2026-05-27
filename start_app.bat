@echo off
setlocal EnableDelayedExpansion

:: ---------------------------------------------------------------------------
:: start_app.bat  --  Kompetenzen-Tool Quick-Start (Windows)
:: ---------------------------------------------------------------------------

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"

echo.
echo =^> Kompetenzen-Tool starten
echo.

:: ---------------------------------------------------------------------------
:: 1. Docker vorhanden?
:: ---------------------------------------------------------------------------
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERR] Docker nicht gefunden.
    echo       Bitte Docker Desktop installieren:
    echo       https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: 2. Docker-Daemon laeuft?
:: ---------------------------------------------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
    echo [!!]  Docker laeuft nicht -- starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo      Warte auf Docker ^(bis zu 60 Sekunden^)...

    set /a TRIES=0
    :wait_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    set /a TRIES=!TRIES!+1
    echo      Versuch !TRIES!/20...
    if !TRIES! lss 20 goto wait_docker

    echo [ERR] Docker ist nach 60 Sekunden nicht bereit.
    echo       Bitte Docker Desktop manuell starten und erneut versuchen.
    pause
    exit /b 1
)
:docker_ready
echo [OK]  Docker laeuft

:: ---------------------------------------------------------------------------
:: 3. .env pruefen
:: ---------------------------------------------------------------------------
if not exist "%SCRIPT_DIR%\.env" (
    if exist "%SCRIPT_DIR%\.env.example" (
        copy "%SCRIPT_DIR%\.env.example" "%SCRIPT_DIR%\.env" >nul
        echo.
        echo [!!]  .env wurde aus .env.example erstellt.
        echo       Bitte Passwoerter und JWT_SECRET anpassen, dann erneut starten.
        echo.
        notepad "%SCRIPT_DIR%\.env"
        pause
        exit /b 0
    ) else (
        echo [ERR] .env fehlt und keine .env.example gefunden.
        echo       Bitte .env manuell erstellen ^(siehe README^).
        pause
        exit /b 1
    )
)
echo [OK]  .env gefunden

:: ---------------------------------------------------------------------------
:: 4. APP_PORT aus .env lesen
:: ---------------------------------------------------------------------------
set "APP_PORT=1337"
for /f "usebackq tokens=1,* delims==" %%A in ("%SCRIPT_DIR%\.env") do (
    if /i "%%A"=="APP_PORT" set "APP_PORT=%%B"
)

:: ---------------------------------------------------------------------------
:: 5. Container bauen und starten
:: ---------------------------------------------------------------------------
echo.
echo =^> docker compose up --build -d
echo.
docker compose up --build -d
if errorlevel 1 (
    echo.
    echo [ERR] docker compose fehlgeschlagen.
    echo       Logs anzeigen mit:  docker compose logs
    pause
    exit /b 1
)

echo.
echo [OK]  Container laufen

:: ---------------------------------------------------------------------------
:: 6. Browser oeffnen
:: ---------------------------------------------------------------------------
echo.
echo =^> Oeffne http://localhost:%APP_PORT%
timeout /t 3 /nobreak >nul
start "" "http://localhost:%APP_PORT%"

echo.
echo  Nuetzliche Befehle:
echo    Logs:      docker compose logs -f
echo    Stoppen:   docker compose down
echo    Neubauen:  docker compose up --build -d
echo.
endlocal
