#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# SmartParking — constrói e valida o stack Docker inteiro (imagens + build).
# Feito para o cenário "apaguei as imagens/builds": um comando reconstroi tudo
# e PROVA que a cadeia Nginx→API→Postgres está viva (smoke_mvp.sh).
#
# Uso (de qualquer lugar do repo):
#   ./scripts/docker.sh up       # build + sobe tudo + smoke   (mais comum)
#   ./scripts/docker.sh build    # só (re)gera as imagens
#   ./scripts/docker.sh up-nb    # sobe sem rebuild (imagens recém-criadas)
#   ./scripts/docker.sh status   # docker compose ps
#   ./scripts/docker.sh logs     # segue logs de backend + nginx
#   ./scripts/docker.sh smoke    # roda smoke_mvp direto na API (8000)
#   ./scripts/docker.sh acesso   # auditoria de controle de acesso (multi-perfil)
#   ./scripts/docker.sh down     # para (mantém volume/dados)
#   ./scripts/docker.sh reset    # down -v (APAGA dados) + rebuild + smoke
# ---------------------------------------------------------------------------
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"   # raiz do repo
SRC="$RAIZ/src"

smoke() {
    echo "── aguardando /health responder (até 90s) ──"
    for _ in $(seq 1 90); do
        curl -sf http://localhost:8000/health >/dev/null 2>&1 && break
        sleep 1
    done
    "$RAIZ/scripts/smoke_mvp.sh"
}

cd "$SRC"
cmd="${1:-up}"
case "$cmd" in
    build)   docker compose build ;;
    up)      docker compose up -d --build && smoke ;;
    up-nb)   docker compose up -d && smoke ;;
    status)  docker compose ps ;;
    logs)    docker compose logs -f --tail=100 backend nginx ;;
    smoke)   smoke ;;
    acesso)  "$RAIZ/scripts/smoke_acesso.sh" ;;
    down)    docker compose down ;;
    reset)   docker compose down -v && docker compose up -d --build && smoke ;;
    *)
        sed -n '2,20p' "$0" | grep '^#' | cut -c 3-
        exit 1
        ;;
esac
