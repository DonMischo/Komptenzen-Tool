#!/usr/bin/env bash
# install-linux.sh
# Kompetenzen-Tool — Linux-Server / Ubuntu / Debian setup
# Usage:  bash install-linux.sh
#
# Tested on: Ubuntu 22.04 / 24.04, Debian 12
# Requires:  sudo privileges

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PORT=1337
DB_PORT=5432
REPO_URL="https://github.com/DonMischo/Komptenzen-Tool.git"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "\n${CYAN}==> $*${NC}"; }
ok()    { echo -e "    ${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "    ${YELLOW}[!!]${NC} $*"; }
die()   { echo -e "    ${RED}[ERR]${NC} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Root check
# ---------------------------------------------------------------------------
step "Berechtigungen pruefen"
if [[ $EUID -eq 0 ]]; then
    SUDO=""
    ok "Laeuft als root"
else
    SUDO="sudo"
    ok "Nutze sudo fuer privilegierte Befehle"
fi

# ---------------------------------------------------------------------------
# 2. Detect distro
# ---------------------------------------------------------------------------
step "Distribution erkennen"
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    DISTRO="${ID:-unknown}"
    ok "$PRETTY_NAME"
else
    die "Konnte /etc/os-release nicht lesen."
fi

case "$DISTRO" in
    ubuntu|debian|linuxmint|pop) PKG_MGR="apt-get" ;;
    fedora)                       PKG_MGR="dnf" ;;
    centos|rhel|rocky|almalinux) PKG_MGR="dnf" ;;
    arch|manjaro)                 PKG_MGR="pacman" ;;
    *)
        warn "Unbekannte Distribution '$DISTRO' – nehme apt-get an."
        PKG_MGR="apt-get"
        ;;
esac

# ---------------------------------------------------------------------------
# 3. System packages
# ---------------------------------------------------------------------------
step "Systempakete installieren"

if [[ "$PKG_MGR" == "apt-get" ]]; then
    $SUDO apt-get update -qq
    $SUDO apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg lsb-release \
        git postgresql-client ufw
    ok "Basispakete installiert"

elif [[ "$PKG_MGR" == "dnf" ]]; then
    $SUDO dnf install -y \
        ca-certificates curl gnupg git \
        postgresql ufw
    ok "Basispakete installiert"

elif [[ "$PKG_MGR" == "pacman" ]]; then
    $SUDO pacman -Syu --noconfirm \
        curl gnupg git postgresql-libs ufw
    ok "Basispakete installiert"
fi

# ---------------------------------------------------------------------------
# 4. Docker Engine
# ---------------------------------------------------------------------------
step "Docker Engine pruefen / installieren"

if command -v docker &>/dev/null; then
    ok "Docker bereits installiert: $(docker --version)"
else
    warn "Docker nicht gefunden – installiere Docker Engine..."

    if [[ "$PKG_MGR" == "apt-get" ]]; then
        # Official Docker repo
        $SUDO install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/${DISTRO}/gpg \
            | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

        echo "deb [arch=$(dpkg --print-architecture) \
signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DISTRO} \
$(lsb_release -cs) stable" \
            | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

        $SUDO apt-get update -qq
        $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin

    elif [[ "$PKG_MGR" == "dnf" ]]; then
        $SUDO dnf config-manager --add-repo \
            https://download.docker.com/linux/centos/docker-ce.repo
        $SUDO dnf install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin

    elif [[ "$PKG_MGR" == "pacman" ]]; then
        $SUDO pacman -S --noconfirm docker docker-compose
    fi

    ok "Docker installiert: $(docker --version)"
fi

# Docker Compose plugin
if ! docker compose version &>/dev/null; then
    die "Docker Compose nicht verfuegbar. Bitte manuell nachinstallieren."
fi
ok "Docker Compose: $(docker compose version --short)"

# ---------------------------------------------------------------------------
# 5. Add current user to docker group
# ---------------------------------------------------------------------------
step "Docker-Gruppe konfigurieren"
if [[ $EUID -ne 0 ]]; then
    if ! groups "$USER" | grep -q docker; then
        $SUDO usermod -aG docker "$USER"
        warn "Benutzer '$USER' zur Gruppe 'docker' hinzugefuegt."
        warn "Bitte neu einloggen oder 'newgrp docker' ausfuehren, dann Skript erneut starten."
        # Allow continuing in same session via newgrp trick
        SUDO_DOCKER="sudo docker"
    else
        ok "Bereits in docker-Gruppe"
        SUDO_DOCKER="docker"
    fi
else
    SUDO_DOCKER="docker"
fi

# ---------------------------------------------------------------------------
# 6. Enable & start Docker service
# ---------------------------------------------------------------------------
step "Docker-Dienst starten"
if command -v systemctl &>/dev/null; then
    $SUDO systemctl enable docker
    $SUDO systemctl start docker
    ok "Docker-Dienst aktiv"
else
    warn "systemctl nicht gefunden – Docker manuell starten falls noetig."
fi

