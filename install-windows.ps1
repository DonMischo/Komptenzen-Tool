# install-windows.ps1
# Kompetenzen-Tool - Windows 11 + Docker Desktop + WSL2 setup
# Run as Administrator in PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\install-windows.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$REPO_DIR        = Split-Path -Parent $MyInvocation.MyCommand.Path
$APP_PORT = 1337
$DB_PORT  = 5432

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

    # Auto-generate JWT secret using .NET crypto
    $jwtBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($jwtBytes)
    $jwtSecret = [BitConverter]::ToString($jwtBytes) -replace '-',''
    Write-OK "JWT-Secret automatisch generiert"

    $appPort = Read-Host "Port [$APP_PORT]"
    if ([string]::IsNullOrWhiteSpace($appPort)) { $appPort = $APP_PORT }

    $dbPort = Read-Host "DB-Port [$DB_PORT]"
    if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = $DB_PORT }

    $envContent = @"
POSTGRES_USER=$pgUser
POSTGRES_PASSWORD=$pgPassPlain
APP_PORT=$appPort
DB_PORT=$dbPort
JWT_SECRET=$jwtSecret
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

# Read actual port from .env
$envLines = Get-Content $envFile
$portLine = $envLines | Where-Object { $_ -match "^APP_PORT=" } | Select-Object -First 1
if ($portLine) { $APP_PORT = [int](($portLine -split "=",2)[1] -replace "#.*","" -replace "\s","") }

$ruleName = "Kompetenzen-Tool (Port $APP_PORT)"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Protocol TCP -LocalPort $APP_PORT `
        -Action Allow -Profile Any | Out-Null
    Write-OK "Firewall-Regel angelegt: $ruleName"
} else {
    Write-OK "Firewall-Regel bereits vorhanden: $ruleName"
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
@("data", "app\TexTemplate") | ForEach-Object {
    $dir = Join-Path $REPO_DIR $_
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-OK "Erstellt: $_"
    } else {
        Write-OK "Vorhanden: $_"
    }
}

# ---------------------------------------------------------------------------
# 9. Build & start containers
# ---------------------------------------------------------------------------
Write-Step "Docker-Container bauen und starten"
Set-Location $REPO_DIR
docker compose up --build -d
Write-OK "Container gestartet"

# ---------------------------------------------------------------------------
# 10. Admin-Konto anlegen (falls noch keins vorhanden)
# ---------------------------------------------------------------------------
Write-Step "Warte auf Backend"
Write-Host "    " -NoNewline
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 2
    try {
        $null = Invoke-RestMethod "http://localhost:$APP_PORT/api/health" -ErrorAction Stop
        $backendReady = $true
        break
    } catch {}
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $backendReady) {
    Write-Warn "Backend nicht erreichbar. Admin-Konto bitte manuell unter http://localhost:$APP_PORT/login anlegen."
} else {
    Write-OK "Backend bereit"
    $status = Invoke-RestMethod "http://localhost:$APP_PORT/api/auth/status" -ErrorAction SilentlyContinue
    if ($status -and $status.needs_setup) {
        Write-Step "Admin-Konto anlegen"
        $adminUser = Read-Host "    Admin-Benutzername"
        if ([string]::IsNullOrWhiteSpace($adminUser)) { $adminUser = "admin" }
        do {
            $adminPass = Read-Host "    Admin-Passwort (mind. 8 Zeichen)" -AsSecureString
            $adminPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass)
            )
            if ($adminPassPlain.Length -lt 8) { Write-Warn "Passwort zu kurz, bitte erneut eingeben." }
        } while ($adminPassPlain.Length -lt 8)
        $body = @{ username = $adminUser; password = $adminPassPlain } | ConvertTo-Json
        try {
            $null = Invoke-RestMethod "http://localhost:$APP_PORT/api/auth/setup" `
                -Method POST -Body $body -ContentType "application/json"
            Write-OK "Admin-Konto '$adminUser' angelegt"
        } catch {
            Write-Warn "Fehler beim Anlegen des Admin-Kontos: $_"
            Write-Warn "Bitte manuell unter http://localhost:$APP_PORT/login anlegen."
        }
    } else {
        Write-OK "Admin-Konto bereits vorhanden"
    }
}

# ---------------------------------------------------------------------------
# 11. Access info
# ---------------------------------------------------------------------------
Write-Step "Fertig!"

$lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual" } |
          Where-Object { $_.IPAddress -notlike "169.*" -and $_.IPAddress -notlike "127.*" } |
          Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "  App:     http://localhost:$APP_PORT" -ForegroundColor White
if ($lanIP) {
    Write-Host "  Netzwerk: http://${lanIP}:$APP_PORT" -ForegroundColor White
}
Write-Host ""
Write-Host "  Logs:       docker compose logs -f" -ForegroundColor DarkGray
Write-Host "  Stoppen:    docker compose down" -ForegroundColor DarkGray
Write-Host "  Neu bauen:  docker compose up --build -d" -ForegroundColor DarkGray
Write-Host ""
