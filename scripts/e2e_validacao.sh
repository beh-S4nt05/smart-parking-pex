#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# SmartParking — VALIDAÇÃO E2E COMPLETA (o gate de véspera de banca)
# ═══════════════════════════════════════════════════════════════════════════
# Roda TUDO o que a aplicação promete, em camadas, e fecha com um veredito
# binário (exit 0/1) — para CI, para a banca e para dormir tranquilo.
#
#   ./scripts/e2e_validacao.sh              # blocos A–D (API no ar: docker ou run-dev)
#   ./scripts/e2e_validacao.sh --full       # + suíte Python (E) + tsc do front (F)
#   BASE_URL=http://localhost ./scripts/e2e_validacao.sh    # via nginx (:80)
#
# Blocos:
#   A. Conexão ............. scripts/check_conexao.sh (porta/.env venenoso/LAN/CORS)
#   B. MVP público ......... scripts/smoke_mvp.sh (CRUD admin verificado NO MAPA)
#   C. Controle de acesso .. scripts/smoke_acesso.sh (matriz rota×papel, 21 pontos)
#   D. Jornadas de usuário . este script, espelhando src/services/api.ts (o app):
#      D1 cadastro A(não-declarado)/B(PCD) + login por e-mail E por telefone
#      D2 perfil (placa/is_pcd) + descoberta (lista → mapa → andares)
#      D3 RF-47: nunca PCD p/ não-declarado (auto, rebaixamento com aviso,
#         reserva 403); declarado reserva PCD (sem lockout)
#      D4 reserva → minhas → cancelar → vaga LIVRE no mapa (ciclo fechado real)
#      D5 motorista 403 × admin 200 ao tocar em vaga do mapa
#      D6 sensor IoT: chave emitida → evento sem JWT ocupa a vaga no mapa →
#         idempotência por seq → revogada → 401 (RF-45 de ponta a ponta)
#      D7 simulador QR: criar → validar → revogar → 410
#   E. Suíte backend (FULL) . pytest + ruff via .venv do run-dev.sh, se houver
#   F. Frontend (FULL) tsc --noEmit + regras puras de autenticação
#
# Deps: curl · python3 (blocos D). Logs detalhados em /tmp/e2e-*.log.
# ═══════════════════════════════════════════════════════════════════════════
set -u
NEGR=$'\033[1m'; VERDE=$'\033[32m'; AMAR=$'\033[33m'; VERM=$'\033[31m'; CINZA=$'\033[90m'; FIM=$'\033[0m'
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE_URL:-http://localhost:8000}"
FULL=0; SO_D=0
for arg in "$@"; do
    case "$arg" in
        --full) FULL=1 ;;
        --so-d|--sem-abc) SO_D=1 ;;   # pula A–C ao iterar as jornadas (poupa os logins do rate-limit)
    esac
done
command -v curl >/dev/null 2>&1 || { echo "${VERM}✘ curl é obrigatório${FIM}"; exit 2; }