# ---------------------------------------------------------------------------
# 7. Create .env if missing
# ---------------------------------------------------------------------------
step "Konfiguration (.env)"
ENV_FILE="$REPO_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    warn ".env nicht gefunden – wird angelegt"

    read -rp "    PostgreSQL-Benutzername [appuser]: " PG_USER
    PG_USER="${PG_USER:-appuser}"

    read -rsp "    PostgreSQL-Passwort: " PG_PASS; echo
    [[ -z "$PG_PASS" ]] && die "Passwort darf nicht leer sein."

    # Generate a random JWT secret; fall back to prompting if openssl not available
    JWT_SECRET_DEFAULT="$(openssl rand -hex 32 2>/dev/null || echo "")"
    if [[ -n "$JWT_SECRET_DEFAULT" ]]; then
        ok "JWT-Secret automatisch generiert"
        JWT_SECRET="$JWT_SECRET_DEFAULT"
    else
        read -rsp "    JWT-Secret (mind. 32 Zeichen): " JWT_SECRET; echo
        [[ ${#JWT_SECRET} -lt 32 ]] && die "JWT-Secret zu kurz (mind. 32 Zeichen)."
    fi

    read -rp "    Port [$APP_PORT]: " IN_APP_PORT
    APP_PORT="${IN_APP_PORT:-$APP_PORT}"

    read -rp "    DB-Port [$DB_PORT]: " IN_DB_PORT
    DB_PORT="${IN_DB_PORT:-$DB_PORT}"

    cat > "$ENV_FILE" <<EOF
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}
APP_PORT=${APP_PORT}
DB_PORT=${DB_PORT}
JWT_SECRET=${JWT_SECRET}
POSTGRES_URL=postgresql://${PG_USER}:${PG_PASS}@localhost:5432
EOF
    chmod 600 "$ENV_FILE"
    ok ".env erstellt (Berechtigungen: 600)"
else
    ok ".env bereits vorhanden"
    APP_PORT=$(grep "^APP_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d '[:space:]') || true
    APP_PORT="${APP_PORT:-1337}"
fi

# ---------------------------------------------------------------------------
# 8. Firewall (ufw)
# ---------------------------------------------------------------------------
step "Firewall – Port $APP_PORT"

if command -v ufw &>/dev/null; then
    UFW_STATUS=$($SUDO ufw status | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        $SUDO ufw allow "$APP_PORT"/tcp comment "Kompetenzen-Tool" 2>/dev/null || true
        ok "UFW: Port $APP_PORT freigegeben"
    else
        warn "UFW ist inaktiv – Port wird nicht geblockt, aber auch nicht explizit freigegeben."
        warn "Aktivieren mit: sudo ufw enable"
    fi
else
    warn "ufw nicht gefunden – Firewall manuell konfigurieren (Port $APP_PORT/tcp)."
fi

# ---------------------------------------------------------------------------
# 10. Required directories
# ---------------------------------------------------------------------------
step "Verzeichnisse pruefen"
for dir in data app/TexTemplate; do
    full="$REPO_DIR/$dir"
    if [[ ! -d "$full" ]]; then
        mkdir -p "$full"
        ok "Erstellt: $dir"
    else
        ok "Vorhanden: $dir"
    fi
done

# ---------------------------------------------------------------------------
# 11. Build & start
# ---------------------------------------------------------------------------
step "Docker-Container bauen und starten"
cd "$REPO_DIR"
$SUDO_DOCKER compose up --build -d
ok "Container gestartet"

# ---------------------------------------------------------------------------
# 12. Admin-Konto anlegen (falls noch keins vorhanden)
# ---------------------------------------------------------------------------
step "Warte auf Backend"
BACKEND_READY=0
printf "    "
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${APP_PORT}/api/health" > /dev/null 2>&1; then
        BACKEND_READY=1
        break
    fi
    sleep 2
    printf "."
done
echo ""

if [[ $BACKEND_READY -eq 0 ]]; then
    warn "Backend nicht erreichbar. Admin-Konto bitte manuell unter http://localhost:${APP_PORT}/login anlegen."
else
    ok "Backend bereit"
    NEEDS_SETUP=$(curl -sf "http://localhost:${APP_PORT}/api/auth/status" \
        | grep -o '"needs_setup":true' || true)
    if [[ -n "$NEEDS_SETUP" ]]; then
        step "Admin-Konto anlegen"
        read -rp "    Admin-Benutzername [admin]: " ADMIN_USER
        ADMIN_USER="${ADMIN_USER:-admin}"
        while true; do
            read -rsp "    Admin-Passwort (mind. 8 Zeichen): " ADMIN_PASS; echo
            [[ ${#ADMIN_PASS} -ge 8 ]] && break
            warn "Passwort zu kurz, bitte erneut eingeben."
        done
        HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
            -X POST "http://localhost:${APP_PORT}/api/auth/setup" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}" || echo "000")
        if [[ "$HTTP_CODE" == "200" ]]; then
            ok "Admin-Konto '${ADMIN_USER}' angelegt"
        else
            warn "Fehler beim Anlegen (HTTP $HTTP_CODE). Bitte manuell unter http://localhost:${APP_PORT}/login anlegen."
        fi
    else
        ok "Admin-Konto bereits vorhanden"
    fi
fi

# ---------------------------------------------------------------------------
# 13. Access info
# ---------------------------------------------------------------------------
step "Fertig!"

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || LAN_IP=""

echo ""
echo -e "  ${GREEN}App:      ${NC}http://localhost:${APP_PORT}"
if [[ -n "$LAN_IP" ]]; then
    echo -e "  ${GREEN}Netzwerk: ${NC}http://${LAN_IP}:${APP_PORT}"
fi
echo ""
echo -e "  ${NC}Logs:       docker compose logs -f"
echo -e "  ${NC}Stoppen:    docker compose down"
echo -e "  ${NC}Neu bauen:  docker compose up --build -d"
echo ""
