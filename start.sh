#!/usr/bin/env bash
# start.sh — Kompetenzen-Tool starten (setzt vorherige Installation voraus)
# Usage: bash start.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${CYAN}==> $*${NC}"; }
ok()   { echo -e "    ${GREEN}[OK]${NC} $*"; }
warn() { echo -e "    ${YELLOW}[!!]${NC} $*"; }
die()  { echo -e "    ${RED}[ERR]${NC} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Installation pruefen
# ---------------------------------------------------------------------------
step "Installation pruefen"

[[ -f "$REPO_DIR/.env" ]] \
    || die ".env nicht gefunden. Bitte zuerst install-linux.sh ausfuehren."

command -v docker &>/dev/null \
    || die "Docker nicht gefunden. Bitte zuerst install-linux.sh ausfuehren."

docker compose version &>/dev/null \
    || die "Docker Compose nicht gefunden. Bitte zuerst install-linux.sh ausfuehren."

ok ".env gefunden"

# Read APP_PORT from .env
APP_PORT=$(grep "^APP_PORT=" "$REPO_DIR/.env" | cut -d= -f2 | tr -d '[:space:]') || true
APP_PORT="${APP_PORT:-1337}"

# ---------------------------------------------------------------------------
# 2. Docker-Daemon pruefen
# ---------------------------------------------------------------------------
step "Docker pruefen"

if ! docker info &>/dev/null; then
    warn "Docker-Daemon nicht aktiv – versuche zu starten..."
    if command -v systemctl &>/dev/null; then
        sudo systemctl start docker
        sleep 3
    fi
    docker info &>/dev/null || die "Docker-Daemon konnte nicht gestartet werden. Bitte manuell starten: sudo systemctl start docker"
fi
ok "Docker laeuft"

# ---------------------------------------------------------------------------
# 3. Images pruefen (gebaut?)
# ---------------------------------------------------------------------------
step "Docker-Images pruefen"

IMG_COUNT=$(docker compose images -q 2>/dev/null | wc -l | tr -d ' ')
if [[ "$IMG_COUNT" -lt 2 ]]; then
    die "Docker-Images fehlen ($IMG_COUNT/3 gefunden). Bitte zuerst install-linux.sh ausfuehren."
fi
ok "Images vorhanden"

# ---------------------------------------------------------------------------
# 4. Container starten
# ---------------------------------------------------------------------------
step "Verzeichnisse pruefen"
# zeugnisse is bind-mounted into Docker — ensure it exists and is writable
# by the container's appuser (which may have a different UID than the host user).
mkdir -p "$REPO_DIR/zeugnisse"
chmod 777 "$REPO_DIR/zeugnisse"
ok "zeugnisse bereit"

step "Container starten"

RUNNING=$(docker compose ps --status running -q 2>/dev/null | wc -l | tr -d ' ')
if [[ "$RUNNING" -ge 3 ]]; then
    ok "Alle Container laufen bereits"
else
    docker compose up -d
    ok "Container gestartet"
fi

# ---------------------------------------------------------------------------
# 5. Datenbank-Health pruefen
# ---------------------------------------------------------------------------
step "Datenbank pruefen"

printf "    "
DB_OK=0
for i in $(seq 1 20); do
    HEALTH=$(docker compose ps --format '{{.Health}}' db 2>/dev/null || echo "")
    if [[ "$HEALTH" == "healthy" ]]; then
        DB_OK=1
        break
    fi
    printf "."
    sleep 2
done
echo ""
[[ $DB_OK -eq 1 ]] && ok "Datenbank gesund" \
    || warn "Datenbank-Health-Check schlug fehl (docker compose logs db)"

# ---------------------------------------------------------------------------
# 6. Backend pruefen
# ---------------------------------------------------------------------------
step "Backend pruefen"

printf "    "
BACKEND_OK=0
for i in $(seq 1 30); do
    if docker compose logs backend 2>&1 | grep -q "Application startup complete"; then
        BACKEND_OK=1
        break
    fi
    printf "."
    sleep 3
done
echo ""
[[ $BACKEND_OK -eq 1 ]] && ok "Backend bereit" \
    || warn "Backend antwortet noch nicht (docker compose logs backend)"

# ---------------------------------------------------------------------------
# 7. Frontend pruefen
# ---------------------------------------------------------------------------
step "Frontend pruefen"

printf "    "
FRONTEND_OK=0
for i in $(seq 1 15); do
    if curl -s --max-time 2 "http://localhost:${APP_PORT}" -o /dev/null 2>/dev/null; then
        FRONTEND_OK=1
        break
    fi
    printf "."
    sleep 2
done
echo ""
[[ $FRONTEND_OK -eq 1 ]] && ok "Frontend erreichbar" \
    || warn "Frontend noch nicht erreichbar unter Port $APP_PORT (docker compose logs frontend)"

# ---------------------------------------------------------------------------
# 8. Fertig
# ---------------------------------------------------------------------------
step "Fertig!"

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || LAN_IP=""

echo ""
echo -e "  ${GREEN}App:      ${NC}http://localhost:${APP_PORT}"
[[ -n "$LAN_IP" ]] && echo -e "  ${GREEN}Netzwerk: ${NC}http://${LAN_IP}:${APP_PORT}"
echo ""
echo -e "  ${NC}Logs:     docker compose logs -f"
echo -e "  ${NC}Stoppen:  docker compose down"
echo ""
