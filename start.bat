@echo off
:: start.bat — Kompetenzen-Tool starten (setzt vorherige Installation voraus)
:: Doppelklick oder: start.bat

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo =^> Installation pruefen

:: .env vorhanden?
if not exist ".env" (
    echo    [ERR] .env nicht gefunden. Bitte zuerst install-windows.ps1 ausfuehren.
    pause & exit /b 1
)

:: Docker vorhanden?
where docker >nul 2>&1
if errorlevel 1 (
    echo    [ERR] Docker nicht gefunden. Bitte zuerst install-windows.ps1 ausfuehren.
    pause & exit /b 1
)
echo    [OK] .env gefunden

:: APP_PORT aus .env lesen
set "APP_PORT=1337"
for /f "tokens=2 delims==" %%A in ('findstr /b "APP_PORT=" .env') do set "APP_PORT=%%A"

echo.
echo =^> Docker pruefen

docker info >nul 2>&1
if errorlevel 1 (
    echo    [!!] Docker-Daemon nicht aktiv - starte Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    set /a WAIT=0
    :wait_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    set /a WAIT+=3
    if !WAIT! geq 60 (
        echo    [ERR] Docker hat nicht rechtzeitig gestartet. Bitte Docker Desktop manuell starten.
        pause & exit /b 1
    )
    <nul set /p "=."
    goto wait_docker
    :docker_ready
    echo.
)
echo    [OK] Docker laeuft

echo.
echo =^> Docker-Images pruefen

set "IMG_COUNT=0"
for /f %%A in ('docker compose images -q 2^>nul') do set /a IMG_COUNT+=1
if %IMG_COUNT% lss 2 (
    echo    [ERR] Docker-Images fehlen ^(%IMG_COUNT% gefunden^). Bitte zuerst install-windows.ps1 ausfuehren.
    pause & exit /b 1
)
echo    [OK] Images vorhanden

echo.
echo =^> Container starten

set "RUNNING=0"
for /f %%A in ('docker compose ps --status running -q 2^>nul') do set /a RUNNING+=1
if %RUNNING% geq 3 (
    echo    [OK] Alle Container laufen bereits
) else (
    docker compose up -d
    echo    [OK] Container gestartet
)

echo.
echo =^> Datenbank pruefen

set /a TRIES=0
:check_db
timeout /t 2 /nobreak >nul
set /a TRIES+=1
set "HEALTH="
for /f "tokens=*" %%A in ('docker compose ps --format "{{.Health}}" db 2^>nul') do set "HEALTH=%%A"
if "!HEALTH!"=="healthy" goto db_ok
if %TRIES% geq 20 goto db_warn
<nul set /p "=."
goto check_db
:db_warn
echo    [!!] Datenbank-Health-Check schlug fehl ^(docker compose logs db^)
goto db_done
:db_ok
echo    [OK] Datenbank gesund
:db_done

echo.
echo =^> Backend pruefen

set /a TRIES=0
:check_backend
timeout /t 3 /nobreak >nul
set /a TRIES+=1
docker compose logs backend 2>nul | findstr /c:"Application startup complete" >nul
if not errorlevel 1 goto backend_ok
if %TRIES% geq 30 goto backend_warn
<nul set /p "=."
goto check_backend
:backend_warn
echo    [!!] Backend antwortet noch nicht ^(docker compose logs backend^)
goto backend_done
:backend_ok
echo    [OK] Backend bereit
:backend_done

echo.
echo =^> Frontend pruefen

set /a TRIES=0
:check_frontend
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 2 "http://localhost:%APP_PORT%" -o nul >nul 2>&1
if not errorlevel 1 goto frontend_ok
if %TRIES% geq 15 goto frontend_warn
<nul set /p "=."
goto check_frontend
:frontend_warn
echo    [!!] Frontend noch nicht erreichbar unter Port %APP_PORT% ^(docker compose logs frontend^)
goto frontend_done
:frontend_ok
echo    [OK] Frontend erreichbar
:frontend_done

echo.
echo =^> Fertig!
echo.
echo   App:     http://localhost:%APP_PORT%
echo.
echo   Logs:    docker compose logs -f
echo   Stoppen: docker compose down
echo.

start http://localhost:%APP_PORT%

endlocal
