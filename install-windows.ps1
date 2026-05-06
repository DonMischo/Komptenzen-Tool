# install-windows.ps1
# Kompetenzen-Tool - Windows 11 + Docker Desktop + WSL2 setup
# Run as Administrator in PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\install-windows.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$REPO_DIR        = Split-Path -Parent $MyInvocation.MyCommand.Path
$APP_PORT        = 8501
$APP_PUBLIC_PORT = 8502
$DB_PORT         = 5432

function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    [!!] $msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# 1. Windows version check
# ---------------------------------------------------------------------------
Write-Step "Pruefe Windows-Version"
$build = [System.Environment]::OSVersion.Version.Build
if ($build -lt 19041) {
    Write-Error "Windows 10 Build 19041 (Version 2004) oder hoeher erforderlich fuer WSL2."
}
Write-OK "Windows Build $build"

# ---------------------------------------------------------------------------
# 2. WSL2
# ---------------------------------------------------------------------------
Write-Step "Pruefe WSL2"
$wslInstalled = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslInstalled) {
    Write-Warn "WSL nicht gefunden - installiere WSL2 mit Ubuntu..."
    wsl --install -d Ubuntu
    Write-OK "WSL2 + Ubuntu installiert. Bitte System neu starten und Skript erneut ausfuehren."
    exit 0
} else {
    Write-OK "WSL bereits installiert"
    $wslVersion = wsl --list --verbose 2>&1
    Write-Host $wslVersion
}

# ---------------------------------------------------------------------------
# 3. Docker Desktop (via winget)
# ---------------------------------------------------------------------------
Write-Step "Pruefe Docker Desktop"
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Warn "Docker nicht gefunden - installiere ueber winget..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Error "winget nicht gefunden. Bitte App-Installer aus dem Microsoft Store installieren oder Docker Desktop manuell von https://docs.docker.com/desktop/install/windows-install/"
    }

    winget install --id Docker.DockerDesktop --exact --silent --accept-package-agreements --accept-source-agreements
    Write-OK "Docker Desktop installiert."
    Write-Warn "Bitte Docker Desktop starten, Lizenzbedingungen akzeptieren und Skript erneut ausfuehren."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    exit 0
}

# Docker installed - make sure daemon is running
$dockerRunning = $false
try { docker info 2>&1 | Out-Null; $dockerRunning = $true } catch {}

if (-not $dockerRunning) {
    Write-Warn "Docker ist installiert aber nicht gestartet - starte Docker Desktop..."
    $desktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktopExe) { Start-Process $desktopExe }

    Write-Host "    Warte auf Docker..." -NoNewline
    $timeout = 60
    while ($timeout -gt 0) {
        Start-Sleep 3
        $timeout -= 3
        try { docker info 2>&1 | Out-Null; $dockerRunning = $true; break } catch {}
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $dockerRunning) {
        Write-Error "Docker hat nicht rechtzeitig gestartet. Bitte Docker Desktop manuell starten und Skript erneut ausfuehren."
    }
}
Write-OK "Docker laeuft"

try {
    docker compose version | Out-Null
    Write-OK "Docker Compose verfuegbar"
} catch {
    Write-Error "Docker Compose nicht gefunden. Stelle sicher dass Docker Desktop aktuell ist."
}

# ---------------------------------------------------------------------------
# 4. Create .env if missing
# ---------------------------------------------------------------------------
Write-Step "Konfiguration (.env)"
$envFile = Join-Path $REPO_DIR ".env"
if (-not (Test-Path $envFile)) {
    Write-Warn ".env nicht gefunden - wird angelegt"

    $pgUser = Read-Host "PostgreSQL-Benutzername [appuser]"
    if ([string]::IsNullOrWhiteSpace($pgUser)) { $pgUser = "appuser" }

    $pgPass = Read-Host "PostgreSQL-Passwort" -AsSecureString
    $pgPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pgPass)
    )
    if ([string]::IsNullOrWhiteSpace($pgPassPlain)) {
        Write-Error "Passwort darf nicht leer sein."
    }

    $appPort = Read-Host "Admin-Port [$APP_PORT]"
    if ([string]::IsNullOrWhiteSpace($appPort)) { $appPort = $APP_PORT }

    $pubPort = Read-Host "Public-Port [$APP_PUBLIC_PORT]"
    if ([string]::IsNullOrWhiteSpace($pubPort)) { $pubPort = $APP_PUBLIC_PORT }

    $dbPort = Read-Host "DB-Port [$DB_PORT]"
    if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = $DB_PORT }

    $envContent = @"