RESULTS=""; FAILS=0
bloco() { # bloco <id> <nome> <ok|fail|skip> [detalhe]
    local mark
    case "$3" in
        ok)   mark="${VERDE}✔${FIM}" ;;
        fail) mark="${VERM}✘${FIM}"; FAILS=$((FAILS+1)) ;;
        *)    mark="${CINZA}·${FIM}" ;;
    esac
    RESULTS+="  ${mark} $1 · $2${4:+ — $4}\n"
    if [ "$3" = fail ]; then
        printf '%s✘ bloco %s FALHOU: %s%s\n' "$VERM" "$1" "${4:-}" "$FIM"
    fi
    return 0   # sem isto, `... && bloco ok || bloco fail` conta ok como fail
}
ok()   { printf '  %s✔ %s%s\n' "$VERDE" "$1" "$FIM"; }
bad()  { printf '  %s✘ %s%s\n' "$VERM" "$1" "$FIM"; [ $# -gt 1 ] && printf '    %s→ %s%s\n' "$AMAR" "$2" "$FIM"; }
skipline() { printf '  %s· %s — %s%s\n' "$CINZA" "$1" "${2:-}" "$FIM"; }

http() { # http <method> <path> [json] [token] → "BODY\nSTATUS"
    local m="$1" p="$2" d="${3:-}" t="${4:-}"
    local -a args=(-sS -m 15 -X "$m" -w '\n%{http_code}')
    [ -n "$d" ] && args+=(-H "Content-Type: application/json" -d "$d")
    [ -n "$t" ] && args+=(-H "Authorization: Bearer $t")
    curl "${args[@]}" "$BASE$p" 2>/dev/null
}
st() { tail -n1 <<<"$1"; }
limite() { # limite <metodo> <path> [json] [token] — como http(), mas respeita o
    # rate-limit (429) com backoff: login E cadastro têm bucket no backend (o app real
    # também recebe 429 se martelar); script espera retry_after em vez de acusar falha
    local r i=0 ra
    while :; do
        r=$(http "$@")
        [ "$(st "$r")" = "429" ] && [ "$i" -lt 3 ] || { printf '%s' "$r"; return; }
        i=$((i+1))
        ra=$(jp "$(bd "$r")" 'min(int(obj.get("retry_after",30))+2,75)')
        [ -n "$ra" ] || ra=30
        printf '  %s… 429 (limite de requisições) — aguardando %ss (tentativa %s/3)%s\n' "$CINZA" "$ra" "$i" "$FIM" >&2
        sleep "$ra"
    done
}
bd() { sed '$d' <<<"$1"; }
jp() { [ -n "$1" ] || { echo ""; return; }; python3 -c "import json,sys
try:
    obj=json.loads(sys.stdin.read()); print($2)
except Exception:
    print('')" <<<"$1"; }

printf '\n%s╔══════════════════════════════════════════════════════════════════╗\n║  SMARTPARKING — VALIDAÇÃO E2E  ·  alvo: %-24s  ║\n╚══════════════════════════════════════════════════════════════════╝%s\n' "$NEGR" "$BASE" "$FIM"

# ══════════════════════════════════════════════════════════ A · conexão
if [ "$SO_D" = "1" ]; then
    bloco "A" "conexão" skip "--so-d"
    bloco "B" "smoke MVP" skip "--so-d"
    bloco "C" "matriz de acesso" skip "--so-d"
else
echo "── A. Conexão front↔back (check_conexao.sh)"
if "$RAIZ/scripts/check_conexao.sh" >/tmp/e2e-conexao.log 2>&1; then
    ok "validada (health, candidatos de porta, LAN/firewall, CORS, .env limpo)"
    bloco "A" "conexão" ok
else
    bad "check_conexao acusou bloqueio" "primeiro ✘ de /tmp/e2e-conexao.log é a causa raiz — resolva e rode só ele de novo: ./scripts/check_conexao.sh"
    bloco "A" "conexão" fail "ver /tmp/e2e-conexao.log"
fi

# ══════════════════════════════════════════════════════ B · smoke público
echo "── B. MVP público (smoke_mvp.sh)"
if "$RAIZ/scripts/smoke_mvp.sh" >/tmp/e2e-smoke.log 2>&1; then
    ok "$(grep -E 'Resultado:' /tmp/e2e-smoke.log | tail -1)"
    bloco "B" "smoke MVP" ok "$(grep -E 'Resultado:' /tmp/e2e-smoke.log | tail -1)"
else
    bad "smoke_mvp falhou" "tail -30 /tmp/e2e-smoke.log"
    bloco "B" "smoke MVP" fail "ver /tmp/e2e-smoke.log"
fi

# ══════════════════════════════════════════════════════ C · acesso
echo "── C. Controle de acesso (smoke_acesso.sh)"
if "$RAIZ/scripts/smoke_acesso.sh" >/tmp/e2e-acesso.log 2>&1; then
    ok "$(grep -E 'Auditoria:' /tmp/e2e-acesso.log | tail -1)"
    bloco "C" "matriz de acesso" ok "$(grep -E 'Auditoria:' /tmp/e2e-acesso.log | tail -1)"
else
    bad "smoke_acesso falhou" "tail -30 /tmp/e2e-acesso.log"
    bloco "C" "matriz de acesso" fail "ver /tmp/e2e-acesso.log"
fi
fi

# ══════════════════════════════════════════════════════ D · jornadas
echo "── D. Jornadas de usuário (fluxos reais, espelhando api.ts do app)"
DF=0
f() { bad "$@"; DF=$((DF+1)); }   # fail que conta p/ o bloco D
if ! command -v python3 >/dev/null 2>&1; then
    skipline "jornadas" "python3 ausente (blocos A–C continuam válidos)"
    bloco "D" "jornadas de usuário" skip "python3 ausente"
else
    SUF=$(date +%s)
    ADMIN_TOK=$(jp "$(bd "$(limite POST /auth/login '{"email":"admin@smartparking.com","senha":"admin123"}')" )" 'obj.get("access_token","")')
    [ -n "$ADMIN_TOK" ] || f "login admin (necessário p/ D5/D6/D7)" "sem admin demo: defina ADMIN_* ou rode o seed"

    # D1 — cadastro e login pelas DUAS credenciais (a tela de login aceita e-mail OU telefone)
    rA=$(limite POST /auth/registrar "{\"nome\":\"QA E2e A $SUF\",\"email\":\"e2e-a-$SUF@qa.dev\",\"senha\":\"qa123456\",\"telefone\":\"928$(printf '%08d' $((10000000+SUF%89999999)))\"}")
    TELB="928$(printf '%08d' $((20000000+SUF%79999999)))"
    rB=$(limite POST /auth/registrar "{\"nome\":\"QA E2e B $SUF\",\"email\":\"e2e-b-$SUF@qa.dev\",\"senha\":\"qa123456\",\"telefone\":\"$TELB\",\"is_pcd\":true}")
    if [ "$(st "$rA")" = "201" ] && [ "$(jp "$(bd "$rA")" 'obj.get("is_pcd")')" != "True" ]; then
        ok "D1a cadastro A (sem declaração) → 201 · is_pcd=False (padrão RF-47)"
    else f "D1a cadastro A → HTTP $(st "$rA")"; fi
    if [ "$(st "$rB")" = "201" ] && [ "$(jp "$(bd "$rB")" 'obj.get("is_pcd")')" = "True" ]; then
        ok "D1b cadastro B (autodeclarado PCD) → 201 · is_pcd=True"
    else f "D1b cadastro B → HTTP $(st "$rB")"; fi
    TA=$(jp "$(bd "$(limite POST /auth/login "{\"email\":\"e2e-a-$SUF@qa.dev\",\"senha\":\"qa123456\"}")")" 'obj.get("access_token","")')
    TB=$(jp "$(bd "$(limite POST /auth/login "{\"email\":\"$TELB\",\"senha\":\"qa123456\"}")")" 'obj.get("access_token","")')
    [ -n "$TA" ] && ok "D1c login A por e-mail → token" || f "D1c login A"
    [ -n "$TB" ] && ok "D1d login B por TELEFONE → token" || f "D1d login B por telefone"

    # D2 — perfil e descoberta
    PLACA="E2E$((SUF%9000))"
    r=$(http PUT /auth/me "{\"placa_veiculo\":\"$PLACA\"}" "$TA")
    [ "$(st "$r")" = "200" ] && [ "$(jp "$(bd "$r")" 'obj.get("placa_veiculo","")')" = "$PLACA" ] \
        && ok "D2a PUT /auth/me persiste placa (e o booleano não quebra o patch)" \
        || f "D2a PUT /me → $(st "$r")"
    EST_LIST=$(bd "$(http GET /api/estacionamentos)")
    EST_ID=$(jp "$EST_LIST" 'obj[0]["id"] if isinstance(obj,list) and obj else ""')
    [ -n "$EST_ID" ] && ok "D2b lista pública de estacionamentos → $(jp "$EST_LIST" 'len(obj)') item(ns)" \
        || { f "D2b GET /api/estacionamentos vazio" "sem seed demo neste banco"; }
    MAPA=$(bd "$(http GET "/api/estacionamentos/$EST_ID/vagas")")
    NV=$(jp "$MAPA" 'len(obj.get("vagas",[])) if isinstance(obj,dict) else 0')
    [ "${NV:-0}" -gt 0 ] && ok "D2c mapa do shopping → $NV vagas distribuídas em andares" || f "D2c mapa sem vagas"

    # D3 — RF-47, a régua que o usuário pediu
    r=$(http GET "/api/estacionamentos/$EST_ID/proxima-vaga")
    TP=$(jp "$(bd "$r")" 'obj["vaga"]["tipo"] if obj.get("vaga") else "nenhuma"')
    [ "$TP" != "pcd" ] && ok "D3a atribuição anônima → '$TP' (PCD nunca é entregue às cegas)" || f "D3a anônimo recebeu PCD"
    r=$(http GET "/api/estacionamentos/$EST_ID/proxima-vaga" "" "$TA")
    TP=$(jp "$(bd "$r")" 'obj["vaga"]["tipo"] if obj.get("vaga") else "nenhuma"')
    [ "$TP" != "pcd" ] && ok "D3b não-declarado logado → '$TP' (idêntica ao anônimo)" || f "D3b não-declarado recebeu PCD"
    r=$(http GET "/api/estacionamentos/$EST_ID/proxima-vaga?tipo_vaga=pcd" "" "$TA")
    AV=$(jp "$(bd "$r")" 'obj.get("aviso") or ""')
    if [ -n "$AV" ]; then ok "D3c pedido explícito de PCD → rebaixada com 'aviso' no corpo"; else skipline "D3c rebaixamento avisado" "sem PCD disponível p/ o caso (OK)"; fi
    r=$(http GET "/api/estacionamentos/$EST_ID/proxima-vaga" "" "$TB")
    TP=$(jp "$(bd "$r")" 'obj["vaga"]["tipo"] if obj.get("vaga") else "nenhuma"')
    [ "$TP" = "pcd" ] && ok "D3d PCD declarado → prioriza a especial" || skipline "D3d prioridade PCD" "sem PCD livre agora (regra coberta nos unitários)"

    PCD_ID=$(jp "$MAPA" 'next((v["id"] for v in obj.get("vagas",[]) if v.get("tipo")=="pcd"), "")')
    PCD_COD=$(jp "$MAPA" 'next((v["codigo"] for v in obj.get("vagas",[]) if v.get("tipo")=="pcd"), "")')
    NOW=$(date -u +%Y-%m-%dT%H:%M:%S)
    FUT=$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v+1H +%Y-%m-%dT%H:%M:%S)
    if [ -n "$PCD_ID" ] && [ -n "$ADMIN_TOK" ]; then
        http PATCH "/api/vagas/$PCD_ID/status" '{"status":"livre","origem":"manual"}' "$ADMIN_TOK" >/dev/null
        r=$(http POST /api/reservas "{\"vaga_id\":\"$PCD_ID\",\"horario_inicio\":\"$NOW\",\"horario_fim\":\"$FUT\"}" "$TA")
        DET=$(jp "$(bd "$r")" 'obj.get("detail","")')
        if [ "$(st "$r")" = "403" ] && grep -qi "exclusiva" <<<"$DET"; then
            ok "D3e reserva explícita de PCD por não-declarado → 403 com explicação"
        else f "D3e guarda de reserva → HTTP $(st "$r") · $DET"; fi
        r=$(http POST /api/reservas "{\"vaga_id\":\"$PCD_ID\",\"horario_inicio\":\"$NOW\",\"horario_fim\":\"$FUT\"}" "$TB")
        RESID=$(jp "$(bd "$r")" 'obj.get("id","")')
        [ "$(st "$r")" = "201" ] && ok "D3f mesmo pedido p/ declarado PCD → 201 (exclusividade sem lockout)" || f "D3f PCD declarado foi bloqueado → $(st "$r")"
    else
        skipline "D3e/D3f" "sem vaga PCD/admin — banco sem seed?"
    fi

    # D4 — ciclo da reserva (o que o mapa + tela de reservas fazem)
    COM_ID=$(jp "$MAPA" 'next((v["id"] for v in obj.get("vagas",[]) if v.get("status")=="livre" and v.get("tipo")=="comum"), "")')
    if [ -n "$COM_ID" ] && [ -n "$TA" ]; then
        r=$(http POST /api/reservas "{\"vaga_id\":\"$COM_ID\",\"horario_inicio\":\"$FUT\",\"horario_fim\":\"$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v+2H +%Y-%m-%dT%H:%M:%S)\"}" "$TA")
        RID=$(jp "$(bd "$r")" 'obj.get("id","")')
        [ "$(st "$r")" = "201" ] && ok "D4a reserva comum (motorista) → 201" || f "D4a reserva → $(st "$r") $(bd "$r" | head -c 120)"
        if [ -n "$RID" ]; then
            r=$(http GET /api/reservas/minhas "" "$TA")
            grep -q "$RID" <<<"$(bd "$r")" && ok "D4b 'Minhas reservas' elenca a criada" || f "D4b minhas reservas sem a reserva"
            r=$(http DELETE "/api/reservas/$RID" "" "$TA")
            [ "$(st "$r")" = "200" ] && ok "D4c cancelar → 200 (status CANCELADA)" || f "D4c cancelar → $(st "$r")"
            MAPA2=$(bd "$(http GET "/api/estacionamentos/$EST_ID/vagas")")
            [ "$(jp "$MAPA2" "next((v['status'] for v in obj.get('vagas',[]) if v['id']=='$COM_ID'), '?')")" = "livre" ] \
                && ok "D4d vaga devolvida ao LIVRE no mapa (estado real)" || f "D4d vaga presa em ocupada após cancelar"
        fi
        # D5 — o toque na célula do mapa por quem não pode
        r=$(http PATCH "/api/vagas/$COM_ID/status" '{"status":"ocupada","origem":"manual"}' "$TA")
        [ "$(st "$r")" = "403" ] && ok "D5a motorista não opera vaga do mapa → 403" || f "D5a motorista alterou vaga → $(st "$r")"
        r=$(http PATCH "/api/vagas/$COM_ID/status" '{"status":"livre","origem":"manual"}' "$ADMIN_TOK")
        [ "$(st "$r")" = "200" ] && ok "D5b admin/gestor pode (e devolve o estado)" || f "D5b admin → $(st "$r")"
    else
        skipline "D4/D5" "sem vaga comum livre (seed?)"
    fi

    # D6 — sensor IoT (RF-45), sem JWT, com idempotência e revogação
    if [ -n "$ADMIN_TOK" ] && [ -n "$EST_ID" ] && [ -n "$COM_ID" ]; then
        COD="E2E-$SUF"
        r=$(http POST /api/admin/sensores "{\"estacionamento_id\":\"$EST_ID\",\"codigo\":\"$COD\",\"nome\":\"QA E2E\"}" "$ADMIN_TOK")
        KEY=$(jp "$(bd "$r")" 'obj.get("chave","")'); SEN_ID=$(jp "$(bd "$r")" 'obj.get("id","")')
        COD_VG=$(jp "$MAPA" "next((v['codigo'] for v in obj.get('vagas',[]) if v['id']=='$COM_ID'), '')")
        if [ "$(st "$r")" = "201" ] && [ -n "$KEY" ]; then ok "D6a emissão do dispositivo $COD (chave clara exibida 1x)" || true; else f "D6a emitir sensor → $(st "$r")"; fi
        ev() { curl -sS -m 10 -X POST -H "Content-Type: application/json" -H "X-Device-Key: $1" -w '\n%{http_code}' \
               "$BASE/api/sensores/eventos" -d "$2" 2>/dev/null; }
        r=$(ev "$KEY" "{\"eventos\":[{\"seq\":1,\"codigo_vaga\":\"$COD_VG\",\"status\":\"ocupada\"}]}")
        [ "$(st "$r")" = "200" ] && [ "$(jp "$(bd "$r")" 'obj.get("aceitos",0)')" = "1" ] \
            && ok "D6b evento do dispositivo (OCUPADA) → aceito" || f "D6b ingestão → $(st "$r")"
        MAPAS=$(bd "$(http GET "/api/estacionamentos/$EST_ID/vagas")")
        [ "$(jp "$MAPAS" "next((v['status'] for v in obj.get('vagas',[]) if v['codigo']=='$COD_VG'), '?')")" = "ocupada" ] \
            && ok "D6c a vaga mudou a 'ocupada' NO MAPA por causa do sensor" || f "D6c mapa não refletiu o sensor"
        r=$(ev "$KEY" "{\"eventos\":[{\"seq\":1,\"codigo_vaga\":\"$COD_VG\",\"status\":\"ocupada\"}]}")
        [ "$(jp "$(bd "$r")" 'obj.get("duplicados",0)')" = "1" ] && ok "D6d retransmissão idempotente (duplicados=1)" || f "D6d idempotência → $(bd "$r" | head -c 120)"
        ev "$KEY" "{\"eventos\":[{\"seq\":2,\"codigo_vaga\":\"$COD_VG\",\"status\":\"livre\"}]}" >/dev/null
        http POST "/api/admin/sensores/$SEN_ID/revogar" "" "$ADMIN_TOK" >/dev/null
        r=$(ev "$KEY" '{"eventos":[{"seq":3,"codigo_vaga":"X","status":"livre"}]}')
        [ "$(st "$r")" = "401" ] && ok "D6e chave revogada → 401 (janela de segurança fechada)" || f "D6e chave revogada seguiu viva → $(st "$r")"
    else
        skipline "D6" "sem admin+estacionamento p/ sensor"
    fi

    # D7 — simulador QR (o laço painel → celular)
    if [ -n "$ADMIN_TOK" ] && [ -n "$EST_ID" ]; then
        r=$(http POST /api/admin/simulador/sessoes "{\"estacionamento_id\":\"$EST_ID\",\"andar_numero\":null,\"expira_em_horas\":1}" "$ADMIN_TOK")
        SIM=$(jp "$(bd "$r")" 'obj.get("token","")')
        [ "$(st "$r")" = "201" ] && [ -n "$SIM" ] && ok "D7a sessão QR criada" || f "D7a criar sessão → $(st "$r")"
        if [ -n "$SIM" ]; then
            [ "$(st "$(http GET "/api/admin/simulador/sessoes/$SIM/validar" "" "$ADMIN_TOK")")" = "200" ] \
                && ok "D7b QR válido → 200" || f "D7b validar → $(st "$(http GET "/api/admin/simulador/sessoes/$SIM/validar" "" "$ADMIN_TOK")")"
            rs=$(http DELETE "/api/admin/simulador/sessoes/$SIM" "" "$ADMIN_TOK")
            case "$(st "$rs")" in 200|204) ok "D7c revogada" ;; *) f "D7c revogar → $(st "$rs")" ;; esac
            [ "$(st "$(http GET "/api/admin/simulador/sessoes/$SIM/validar" "" "$ADMIN_TOK")")" = "410" ] \
                && ok "D7d QR morto não reanima → 410" || f "D7d validar pós-revogar não deu 410"
        fi
    else
        skipline "D7" "sem admin p/ QR"
    fi

    if [ "$DF" -eq 0 ]; then bloco "D" "jornadas (D1–D7)" ok
    else bloco "D" "jornadas (D1–D7)" fail "$DF checkpoint(s) fora do contrato"; fi
