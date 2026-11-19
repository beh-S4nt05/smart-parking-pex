#!/usr/bin/env bash
# Desliga a exposicao publica e o ambiente de piloto sem apagar o banco.
# Chamado automaticamente pelo systemd timer de expiracao, ou manualmente.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$ROOT/src/docker-compose.piloto.yml"
ENV="$ROOT/src/.env.piloto"
ERRO=0

printf 'Encerrando Smart Parking V1 - piloto de 14 dias\n'
if command -v tailscale >/dev/null 2>&1; then
  if tailscale funnel --https=443 off; then
    printf 'OK: API nao esta mais publicada pelo Funnel na porta 443\n'
  else
    printf 'ATENCAO: nao consegui desligar o Funnel; revisar tailscale funnel status\n' >&2
    ERRO=1
  fi
else
  printf 'ATENCAO: Tailscale nao encontrado neste host\n' >&2
  ERRO=1
fi

if command -v docker >/dev/null 2>&1 && [ -f "$ENV" ] && [ -f "$COMPOSE" ]; then
  if docker compose --env-file "$ENV" -f "$COMPOSE" stop; then
    printf 'OK: containers de API e banco do piloto parados, volume preservado\n'
  else
    printf 'ATENCAO: falha ao parar containers do piloto\n' >&2
    ERRO=1
  fi
else
  printf 'ATENCAO: Docker/compose ou .env.piloto indisponivel. Verifique manualmente.\n' >&2
  ERRO=1
fi

printf 'Cloudflare Pages: retire o site publico manualmente apos o piloto.\n'
exit "$ERRO"