POSTGRES_USER=$pgUser
POSTGRES_PASSWORD=$pgPassPlain
APP_PORT=$appPort
APP_PUBLIC_PORT=$pubPort
DB_PORT=$dbPort
POSTGRES_URL=postgresql://${pgUser}:${pgPassPlain}@localhost:5432
"@
    [System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.Encoding]::UTF8)
    Write-OK ".env erstellt"
} else {
    Write-OK ".env bereits vorhanden"
}

# ---------------------------------------------------------------------------
# 5. Windows Firewall rule for public port
# ---------------------------------------------------------------------------
Write-Step "Windows Firewall"

# Read actual ports from .env
$envLines    = Get-Content $envFile
$portLine    = $envLines | Where-Object { $_ -match "^APP_PORT=" }
$pubPortLine = $envLines | Where-Object { $_ -match "^APP_PUBLIC_PORT=" }
if ($portLine)    { $APP_PORT        = [int]($portLine    -split "=")[1].Trim() }
if ($pubPortLine) { $APP_PUBLIC_PORT = [int]($pubPortLine -split "=")[1].Trim() }

Write-OK "Port $APP_PORT (Admin) ist auf localhost gebunden - keine Firewall-Regel noetig"

$pubRuleName = "Kompetenzen-Tool Public (Port $APP_PUBLIC_PORT)"
$existingPub = Get-NetFirewallRule -DisplayName $pubRuleName -ErrorAction SilentlyContinue
if (-not $existingPub) {
    New-NetFirewallRule -DisplayName $pubRuleName `
        -Direction Inbound -Protocol TCP -LocalPort $APP_PUBLIC_PORT `
        -Action Allow -Profile Any | Out-Null
    Write-OK "Firewall-Regel angelegt: $pubRuleName"
} else {
    Write-OK "Firewall-Regel bereits vorhanden: $pubRuleName"
}

# ---------------------------------------------------------------------------
# 6. Docker WSL integration hint
# ---------------------------------------------------------------------------
Write-Step "Docker Desktop - WSL Integration"
Write-Warn "Bitte sicherstellen, dass in Docker Desktop unter:"
Write-Host "    Settings > Resources > WSL Integration"
Write-Host "    ... Ubuntu aktiviert ist."
Write-Host "    (Einmalig manuell zu pruefen)"

# ---------------------------------------------------------------------------
# 7. Required directories
# ---------------------------------------------------------------------------
Write-Step "Verzeichnisse pruefen"
@("app\student_data", "app\data", "app\TexTemplate") | ForEach-Object {
    $dir = Join-Path $REPO_DIR $_
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-OK "Erstellt: $_"
    } else {
        Write-OK "Vorhanden: $_"
    }
}

# ---------------------------------------------------------------------------
# 8. Build & start containers
# ---------------------------------------------------------------------------
Write-Step "Docker-Container bauen und starten"
Set-Location $REPO_DIR
docker compose up --build -d
Write-OK "Container gestartet"

# ---------------------------------------------------------------------------
# 9. Access info
# ---------------------------------------------------------------------------
Write-Step "Fertig!"

$lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual" } |
          Where-Object { $_.IPAddress -notlike "169.*" -and $_.IPAddress -notlike "127.*" } |
          Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "  Admin  (nur lokal): http://localhost:$APP_PORT" -ForegroundColor White
Write-Host "  Public (lokal):     http://localhost:$APP_PUBLIC_PORT" -ForegroundColor White
if ($lanIP) {
    Write-Host "  Public (Netzwerk):  http://${lanIP}:$APP_PUBLIC_PORT" -ForegroundColor White
}
Write-Host ""
Write-Host "  Logs:       docker compose logs -f" -ForegroundColor DarkGray
Write-Host "  Stoppen:    docker compose down" -ForegroundColor DarkGray
Write-Host "  Neu bauen:  docker compose up --build -d" -ForegroundColor DarkGray
Write-Host ""
