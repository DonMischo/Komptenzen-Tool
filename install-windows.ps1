# install-windows.ps1
# Kompetenzen-Tool - Windows 11 + Docker Desktop + WSL2 setup
# Run as Administrator in PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\install-windows.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
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
        Write-Error "winget nicht gefunden. Bitte App-Installer aus dem Microsoft Store installieren oder Docker Desktop manuell installieren."
    }

    winget install --id Docker.DockerDesktop --exact --silent --accept-package-agreements --accept-source-agreements
    Write-OK "Docker Desktop installiert."
    Write-Warn "Bitte Docker Desktop starten, Lizenzbedingungen akzeptieren und Skript erneut ausfuehren."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    exit 0
}

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

    # Auto-generate JWT secret
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

    # Fresh credentials — remove old DB volume so PostgreSQL initialises with new password
    $volumeName = (Split-Path -Leaf $REPO_DIR).ToLower() -replace '[^a-z0-9]',''
    $volumeName = "${volumeName}_pgdata"
    $volExists = docker volume ls --quiet --filter "name=$volumeName" 2>&1
    if ($volExists) {
        docker compose down --volumes 2>&1 | Out-Null
        Write-OK "Altes Datenbankvolume entfernt (neue Zugangsdaten erfordern frische DB)"
    }
} else {
    Write-OK ".env bereits vorhanden"
}

# ---------------------------------------------------------------------------
# Admin credentials (collected now, applied after containers start)
# ---------------------------------------------------------------------------
Write-Step "Admin-Konto konfigurieren"
$adminUser = Read-Host "    Admin-Benutzername [admin]"
if ([string]::IsNullOrWhiteSpace($adminUser)) { $adminUser = "admin" }
do {
    $adminPass = Read-Host "    Admin-Passwort (mind. 8 Zeichen)" -AsSecureString
    $adminPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass)
    )
    if ($adminPassPlain.Length -lt 8) { Write-Warn "Passwort zu kurz, bitte erneut eingeben." }
} while ($adminPassPlain.Length -lt 8)
Write-OK "Admin-Konto vorgemerkt: $adminUser"

Write-Step "Benutzer-Konto konfigurieren (oeffentliche Ansicht)"
$publicUser = Read-Host "    Benutzername [lehrer]"
if ([string]::IsNullOrWhiteSpace($publicUser)) { $publicUser = "lehrer" }
do {
    $publicPass = Read-Host "    Passwort (mind. 8 Zeichen)" -AsSecureString
    $publicPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($publicPass)
    )
    if ($publicPassPlain.Length -lt 8) { Write-Warn "Passwort zu kurz, bitte erneut eingeben." }
} while ($publicPassPlain.Length -lt 8)
Write-OK "Benutzer-Konto vorgemerkt: $publicUser"

# Read actual port from .env
$envLines = Get-Content $envFile
$portLine = $envLines | Where-Object { $_ -match "^APP_PORT=" } | Select-Object -First 1
if ($portLine) { $APP_PORT = [int](($portLine -split "=",2)[1] -replace "#.*","" -replace "\s","") }

