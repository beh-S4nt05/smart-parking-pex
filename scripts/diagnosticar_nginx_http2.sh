#!/usr/bin/env bash
# Diagnostico somente leitura: Nginx local HTTP/1.1 x HTTP/2 na borda HTTPS.
# Uso: bash scripts/diagnosticar_nginx_http2.sh [host-publico-sem-caminho]
# Nao abre portas, nao reinicia containers, nao exibe variaveis ou segredos.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$ROOT/src/docker-compose.yml"
HOST="${1:-}"

echo "=== Smart Parking — diagnostico Nginx / HTTP2 (somente leitura) ==="
if ! command -v docker >/dev/null 2>&1; then
  echo "BLOQUEIO: Docker nao instalado."
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "BLOQUEIO: Docker Compose nao disponivel."
  exit 1
fi

echo
echo "[1] Servico nginx (compose local; piloto usa Funnel direto na API):"
docker compose -f "$COMPOSE" ps nginx || true

echo
echo "[2] Nginx -t (sintaxe da configuracao carregada):"
if docker compose -f "$COMPOSE" exec -T nginx nginx -t; then
  echo "OK: nginx -t aprovado."
else
  echo "BLOQUEIO: nginx -t falhou. Inspecione config/volumes do container."
fi

echo
echo "[3] Versao do Nginx em execucao:"
docker compose -f "$COMPOSE" exec -T nginx nginx -v || true

echo
echo "[4] Origem local HTTP/1.1 (porta 8080):"
if command -v curl >/dev/null 2>&1; then
  curl --http1.1 --max-time 8 -sS -o /dev/null \
    -w 'HTTP=%{http_code} protocolo=%{http_version} endpoint=http://127.0.0.1:8080/health\n' \
    http://127.0.0.1:8080/health || true
else
  echo "curl nao instalado"
fi

echo
echo "[5] Publicacao opcional HTTPS:"
if [ -n "$HOST" ]; then
  # Apenas hostname, sem path/query/credenciais/tokens, para evitar vazamentos.
  if [[ ! "$HOST" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$ ]]; then
    echo "Informe somente o hostname publico (ex.: maquina.tailnet.ts.net), sem https:// ou /rota."
    exit 2
  fi
  if command -v curl >/dev/null 2>&1; then
    curl --http2 --max-time 10 -sS -o /dev/null \
      -w "HTTP=%{http_code} protocolo=%{http_version} TLS=https://${HOST}/health\\n" \
      "https://${HOST}/health" || true
  fi
else
  echo "Nenhum host informado. HTTPS HTTP/2 e negociado no Funnel/Cloudflare, nao no Nginx local."
  echo "Execute com hostname publico como argumento depois da publicacao para conferir ALPN."
fi

echo
echo "Diagnostico concluido; nenhuma configuracao foi alterada."
