#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Auditoria de CONTROLE DE ACESSO — matriz rota × perfil (auditoria de 20/10).
# Cria um cenário isolado (2 estacionamentos QA + gestor/financeiro/motorista
# próprios), bate em cada rota sensível com e sem token e exige o código HTTP
# correto em 21 pontos. Ao final desfaz os estacionamentos e desativa os usuários.
#
# Uso:
#   ./scripts/smoke_acesso.sh                              # API local (8000)
#   BASE_URL=http://localhost ./scripts/smoke_acesso.sh    # via Nginx (80)
# ---------------------------------------------------------------------------
set -u
BASE="${BASE_URL:-http://localhost:8000}"
EMAIL="${ADMIN_EMAIL:-admin@smartparking.com}"
SENHA="${ADMIN_SENHA:-admin123}"
QA="qa$(date +%s)"

OK=0
FAIL=0
pass() { printf '  \033[32m✔\033[0m %s\n' "$1"; OK=$((OK + 1)); }
fail() { printf '  \033[31m✘\033[0m %s %s\n' "$1" "${2:-}"; FAIL=$((FAIL + 1)); }

req() {
    local m="$1" p="$2" d="${3:-}" t="${4:-}"
    local args=(-sS -m 15 -X "$m" -w '\n%{http_code}')
    [ -n "$d" ] && args+=(-H 'Content-Type: application/json' -d "$d")
    [ -n "$t" ] && args+=(-H "Authorization: Bearer $t")
    curl "${args[@]}" "$BASE$p"
}
status_of() { tail -n1 <<<"$1"; }
body_of() { sed '$d' <<<"$1"; }

# jget <json> <caminho.a.b> — atravessa dicts e índices numéricos
jget() {
    python3 -c 'import json,sys
try:
    obj=json.loads(sys.stdin.read())
    for k in sys.argv[1].split("."):
        obj=obj[int(k)] if isinstance(obj,list) else obj.get(k,"")
    print(obj if obj is not None else "")
except Exception:
    print("")' "$2" <<<"$1" 2>/dev/null
}

espera() { # espera <rotulo> <status esperado> <method> <path> [json] [token]
    local rot="$1" exp="$2" m="$3" p="$4" d="${5:-}" t="${6:-}" r s
    r=$(req "$m" "$p" "$d" "$t")
    s=$(status_of "$r")
    if [ "$exp" = "$s" ]; then pass "$rot → $s"
    else fail "$rot → esperado $exp, veio $s" "$(body_of "$r" | head -c 200)"; fi
}

echo "🛂 Auditoria de acesso → $BASE  (cenário $QA)"
r=$(req POST /auth/login "{\"email\":\"$EMAIL\",\"senha\":\"$SENHA\"}")
TOKEN=$(jget "$(body_of "$r")" access_token)
if [ -z "$TOKEN" ]; then echo "admin não logou em $BASE — abortando"; exit 1; fi
pass "login admin"

