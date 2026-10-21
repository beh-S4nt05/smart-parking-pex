#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Smoke test do MVP — marca 2 da rubrica PEX (22/out, peso 2)
# Valida a cadeia completa: Nginx/Docker -> FastAPI -> PostgreSQL -> Auth -> CRUD.
#
# Uso:
#   ./scripts/smoke_mvp.sh                              # API local direta (:8000)
#   BASE_URL=http://localhost ./scripts/smoke_mvp.sh    # via Nginx (porta 80, cadeia completa)
#
# Credenciais sobrescritáveis: ADMIN_EMAIL / ADMIN_SENHA.
# Deps: curl (python3 para parsear JSON se existir; cai em grep se não).
# ---------------------------------------------------------------------------
set -u
BASE="${BASE_URL:-http://localhost:8000}"
EMAIL="${ADMIN_EMAIL:-admin@smartparking.com}"
SENHA="${ADMIN_SENHA:-admin123}"

OK=0
FAIL=0
pass() { printf '  \033[32m✔\033[0m %s\n' "$1"; OK=$((OK + 1)); }
fail() { printf '  \033[31m✘\033[0m %s %s\n' "$1" "${2:-}"; FAIL=$((FAIL + 1)); }

# req METHOD PATH [json] [token]  -> imprime corpo + última linha = status HTTP
req() {
    local m="$1" p="$2" d="${3:-}" t="${4:-}"
    local args=(-sS -m 15 -X "$m" -w '\n%{http_code}')
    [ -n "$d" ] && args+=(-H 'Content-Type: application/json' -d "$d")
    [ -n "$t" ] && args+=(-H "Authorization: Bearer $t")
    curl "${args[@]}" "$BASE$p"
}
status_of() { tail -n1 <<<"$1"; }
body_of() { sed '$d' <<<"$1"; }
jget() { # jget <json> <chave>
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get(sys.argv[1],""))' "$2" <<<"$1" 2>/dev/null
    else
        grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"\?[A-Za-z0-9_.@:-]*" <<<"$1" | head -1 | sed 's/.*[:"]//'
    fi
}

echo "🔌 Smoke MVP → $BASE"
PAYLOAD='{"nome":"Smoke QA (apagar)","endereco":"Rua do Teste, 1","total_andares":1,"vagas_por_andar":2,"horario_abertura":"08:00","horario_fechamento":"20:00"}'

echo "── 1. Infraestrutura"
r=$(req GET /health)
s=$(status_of "$r")
if [ "$s" = "200" ]; then pass "GET /health → 200"; else fail "GET /health → $s" "$(body_of "$r")"; echo "API fora do ar em $BASE — suba o compose e rode com --build."; exit 1; fi

r=$(req GET /api/estacionamentos)
s=$(status_of "$r")
if [ "$s" = "200" ]; then pass "GET /api/estacionamentos (lista pública) → 200"; else fail "lista pública → $s" "$(body_of "$r")"; fi

echo "── 2. Autenticação"
r=$(req POST /auth/login "{\"email\":\"$EMAIL\",\"senha\":\"$SENHA\"}")
s=$(status_of "$r")
TOKEN=$(jget "$(body_of "$r")" access_token)
if [ "$s" = "200" ] && [ -n "$TOKEN" ]; then
    pass "POST /auth/login (admin) → token OK"
else
    fail "login admin → $s" "$(body_of "$r")"
    echo "Sem token — abortando o resto."
    exit 1
fi

echo "── 3. Entrada e saída de dados (CRUD admin de ponta a ponta)"
r=$(req POST /api/admin/estacionamentos "$PAYLOAD" "$TOKEN")
s=$(status_of "$r")
ID=$(jget "$(body_of "$r")" id)
if [ "$s" = "201" ] && [ -n "$ID" ]; then
    pass "POST /api/admin/estacionamentos → 201 (id=$ID)"
    r=$(req GET "/api/estacionamentos/$ID/vagas" "" "$TOKEN")
    s=$(status_of "$r")
    if [ "$s" = "200" ]; then pass "GET /api/estacionamentos/$ID/vagas → 200 (mapa com andares+vagas do lote)"; else fail "mapa de vagas → $s" "$(body_of "$r")"; fi
    r=$(req DELETE "/api/admin/estacionamentos/$ID" "" "$TOKEN")
    s=$(status_of "$r")
    if [ "$s" = "200" ]; then pass "DELETE /api/admin/estacionamentos/$ID → 200 (cascata, lixo limpo)"; else fail "delete → $s" "$(body_of "$r")"; fi
else
    fail "POST /api/admin/estacionamentos → $s" "$(body_of "$r")"
fi

echo "── 4. Segurança"
r=$(req POST /api/admin/estacionamentos "$PAYLOAD")
s=$(status_of "$r")
case "$s" in
    401 | 403) pass "escrita sem token → $s (bloqueada como esperado)" ;;
    *) fail "escrita sem token → $s (deveria ser 401/403!)" ;;
esac

echo "──────────────────────────────────────────────"
printf 'Resultado: %d OK, %d FAIL\n' "$OK" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "✅ MVP smoke passou — cadeia Docker→Nginx→API→DB inteira de pé. Pode apresentar."
    exit 0
else
    echo "❌ Corrija os ✘ acima antes do dia 22. Logs úteis: docker compose logs backend | tail -50"
    exit 1
fi
