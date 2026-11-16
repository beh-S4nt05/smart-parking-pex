#!/usr/bin/env bash
# Smart Parking — Expo Go na LAN + detecção de API (Android/iOS).
# Uso: ./scripts/dev-front.sh [--no-start] [--no-check] [--tunnel]
#      LAN_IP=192.168.1.20 ./scripts/dev-front.sh
# O QR do Metro e o acesso à API são serviços diferentes: 8081 vs 8000.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONT="$RAIZ/src/frontend/smart-parking"
ENV="$FRONT/.env"
API_PORT="${API_PORT:-8000}"
START=1
CHECK=1
TUNNEL=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --no-start) START=0 ;;
    --no-check) CHECK=0 ;;
    --tunnel) TUNNEL=1; ARGS+=("$a") ;;
    --lan|--localhost) ARGS+=("$a") ;;
    *) ARGS+=("$a") ;;
  esac
done

[[ "$API_PORT" =~ ^[0-9]+$ ]] && (( API_PORT > 0 && API_PORT < 65536 )) ||
  { echo "Erro: API_PORT inválida: $API_PORT" >&2; exit 2; }

ipv4_privado() {
  local ip="$1" a b c d
  [[ "$ip" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]] || return 1
  IFS=. read -r a b c d <<< "$ip"
  (( a <= 255 && b <= 255 && c <= 255 && d <= 255 )) || return 1
  (( a == 10 || (a == 172 && b >= 16 && b <= 31) ||
     (a == 192 && b == 168) )) || return 1
}

# LAN_IP explícito prevalece (antes era ignorado pelo script).
LAN_IP="${LAN_IP:-}"
if [[ -z "$LAN_IP" ]] && command -v ip >/dev/null 2>&1; then
  # Rede/rota ativa do PC. Pode ser VPN; LAN_IP permite sobrepor.
  LAN_IP="$(ip -4 route get 1.1.1.1 2>/dev/null |
    awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1);exit}}' || true)"
fi
if ! ipv4_privado "$LAN_IP" && command -v hostname >/dev/null 2>&1; then
  while read -r candidato; do
    if ipv4_privado "$candidato"; then LAN_IP="$candidato"; break; fi
  done < <(hostname -I 2>/dev/null | tr ' ' '\n')
fi
if ! ipv4_privado "$LAN_IP"; then
  echo "Erro: IP LAN privado não detectado. Informe LAN_IP=192.168.x.y" >&2
  exit 2
fi

URL="http://$LAN_IP:$API_PORT"
mkdir -p "$FRONT"
touch "$ENV"
# Não altera EXPO_PUBLIC_API_URL_WEB nem variáveis globais: backend web usa host do navegador.
if grep -qE '^[[:space:]]*#?[[:space:]]*EXPO_PUBLIC_API_URL_MOBILE=' "$ENV"; then
  sed -i -E "s|^[[:space:]]*#?[[:space:]]*EXPO_PUBLIC_API_URL_MOBILE=.*|EXPO_PUBLIC_API_URL_MOBILE=$URL|" "$ENV"
else
  printf '\nEXPO_PUBLIC_API_URL_MOBILE=%s\n' "$URL" >> "$ENV"
fi

printf 'Smart Parking Expo Go\n  Metro: porta 8081 (QR)\n  API: %s\n' "$URL"
printf '  No celular: abra %s/health no navegador para comprovar a rede\n' "$URL"

if (( CHECK )) && (( START )); then
  command -v curl >/dev/null 2>&1 ||
    { echo "Erro: instale curl para validar o backend." >&2; exit 2; }
  if ! curl --noproxy '*' -fsS --connect-timeout 2 --max-time 5 "$URL/health" >/dev/null; then
    printf '\nErro: API não responde pelo IP LAN %s.\n' "$URL" >&2
    printf '  Confira: docker compose -f src/docker-compose.yml up -d backend postgres\n' >&2
    printf '  Se houver VPN ou múltiplos adaptadores: LAN_IP=IP_DO_WIFI ./scripts/dev-front.sh\n' >&2
    printf '  Verifique firewall TCP %s e isolamento de clientes no Wi-Fi.\n' "$API_PORT" >&2
    exit 1
  fi
  echo "  Backend /health OK neste PC (ainda é preciso testar pelo celular)."
fi
if (( TUNNEL )); then
  echo "AVISO: --tunnel encaminha o Metro, NÃO a API na porta $API_PORT."
  echo "       O telefone ainda precisa alcançar $URL, ou use uma API HTTPS válida."
fi
if (( ! START )); then
  echo "Configuração escrita; Metro não iniciado (--no-start)."
  exit 0
fi
cd "$FRONT"
# Fast Refresh carrega mudanças no JS/TS automaticamente enquanto o Metro estiver aberto.
if (( ! TUNNEL )) && [[ " ${ARGS[*]} " != *" --lan "* ]] && [[ " ${ARGS[*]} " != *" --localhost "* ]]; then
  ARGS=(--lan "${ARGS[@]}")
fi
exec npx expo start --clear "${ARGS[@]}"