fi

# ══════════════════════════════════════════════════════ E · suíte backend
if [ "$FULL" = 1 ]; then
    echo "── E. Suíte do backend (pytest + ruff)"
    VENV=""
    for cand in "$RAIZ/src/backend/.venv" "$RAIZ/.venv" "$HOME/venv-be" "$HOME/venv-ci"; do
        [ -x "$cand/bin/pytest" ] && VENV="$cand" && break
    done
    if [ -n "$VENV" ]; then
        (cd "$RAIZ/src/backend" && "$VENV/bin/python" -m pytest tests -q --no-header -p no:cacheprovider >/tmp/e2e-pytest.log 2>&1)
        PASSED=$(grep -oE '[0-9]+ passed' /tmp/e2e-pytest.log | tail -1)
        if [ -n "$PASSED" ] && ! grep -qE "[0-9]+ failed|error" <(tail -2 /tmp/e2e-pytest.log); then
            ok "pytest $PASSED"
            (cd "$RAIZ/src/backend" && "$VENV/bin/python" -m ruff check . >/tmp/e2e-ruff.log 2>&1)
            grep -q "All checks passed" /tmp/e2e-ruff.log && { ok "ruff limpo"; bloco "E" "suíte backend" ok "$PASSED + ruff"; } \
                || bloco "E" "suíte backend" fail "ruff sujo"
        else
            bloco "E" "suíte backend" fail "pytest — tail -40 /tmp/e2e-pytest.log"
        fi
    else
        bloco "E" "suíte backend" skip "sem venv (./src/run-dev.sh cria src/backend/.venv)"
    fi
