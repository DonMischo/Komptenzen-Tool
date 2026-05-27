#!/usr/bin/env bash
# start.sh — Kompetenzen-Tool Quick-Start (Linux / macOS)
# Run this after install to start or update the app.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
step() { echo -e "\n${CYAN}==> $*${NC}"; }
ok()   { echo -e "    ${GREEN}[OK]${NC} $*"; }
warn() { echo -e "    ${YELLOW}[!!]${NC} $*"; }
die()  { echo -e "    ${RED}[ERR]${NC} $*" >&2; exit 1; }

step "Kompetenzen-Tool starten"

# ---------------------------------------------------------------------------
# 1. Docker vorhanden?
# ---------------------------------------------------------------------------
command -v docker &>/dev/null || die "Docker nicht gefunden. Bitte installieren: https://docs.docker.com/get-docker/"

# ---------------------------------------------------------------------------
# 2. Docker-Daemon läuft?
# ---------------------------------------------------------------------------
if ! docker info &>/dev/null; then
    warn "Docker-Daemon nicht erreichbar – versuche zu starten..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start docker
    else
        die "Docker-Daemon nicht aktiv. Bitte manuell starten."
    fi

    printf "    Warte auf Docker"
    for i in $(seq 1 20); do
        sleep 3
        if docker info &>/dev/null; then
            echo ""
            ok "Docker bereit"
            break
        fi
        printf "."
        if [[ $i -eq 20 ]]; then
            echo ""
            die "Docker ist nach 60 Sekunden immer noch nicht bereit."
        fi
    done
else
    ok "Docker läuft"
fi

# ---------------------------------------------------------------------------
# 3. Docker Compose verfügbar?
# ---------------------------------------------------------------------------
if ! docker compose version &>/dev/null; then
    die "Docker Compose nicht gefunden. Bitte Docker (>= 23) neu installieren."
fi

# ---------------------------------------------------------------------------
# 4. .env prüfen
# ---------------------------------------------------------------------------
step ".env prüfen"
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        warn ".env wurde aus .env.example erstellt."
        warn "Bitte .env anpassen (Passwörter, JWT_SECRET), dann Skript erneut starten."
        warn "  nano $SCRIPT_DIR/.env"
        exit 0
    else
        die ".env fehlt und keine .env.example gefunden. Bitte .env manuell erstellen."
    fi
else
    ok ".env gefunden"
fi

# ---------------------------------------------------------------------------
# 5. APP_PORT aus .env lesen
# ---------------------------------------------------------------------------
APP_PORT=$(grep "^APP_PORT=" "$SCRIPT_DIR/.env" | cut -d= -f2 | tr -d '[:space:]') || true
APP_PORT="${APP_PORT:-1337}"

# ---------------------------------------------------------------------------
# 6. Container bauen und starten
# ---------------------------------------------------------------------------
step "Container starten (docker compose up --build -d)"
docker compose up --build -d
ok "Container laufen"

# ---------------------------------------------------------------------------
# 7. Browser öffnen
# ---------------------------------------------------------------------------
URL="http://localhost:${APP_PORT}"
step "Fertig!"
echo ""
echo -e "  ${GREEN}App:${NC} $URL"
echo ""
echo "  Nützliche Befehle:"
echo "    Logs:      docker compose logs -f"
echo "    Stoppen:   docker compose down"
echo "    Neubauen:  docker compose up --build -d"
echo ""

# Try to open browser (non-fatal)
if command -v xdg-open &>/dev/null; then
    xdg-open "$URL" &>/dev/null &
elif command -v open &>/dev/null; then
    open "$URL"
fi