criar_est() { # criar_est <nome> -> id (payload nos nomes REAIS de EstacionamentoBase)
    local r
    r=$(req POST /api/admin/estacionamentos "{\"nome\":\"$1 ($QA)\",\"endereco\":\"Rua QA, 1\",\"total_andares\":1,\"total_vagas\":2,\"hora_abertura\":\"08:00\",\"hora_fechamento\":\"20:00\",\"taxa_hora\":10.0}" "$TOKEN")
    jget "$(body_of "$r")" id
}
gerar_andar_vagas() { # gerar_andar_vagas <est_id> <numero> <qtd> -> 0 se ok
    local r_andar r_id r_lote
    r_andar=$(req POST /api/admin/andares "{\"estacionamento_id\":\"$1\",\"numero_andar\":$2,\"capacidade\":$3}" "$TOKEN")
    if [ "$(status_of "$r_andar")" != "201" ]; then echo "andar falhou: $(status_of "$r_andar") $(body_of "$r_andar" | head -c 120)" >&2; return 1; fi
    r_id=$(jget "$(body_of "$r_andar")" id)
    r_lote=$(req POST /api/admin/vagas/lote "{\"andar_id\":\"$r_id\",\"quantidade\":$3,\"prefixo_codigo\":\"QA$2\"}" "$TOKEN")
    if [ "$(status_of "$r_lote")" != "201" ]; then echo "lote falhou: $(status_of "$r_lote") $(body_of "$r_lote" | head -c 120)" >&2; return 1; fi
    return 0
}
criar_user() { # criar_user <role> <est_id> -> email (⚠️ um local por linha: `local a=1 b=$a` expande ANTES de vincular)
    local role="$1"
    local est="${2:-}"
    local email="${QA}-${role}@qa.test.com" # sufixo role p/ e-mails únicos; ".test.com" p/ email-validator aceitar
    local vinc=""
    [ -n "$est" ] && vinc="\"estacionamento_id\":\"$est\","
    local r
    r=$(req POST /api/admin/usuarios "{\"nome\":\"QA $role\",\"email\":\"$email\",\"senha\":\"qa123456\",${vinc}\"role\":\"$role\"}" "$TOKEN")
    if [ "$(status_of "$r")" != "201" ]; then
        echo "  (falhou criar $role: $(status_of "$r") $(body_of "$r" | head -c 120))" >&2
    fi
    echo "$email"
}
login_as() {
    local r
    r=$(req POST /auth/login "{\"email\":\"$1\",\"senha\":\"qa123456\"}")
    jget "$(body_of "$r")" access_token
}

echo "── montando cenário"
EST_A=$(criar_est "QA Parking A")
EST_B=$(criar_est "QA Parking B")
if [ -z "$EST_A" ] || [ -z "$EST_B" ]; then echo "falha ao criar estacionamentos QA — abortando"; exit 1; fi
gerar_andar_vagas "$EST_A" 1 2 || exit 1
gerar_andar_vagas "$EST_B" 1 2 || exit 1
EM_GA=$(criar_user gestor "$EST_A")
EM_FB=$(criar_user financeiro "$EST_B")
EM_MO=$(criar_user usuario "")
T_GA=$(login_as "$EM_GA")
T_FB=$(login_as "$EM_FB")
T_MO=$(login_as "$EM_MO")
if [ -z "$T_GA" ] || [ -z "$T_FB" ] || [ -z "$T_MO" ]; then
    echo "não logou os usuários QA — abortando (criação de usuário falhou?)"; exit 1
fi
VAGA_A=$(jget "$(body_of "$(req GET "/api/estacionamentos/$EST_A/vagas" "" "$TOKEN")")" vagas.0.id)
VAGA_B=$(jget "$(body_of "$(req GET "/api/estacionamentos/$EST_B/vagas" "" "$TOKEN")")" vagas.0.id)
if [ -z "$VAGA_A" ] || [ -z "$VAGA_B" ]; then echo "estacionamento QA sem vagas (lote falhou?) — abortando"; exit 1; fi
echo "   A=$EST_A"
echo "   B=$EST_B"

echo "── 1. Escrita de vagas (era 100% pública antes da auditoria)"
espera "anon PATCH /api/vagas/{id}/status"           401 PATCH "/api/vagas/$VAGA_A/status" '{"status":"ocupada"}' ""
espera "motorista PATCH /api/vagas/{id}/status"      403 PATCH "/api/vagas/$VAGA_A/status" '{"status":"ocupada"}' "$T_MO"
espera "financeiro PATCH /api/vagas/{id}/status"     403 PATCH "/api/vagas/$VAGA_A/status" '{"status":"ocupada"}' "$T_FB"
espera "gestorA PATCH vaga do estacionamento B"      403 PATCH "/api/vagas/$VAGA_B/status" '{"status":"ocupada"}' "$T_GA"
espera "gestorA PATCH lote invadindo o B"            403 PATCH "/api/vagas/lote/status" "{\"vaga_ids\":[\"$VAGA_B\"],\"status\":\"ocupada\"}" "$T_GA"
espera "gestorA PATCH vaga do próprio A (ok)"        200 PATCH "/api/vagas/$VAGA_A/status" '{"status":"ocupada","origem":"manual"}' "$T_GA"