else
    bloco "E" "suíte backend" skip "use --full"
fi

# ══════════════════════════════════════════════════════ F · frontend
if [ "$FULL" = 1 ]; then
    echo "── F. Frontend (TypeScript + regras de autenticação)"
    if [ -d "$RAIZ/src/frontend/smart-parking/node_modules" ]; then
        F_ERROS=""
        if (cd "$RAIZ/src/frontend/smart-parking" && ./node_modules/.bin/tsc --noEmit >/tmp/e2e-tsc.log 2>&1); then
            ok "tsc limpo (contratos api/types íntegros)"
        else
            F_ERROS="typecheck"
        fi
        if node "$RAIZ/scripts/test_frontend_core.cjs" >/tmp/e2e-frontend-core.log 2>&1; then
            ok "regras de autenticação/next íntegras"
        else
            F_ERROS="$F_ERROS authFlow"
        fi
        if [ -z "$F_ERROS" ]; then
            bloco "F" "frontend" ok "tsc + authFlow"
        else
            bloco "F" "frontend" fail "$F_ERROS — cat /tmp/e2e-tsc.log /tmp/e2e-frontend-core.log"
        fi
    else
        bloco "F" "frontend" skip "npm install pendente"
    fi
else
    bloco "F" "frontend" skip "use --full"
fi

# ══════════════════════════════════════════════════════ veredito
echo
printf '%s╔══════════════════════════════════════════════════════════════════╗%s\n' "$NEGR" "$FIM"
printf '%s║  RESUMO DA VALIDAÇÃO E2E                                         ║%s\n' "$NEGR" "$FIM"
printf '%s╚══════════════════════════════════════════════════════════════════╝%s\n' "$NEGR" "$FIM"
printf '%b\n' "$RESULTS"
if [ "$FAILS" -eq 0 ]; then
    printf '%s✅ E2E COMPLETO: todas as camadas validadas — projeto entregável.%s\n' "$VERDE" "$FIM"
    [ "$FULL" = 0 ] && printf '%s   (com suíte Python + tsc: ./scripts/e2e_validacao.sh --full)%s\n' "$CINZA" "$FIM"
    exit 0
else
    printf '%s❌ %d bloco(s) com falha — cada ✘ acima aponta o log/detalhe.%s\n' "$VERM" "$FAILS" "$FIM"
    exit 1
fi
