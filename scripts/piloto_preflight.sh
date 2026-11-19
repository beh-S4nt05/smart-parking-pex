#!/usr/bin/env bash
# Smart Parking V1: diagnostico somente de leitura do host Linux ANTES da publicacao.
# Uso: bash scripts/piloto_preflight.sh
# Nunca imprime segredos, tokens ou dados pessoais do banco.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PILOT_COMPOSE="$ROOT/src/docker-compose.piloto.yml"
PILOT_ENV="$ROOT/src/.env.piloto"
BLOQUEIOS=0

ok()   { printf 'OK    %s\n' "$*"; }
warn() { printf 'ATENCAO %s\n' "$*"; }
fail() { printf 'BLOQUEIO %s\n' "$*"; BLOQUEIOS=$((BLOQUEIOS+1)); }
exists() { command -v "$1" >/dev/null 2>&1; }

printf 'Smart Parking V1 - preflight do Linux para piloto de 14 dias\n\n'

if exists docker && docker compose version >/dev/null 2>&1; then
  ok "Docker Compose instalado"
  if docker info >/dev/null 2>&1; then ok "Daemon Docker acessivel"; else fail "Daemon Docker inacessivel: verifique serviço/permissao do usuario"; fi
else fail "Docker Compose nao encontrado"; fi

if exists node; then
  VERSION="$(node -p "process.versions.node" 2>/dev/null || true)"
  if node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>24 || a===24 && b>=19 ? 0 : 1)' >/dev/null 2>&1; then
    ok "Node.js $VERSION (SDK Expo 58)"
  else fail "Node.js $VERSION nao atende ao minimo 24.19"; fi
else fail "Node.js nao encontrado"; fi

if exists git; then
  ok "Git instalado"
  if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [ -f "$ROOT/src/frontend/smart-parking/eas.json" ]; then
      ok "Perfil EAS do APK existe nesta copia"
    else
      fail "Perfil EAS nao existe: PR de publicacao ainda nao esta nesta copia"
    fi
  else fail "Pasta atual nao e repositorio Git"; fi
else fail "Git nao encontrado"; fi

if exists tailscale; then
  ok "CLI Tailscale instalada"
  if tailscale status --json >/dev/null 2>&1; then
    ok "Tailscale responde; confirmar conta, MagicDNS e Funnel antes de expor"
  else warn "Tailscale ainda nao foi autenticado ou daemon esta parado"; fi
else warn "Tailscale nao instalado (necessario para API publica HTTPS)"; fi

if exists curl; then
  ok "curl instalado"
  if curl -fsS --max-time 3 http://127.0.0.1:8000/health >/dev/null 2>&1; then
    warn "A porta 8000 ja responde. Verifique se e o backend anterior antes de subir o piloto"
  else
    ok "API antiga nao respondeu em 127.0.0.1:8000 (nao prova porta livre)"
  fi
else fail "curl nao encontrado"; fi

if [ -f "$PILOT_COMPOSE" ]; then
  ok "Compose isolado do piloto presente"
else fail "Falta src/docker-compose.piloto.yml: atualize o repo apos aprovar PR #75"; fi

if [ -f "$PILOT_ENV" ]; then
  ok "Arquivo privado do piloto presente (conteudo nao sera exibido)"
  if exists docker && docker compose version >/dev/null 2>&1; then
    if docker compose --env-file "$PILOT_ENV" -f "$PILOT_COMPOSE" config --quiet >/dev/null 2>&1; then
      ok "Variaveis de ambiente do piloto passam pela validacao do Compose"
    else fail "Compose invalido ou segredo obrigatorio nao definido em src/.env.piloto"; fi
  fi
else warn "src/.env.piloto ainda nao foi criado; gere os segredos localmente antes de iniciar"; fi

if exists df; then
  DISPONIVEL="$(df -Pk "$ROOT" | awk 'NR==2{print $4}')"
  if [[ "$DISPONIVEL" =~ ^[0-9]+$ ]] && (( DISPONIVEL < 3145728 )); then
    warn "Menos de 3 GiB livres; Docker pode precisar de mais espaco"
  else ok "Espaco em disco consultado"; fi
fi

printf '\n'
if (( BLOQUEIOS > 0 )); then
  printf 'Preflight: %s bloqueio(s). Corrigir antes de expor a API.\n' "$BLOQUEIOS"
  exit 1
fi
printf 'Preflight local: sem bloqueios detectados. Ainda falta validar HTTPS, APK, FCM e 4G.\n'
