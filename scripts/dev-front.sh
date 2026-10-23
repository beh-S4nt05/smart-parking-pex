#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# SmartParking — launcher do frontend com .env auto-atualizado (rod.13)
# ═══════════════════════════════════════════════════════════════════════════
# É o "Expo alimentando a .env": detecta o MESMO IP LAN que o Metro vai
# publicar no QR (mesma heurística do check_conexao.sh: `ip route get` →
# `hostname -I`), grava EXPO_PUBLIC_API_URL_MOBILE no .env do front e sobe o
# `npx expo start -c` com o cache limpo (env congela no bundle sem -c).
#
#   ./scripts/dev-front.sh                # LAN default (porta 8000)
#   API_PORT=8010 ./scripts/dev-front.sh  # API em porta diferente
#   ./scripts/dev-front.sh --tunnel       # args extras vão p/ o expo start
#   ./scripts/dev-front.sh --no-start     # só escreve o .env (CI/teste)
#
# A WEB fica SEM variável de propósito: window.location já é sempre correta
# (inclusive quando outro dispositivo abre o http://IP:8081). Se você quiser
# forçar, use EXPO_PUBLIC_API_URL_WEB no .env manualmente.
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$RAIZ/src/frontend/smart-parking/.env"
API_PORT="${API_PORT:-8000}"
ARGS=()
START=1
for a in "$@"; do
    [ "$a" = "--no-start" ] && START=0 || ARGS+=("$a")
done

LAN_IP=""
if command -v ip >/dev/null 2>&1; then
    LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
fi
[ -z "$LAN_IP" ] && command -v hostname >/dev/null 2>&1 && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LAN_IP" ] && LAN_IP=$(node -e 'const os=require("os");for(const n of Object.values(os.networkInterfaces()).flat())if(n&&n.family==="IPv4"&&!n.internal){console.log(n.address);break}' 2>/dev/null || true)
if [ -z "$LAN_IP" ]; then
    echo "✘ não achei um IP LAN — rode com explícito:  LAN_IP=x.y.z.w ./scripts/dev-front.sh"
    exit 1
fi

URL="http://$LAN_IP:$API_PORT"
touch "$ENV"
if grep -qE '^[[:space:]]*EXPO_PUBLIC_API_URL_MOBILE=' "$ENV"; then
    sed -i -E "s|^[[:space:]]*#?[[:space:]]*EXPO_PUBLIC_API_URL_MOBILE=.*|EXPO_PUBLIC_API_URL_MOBILE=$URL|" "$ENV"
elif grep -qE '^[[:space:]]*#.*EXPO_PUBLIC_API_URL_MOBILE=' "$ENV"; then
    sed -i -E "s|^[[:space:]]*#[[:space:]]*EXPO_PUBLIC_API_URL_MOBILE=.*|EXPO_PUBLIC_API_URL_MOBILE=$URL|" "$ENV"
else
    printf 'EXPO_PUBLIC_API_URL_MOBILE=%s\n' "$URL" >> "$ENV"
fi
echo "✔ .env → EXPO_PUBLIC_API_URL_MOBILE=$URL  (web segue automática)"
[ "$START" = "0" ] && exit 0
cd "$RAIZ/src/frontend/smart-parking" && exec npx expo start -c "${ARGS[@]}"