# ---------------------------------------------------------------------------
# SSL-Zertifikat (selbstsigniert)
# ---------------------------------------------------------------------------
Write-Step "SSL-Zertifikat pruefen"
$sslDir = Join-Path $REPO_DIR "ssl"
if (-not (Test-Path $sslDir)) { New-Item -ItemType Directory -Path $sslDir | Out-Null }
$certFile = Join-Path $sslDir "cert.pem"
$keyFile  = Join-Path $sslDir "key.pem"
if (-not (Test-Path $certFile) -or -not (Test-Path $keyFile)) {
    # Use .NET to create a self-signed cert and export as PEM
    $cert = New-SelfSignedCertificate `
        -DnsName "kompetenzen-tool" `
        -CertStoreLocation "Cert:\LocalMachine\My" `
        -NotAfter (Get-Date).AddYears(10) `
        -KeyAlgorithm RSA -KeyLength 2048
    # Export cert (public) as PEM
    $certBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    $certB64   = [Convert]::ToBase64String($certBytes, 'InsertLineBreaks')
    [IO.File]::WriteAllText($certFile, "-----BEGIN CERTIFICATE-----`n$certB64`n-----END CERTIFICATE-----`n")
    # Export private key as PEM via openssl if available, else use certutil
    $pfxPath = Join-Path $env:TEMP "kt_tmp.pfx"
    $pfxPwd  = ConvertTo-SecureString "tmp" -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPwd | Out-Null
    $opensslCmd = Get-Command openssl -ErrorAction SilentlyContinue
    if ($opensslCmd) {
        & openssl pkcs12 -in $pfxPath -nocerts -nodes -passin pass:tmp -out $keyFile 2>$null
    } else {
        # Fallback: use Docker to run openssl
        docker run --rm -v "${env:TEMP}:/tmp" alpine/openssl `
            pkcs12 -in /tmp/kt_tmp.pfx -nocerts -nodes -passin pass:tmp -out /tmp/kt_key.pem 2>$null
        Copy-Item (Join-Path $env:TEMP "kt_key.pem") $keyFile
    }
    Remove-Item $pfxPath -ErrorAction SilentlyContinue
    # Clean up from cert store
    Remove-Item "Cert:\LocalMachine\My\$($cert.Thumbprint)" -ErrorAction SilentlyContinue
    Write-OK "Selbstsigniertes Zertifikat erstellt (gueltig 10 Jahre)"
} else {
    Write-OK "SSL-Zertifikat bereits vorhanden"
}

# ---------------------------------------------------------------------------
# 5. Windows Firewall
# ---------------------------------------------------------------------------
Write-Step "Windows Firewall"

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
@("data", "app\TexTemplate", "zeugnisse") | ForEach-Object {
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
# 9. Admin-Konto anlegen
# ---------------------------------------------------------------------------
Write-Step "Warte auf Backend"
Write-Host "    " -NoNewline
$backendReady = $false
for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep 3
    $logs = docker compose logs backend 2>&1
    if ($logs -match "Application startup complete") { $backendReady = $true; break }
    Write-Host "." -NoNewline
}
Write-Host ""

if (-not $backendReady) {
    Write-Warn "Timeout — versuche Admin-Erstellung trotzdem..."
}

Write-Step "Konten anlegen"

function Create-AppUser {
    param($uname, $upass, $urole)
    $tmpFile = Join-Path $env:TEMP "kt_create_user.py"
    # Single-quoted here-string: no PowerShell variable expansion, no quoting conflicts
    @'
import auth_pure, os
from sqlalchemy.orm import Session
uname = os.environ["KT_UNAME"]
upass = os.environ["KT_UPASS"]
urole = os.environ["KT_UROLE"]
exists = Session(auth_pure._auth_engine).query(auth_pure.AdminUser).filter_by(username=uname).first()
if not exists:
    auth_pure.create_user(uname, upass, role=urole)
    print("created")
else:
    print("exists")
'@ | Set-Content $tmpFile -Encoding UTF8
    $result = Get-Content $tmpFile | docker compose exec -T `
        -e KT_UNAME=$uname -e KT_UPASS=$upass -e KT_UROLE=$urole `
        backend python 2>&1
    Remove-Item $tmpFile -ErrorAction SilentlyContinue
    return $result
}

$rAdmin = Create-AppUser $adminUser $adminPassPlain "admin"
if ($rAdmin -match "created") { Write-OK "Admin-Konto '$adminUser' angelegt" }
elseif ($rAdmin -match "exists") { Write-OK "Admin-Konto '$adminUser' bereits vorhanden" }
else { Write-Warn "Fehler beim Anlegen des Admin-Kontos: $rAdmin" }

$rUser = Create-AppUser $publicUser $publicPassPlain "user"
if ($rUser -match "created") { Write-OK "Benutzer-Konto '$publicUser' angelegt" }
elseif ($rUser -match "exists") { Write-OK "Benutzer-Konto '$publicUser' bereits vorhanden" }
else { Write-Warn "Fehler beim Anlegen des Benutzer-Kontos: $rUser" }

# ---------------------------------------------------------------------------
# 10. Access info
# ---------------------------------------------------------------------------
Write-Step "Fertig!"

$lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual" } |
          Where-Object { $_.IPAddress -notlike "169.*" -and $_.IPAddress -notlike "127.*" } |
          Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "  App:      https://localhost:$APP_PORT" -ForegroundColor White
if ($lanIP) {
    Write-Host "  Netzwerk: https://${lanIP}:$APP_PORT" -ForegroundColor White
}
Write-Warn "Zertifikat ist selbstsigniert - Browser-Warnung einmalig bestaetigen."
Write-Host ""
Write-Host "  Logs:       docker compose logs -f" -ForegroundColor DarkGray
Write-Host "  Stoppen:    docker compose down" -ForegroundColor DarkGray
Write-Host "  Neu bauen:  docker compose up --build -d" -ForegroundColor DarkGray
Write-Host ""