echo "── 2. Relatórios (detalhe financeiro × agregado público)"
espera "anon GET /api/relatorios/fluxo"              401 GET "/api/relatorios/fluxo?periodo=diario" ""
espera "motorista GET /api/relatorios/fluxo"         403 GET "/api/relatorios/fluxo?periodo=diario" "" "$T_MO"
espera "anon GET /api/relatorios/ocupacao"           401 GET "/api/relatorios/ocupacao?periodo=diario" ""
espera "gestorA GET fluxo do próprio A (ok)"         200 GET "/api/relatorios/fluxo?periodo=diario&estacionamento_id=$EST_A" "" "$T_GA"
espera "gestorA GET fluxo do B (intruso)"            403 GET "/api/relatorios/fluxo?periodo=diario&estacionamento_id=$EST_B" "" "$T_GA"
espera "financeiroB GET fluxo sem filtro (escopado)" 200 GET "/api/relatorios/fluxo?periodo=diario" "" "$T_FB"
espera "anon GET /api/relatorios/fluxo/publico"      200 GET "/api/relatorios/fluxo/publico?periodo=diario" ""
r=$(req GET "/api/relatorios/fluxo/publico?periodo=diario" "" "")
if grep -q '"registros"' <<<"$(body_of "$r")"; then
    fail "público VAZOU 'registros' (valores/placas!)"
else
    pass "público só com agregados (sem registros/valores)"
fi

echo "── 3. Painel administrativo (papéis)"
espera "anon GET /api/admin/dashboard"               401 GET "/api/admin/dashboard" ""
espera "motorista GET /api/admin/dashboard"          403 GET "/api/admin/dashboard" "" "$T_MO"
espera "gestor GET /api/admin/usuarios"              403 GET "/api/admin/usuarios" "" "$T_GA"
espera "gestor POST /api/admin/estacionamentos"      403 POST /api/admin/estacionamentos '{"nome":"QA intruso","endereco":"x","total_andares":1,"vagas_por_andar":1,"horario_abertura":"08:00","horario_fechamento":"20:00"}' "$T_GA"
espera "motorista POST /api/admin/simulador/sessoes" 403 POST /api/admin/simulador/sessoes "{\"estacionamento_id\":\"$EST_A\"}" "$T_MO"
espera "admin POST /api/admin/simulador/sessoes"     201 POST /api/admin/simulador/sessoes "{\"estacionamento_id\":\"$EST_A\"}" "$TOKEN"
espera "anon validar QR de sessão inexistente"       410 GET "/api/admin/simulador/sessoes/NAO-EXISTE-1234/validar" ""

echo "── 4. O que o motorista PODE (fluxo próprio dele)"
espera "motorista GET /auth/me"                      200 GET "/auth/me" "" "$T_MO"
espera "anon GET /api/reservas/minhas"               401 GET "/api/reservas/minhas" ""

echo "── 5. Limpeza do cenário"
for email in "$EM_GA" "$EM_FB" "$EM_MO"; do
    uid=$(jget "$(body_of "$(req GET /auth/me "" "$(login_as "$email")")")" id)
    [ -n "$uid" ] && req PATCH "/api/admin/usuarios/$uid/ativar-desativar" "" "$TOKEN" >/dev/null
done
pass "usuários QA desativados (a API não tem DELETE de usuário, por design)"
for E in "$EST_A" "$EST_B"; do
    r=$(req DELETE "/api/admin/estacionamentos/$E" "" "$TOKEN")
    if [ "$(status_of "$r")" = "200" ]; then pass "DELETE estacionamento QA $E (cascata)"; else fail "DELETE QA $E" "$(body_of "$r")"; fi
done

echo "──────────────────────────────────────────────"
printf 'Auditoria: %d OK, %d FAIL\n' "$OK" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "✅ Controle de acesso conforme a matriz: anonimato barrado, papéis respeitados, escopo por estacionamento."
    exit 0
else
    echo "❌ Divergência de controle de acesso — corrigir antes de expor a demo."
    exit 1
fi
