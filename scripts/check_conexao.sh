#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# SmartParking — VERIFICADOR DE CONEXÃO frontend ↔ backend (ticket QA-101)
# ═══════════════════════════════════════════════════════════════════════════
# Responde em segundos a ÚNICA pergunta que trava a entrega:
#   "o acesso entre o app e a API está OK? se não, o que exatamente?"
#
# Uso (de QUALQUER pasta do repo — o script se ancora sozinho):
#   ./scripts/check_conexao.sh              # diagnóstico completo
#   ./scripts/check_conexao.sh --fix        # + conserta o que é seguro (item 1)
#   BACKEND_URL=http://192.168.0.42:8000 ./scripts/check_conexao.sh   # API remota
#   ADMIN_EMAIL=... ADMIN_SENHA=...        # credenciais p/ o aperto de mão
#
# O que ele verifica (na ordem, cada um com o "o que fazer" impresso):
#   1. .env do front envenenado  → QA-101: overrides errados (localhost global,
#      IP mobile antigo ou qualquer chave apontando para o Metro :8081) congelam
#      a URL no bundle; --fix comenta o override inválido ou atualiza o IP.
#   2. Backend vivo em 3 candidatos: http://localhost:8000 (run-dev/docker),
#      :80 (nginx) e http://<IP-LAN>:8000 (o que o CELULAR usa — cai aqui, é
#      rede/firewall, não código).
#   3. Aperto de mão real: /health → login (token) → /auth/me com Bearer →
#      GET /api/estacionamentos (leitura pública) → /proxima-vaga SEM e COM
#      token (a rota pública não pode dar 401 quando o app manda Bearer).
#   4. CORS do ponto de vista da web: preflight OPTIONS /auth/login com
#      Origin http://localhost:8081 tem que voltar access-control-allow-origin.
#   5. Metro (npx expo start) na 8081 — e, quando responde, o BUNDLE servido é
#      inspecionado: contém o resolver vivo (hostUri) ou o localhost congelado?
#   6. Containers Docker relevantes (postgres healthy / backend healthy).
#
# Saída: tabela ✔/⚠/✘ + veredito. Exit code: 0 tudo ok · 1 falha crítica.
# Deps: curl. (python3 opcional, só p/ JSON bonito.)
# ═══════════════════════════════════════════════════════════════════════════
set -u

VERDE=$'\033[32m'; AMAR=$'\033[33m'; VERM=$'\033[31m'; AZUL=$'\033[36m'; NEGR=$'\033[1m'; FIM=$'\033[0m'
FIX=0
[ "${1:-}" = "--fix" ] && FIX=1

command -v curl >/dev/null 2>&1 || { echo "${VERM}✘ curl não está instalado — é o único requisito deste script.${FIM}"; exit 2; }

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
FRONT_ENV="$RAIZ/src/frontend/smart-parking/.env"
DIST_JS_GLOB="$RAIZ/src/frontend/smart-parking/dist/_expo/static/js/web/entry-*.js"
BACKEND_PORT="${BACKEND_PORT:-8000}"
NGINX_PORT="${NGINX_PORT:-80}"
METRO_PORT="${METRO_PORT:-8081}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@smartparking.com}"
ADMIN_SENHA="${ADMIN_SENHA:-admin123}"

OKS=0; WARNS=0; CRITS=0
pass() { OKS=$((OKS+1)); printf '  %s✔ %s%s\n' "$VERDE" "$1" "$FIM"; }
warn() { WARNS=$((WARNS+1)); printf '  %s⚠ %s%s\n' "$AMAR" "$1" "$FIM"; }
fail() { CRITS=$((CRITS+1)); printf '  %s✘ %s%s\n' "$VERM" "$1" "$FIM"; [ $# -gt 1 ] && printf '    %s→ %s%s\n' "$AZUL" "$2" "$FIM"; }
info() { printf '  · %s\n' "$1"; }

# http_get <method> <url> [extra curl args...] → imprime "STATUS\nCORPO"
http_get() {
    local m="$1" url="$2"; shift 2
    curl -sS -m 8 -X "$m" -w '\n%{http_code}' "$@" "$url" 2>/dev/null | awk 'NR>1{print prev} {prev=$0} END{print "BODY:" prev}' | head -c 4000
}
status_of() { tail -n1 <<<"$1"; }
body_of() { sed '$d' <<<"$1" | sed 's/^BODY://'; }

printf '%s\n═══ SMARTPARKING — VERIFICADOR DE CONEXÃO (QA-101) ═══%s\n' "$NEGR" "$FIM"

# ───────────────────────────────────────────────────────────── 1. .env front
echo "── 1. Configuração do app (src/frontend/smart-parking/.env)"
ENV_DIRTY=0
# LAN_IP calculado cedo (rod.13): usado aqui e na seção 2
LAN_IP=""
if command -v ip >/dev/null 2>&1; then
    LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
fi
[ -z "$LAN_IP" ] && command -v hostname >/dev/null 2>&1 && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

if [ -f "$FRONT_ENV" ]; then
    ENV_ACHOU=0
    # as TRÊS chaves que o resolver (src/services/apiBaseUrl.ts) respeita,
    # já na ordem de prioridade: _WEB/_MOBILE por plataforma, global depois
    for PAR in "EXPO_PUBLIC_API_URL_WEB:web" "EXPO_PUBLIC_API_URL_MOBILE:mobil" "EXPO_PUBLIC_API_URL:any"; do
        K="${PAR%%:*}"; ESC="${PAR##*:}"
        LINHA=$(grep -nE "^[[:space:]]*${K}=" "$FRONT_ENV" | head -1 || true)
        [ -z "$LINHA" ] && continue
        ENV_ACHOU=1
        N=${LINHA%%:*}
        VAL=${LINHA#*=}
        case "$VAL" in
            exp://*)
                if [ "$FIX" = 1 ]; then
                    cp "$FRONT_ENV" "$FRONT_ENV.bak-qa101"
                    sed -i "${N}s|^\(${K}=\)exp://|\1http://|" "$FRONT_ENV"
                    pass "--fix: $K usava exp:// (deep-link do QR) → convertida para http://; REINICIE com: npx expo start -c"
                else
                    fail "$K=$VAL começa com exp:// — é o deep-link do QR do Expo Go, não URL de API (o runtime agora converte sozinho, mas o .env deveria estar certo)"                          "rode:  ./scripts/check_conexao.sh --fix   (converte p/ http://)   ou   ./scripts/dev-front.sh"
                    ENV_DIRTY=1
                fi ;;
            *)
                if [[ "$VAL" == *:8081* ]]; then
                    if [ "$FIX" = 1 ]; then
                        cp "$FRONT_ENV" "$FRONT_ENV.bak-qa101"
                        sed -i "${N}s|^|# QA-101 (check_conexao --fix): |" "$FRONT_ENV"
                        pass "--fix: $K apontava para o Metro (:8081), não para a API — linha COMENTADA; a auto-detecção usa a porta $BACKEND_PORT; backup .env.bak-qa101; REINICIE com npx expo start -c"
                    else
                        fail "$K=$VAL mira a porta 8081 — essa é o METRO (serve o bundle), a API FastAPI é a $BACKEND_PORT" "rode ./scripts/check_conexao.sh --fix (comenta a linha e devolve a auto-detecção para a porta $BACKEND_PORT) ou remova essa chave"
                        ENV_DIRTY=1
                    fi
                elif [ "$ESC" != "web" ] && grep -qE 'localhost|127\.0\.0\.1|\[::1\]' <<<"$VAL"; then
                    if [ "$FIX" = 1 ]; then
                        cp "$FRONT_ENV" "$FRONT_ENV.bak-qa101"
                        sed -i "${N}s|^|# QA-101 (check_conexao --fix): |" "$FRONT_ENV"
                        pass "--fix: $K apontava p/ localhost (no celular, localhost é o PRÓPRIO celular) — linha COMENTADA, app cai na auto-detecção; backup .env.bak-qa101; REINICIE com npx expo start -c"
                    else
                        fail "$K=$VAL contém localhost — em Expo Go o celular vai procurar a API dentro dele mesmo (a web até aceitaria, mas esse valor global/amarrado congela as duas plataformas)"                              "rode:  ./scripts/dev-front.sh   (grava o IP LAN atual)   ou   ./scripts/check_conexao.sh --fix   (comenta a linha)"
                        ENV_DIRTY=1
                    fi
                elif [ "$ESC" != "web" ] && [ -n "$LAN_IP" ] && [[ "$VAL" =~ ^https?://([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
                    IPVAR="${BASH_REMATCH[1]}"
                    if [ "$IPVAR" != "$LAN_IP" ]; then
                        if [ "$FIX" = 1 ]; then
                            cp "$FRONT_ENV" "$FRONT_ENV.bak-qa101"
                            sed -i "${N}s|://${IPVAR}|://${LAN_IP}|" "$FRONT_ENV"
                            pass "--fix: $K tinha IP desatualizado ($IPVAR, rede mudou) → $LAN_IP; REINICIE com npx expo start -c"
                        else
                            fail "$K aponta para http://$IPVAR mas esta máquina hoje é $LAN_IP — IP do Wi-Fi mudou e o valor congelou no .env"                                  "rode:  ./scripts/dev-front.sh   ou   ./scripts/check_conexao.sh --fix   (ambos atualizam p/ $LAN_IP)"
                            ENV_DIRTY=1
                        fi
                    else
                        pass "$K=$VAL (IP LAN atual ✓ — same network do celular p/ este PC)"
                    fi
                else
                    pass "$K=$VAL (override por plataforma — o app usa isto antes de auto-resolver)"
                fi ;;
        esac
    done
    if [ "$ENV_ACHOU" = 0 ]; then
        pass "sem override ativo no .env → o app resolve a URL sozinho por plataforma (apiBaseUrl.ts)"
    fi
else
    pass "não existe .env (nem precisa: auto-detecção por plataforma está viva; p/ fixar o IP do celular use ./scripts/dev-front.sh)"
fi

# ───────────────────────────────────────────────────────── 2. backend vivo
echo "── 2. Backend alcançável? (3 candidatos)"
# LAN_IP já veio da seção 1 (hoist da rod.13); recalcula só se estiver vazio
if [ -z "$LAN_IP" ]; then
    if command -v ip >/dev/null 2>&1; then
        LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
    fi
    [ -z "$LAN_IP" ] && command -v hostname >/dev/null 2>&1 && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi

declare -a CANDIDATOS=()
[ -n "${BACKEND_URL:-}" ] && CANDIDATOS+=("$BACKEND_URL")
CANDIDATOS+=("http://localhost:$BACKEND_PORT" "http://localhost:$NGINX_PORT")
[ -n "$LAN_IP" ] && CANDIDATOS+=("http://$LAN_IP:$BACKEND_PORT")

BASE=""
LOCAL_OK=0
for c in "${CANDIDATOS[@]}"; do
    code=$(curl -sS -m 3 -o /dev/null -w '%{http_code}' "$c/health" 2>/dev/null || true)
    if [ "$code" = "200" ]; then
        pass "$c/health → 200"
        [ -z "$BASE" ] && BASE="$c"
        case "$c" in *"://$LAN_IP:"*) LAN_OK=1 ;; http://localhost:$BACKEND_PORT) LOCAL_OK=1 ;; esac
    else
        [ "$c" = "http://$LAN_IP:$BACKEND_PORT" ] && LANFAIL="$c"
        warn "$c/health → ${code:-sem resposta}"
    fi
done
if [ -z "$BASE" ]; then
    fail "nenhum backend respondeu em ${CANDIDATOS[*]}" \
         "suba a API:  ./src/run-dev.sh   (dev: banco no Docker + backend local)   OU o stack completo:  ./scripts/docker.sh up   — depois rode este verificador de novo"
else
    info "usando $BASE para o aperto de mão"
    # firewall/LAN: celular FALA com o IP LAN — se só localhost responde, é rede local/firewall, não código
    if [ -z "${BACKEND_URL:-}" ] && [ "$LOCAL_OK" = 1 ] && [ "${LAN_OK:-0}" != 1 ] && [ -n "$LAN_IP" ]; then
        fail "API OK em localhost, mas INACESSÍVEL em http://$LAN_IP:$BACKEND_PORT — o celular usa esse caminho" \
             "verifique Wi-Fi/AP isolation e permita TCP $BACKEND_PORT somente na sub-rede privada do Wi-Fi (perfil Privado no Windows); não faça port forwarding nem libere para qualquer origem"
        printf '    %s→ teste no navegador do celular: http://%s:%s/health — se não abrir, ainda é rede/firewall, não CORS%s\n' "$AZUL" "$LAN_IP" "$BACKEND_PORT" "$FIM"
    elif [ "${LAN_OK:-0}" = 1 ]; then
        pass "API responde pelo IP da LAN (http://$LAN_IP:$BACKEND_PORT) a partir deste PC — falta confirmar do aparelho"
    fi
fi

# ────────────────────────────────────────────────── 3. aperto de mão da API
if [ -n "$BASE" ]; then
    echo "── 3. Aperto de mão (o que o app realmente chama)"
    tok=""
    r=$(curl -sS -m 8 -X POST -H 'Content-Type: application/json' \
        -d "{\"email\":\"$ADMIN_EMAIL\",\"senha\":\"$ADMIN_SENHA\"}" \
        -w '\n%{http_code}' "$BASE/auth/login" 2>/dev/null || true)
    s=$(status_of "$r"); body=$(body_of "$r")
    TOK=$(grep -o '"access_token"[^,}]*' <<<"$body" | sed 's/.*: *"//; s/"//' | head -1)
    if [ "$s" = "200" ] && [ -n "$TOK" ]; then
        pass "POST /auth/login → 200 + access_token (rota de auth do app funciona)"
        tok="$TOK"
    else
        warn "POST /auth/login → $s (admin demo pode estar desligado em ENVIRONMENT=production; defina ADMIN_EMAIL/ADMIN_SENHA e rode de novo — as leituras abaixo ainda valem)"
    fi

    r=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' "$BASE/api/estacionamentos" 2>/dev/null || true)
    [ "$r" = "200" ] && pass "GET /api/estacionamentos (público) → 200" || fail "GET /api/estacionamentos → $r" "API respondeu o health mas não a lista — veja logs: docker logs smartparking-backend --tail 30"

    if [ -n "$tok" ]; then
        r=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $tok" "$BASE/auth/me" 2>/dev/null || true)
        [ "$r" = "200" ] && pass "GET /auth/me com Bearer → 200 (token válido de ponta a ponta)" || fail "GET /auth/me → $r" "o app salva o token mas não se reconhece — confira SECRET_KEY estável (não pode mudar entre reinícios do backend)"

        EST_ID=$(curl -sS -m 8 "$BASE/api/estacionamentos" 2>/dev/null | grep -o '"id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
        if [ -n "$EST_ID" ]; then
            r=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' "$BASE/api/estacionamentos/$EST_ID/proxima-vaga" 2>/dev/null || true)
            [ "$r" = "200" ] && pass "GET /proxima-vaga anônimo → 200 (rota pública viva)" || fail "GET /proxima-vaga (anônimo) → $r" "rota que deveria ser pública está falhando — a tela de busca de vaga quebra"
            r=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $tok" "$BASE/api/estacionamentos/$EST_ID/proxima-vaga" 2>/dev/null || true)
            [ "$r" = "200" ] && pass "GET /proxima-vaga COM token → 200 (token opcional não virou 401 — ACH-21)" || fail "GET /proxima-vaga com Bearer → $r" "regressão: rota pública que conheceu o token precisa aceitar token válido (get_usuario_logado_opcional)"
        else
            info "sem estacionamento cadastrado ainda — pulei /proxima-vaga (suba o seed: python seed_demo.py em src/backend/)"
        fi
    fi

    echo "── 4. CORS na visão do navegador (web em :$METRO_PORT → API)"
    r=$(curl -sSI -m 8 -X OPTIONS -H "Origin: http://localhost:$METRO_PORT" \
        -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type,authorization' \
        "$BASE/auth/login" 2>/dev/null || true)
    if grep -qi 'access-control-allow-origin' <<<"$r"; then
        pass "preflight OPTIONS → acesso liberado ($(grep -i 'access-control-allow-origin' <<<"$r" | head -1 | tr -d '\r'))"
    else
        fail "preflight CORS sem access-control-allow-origin" "a Web local usa localhost:8081 ou IP privado:8081; outra origem precisa ser explícita em CORS_ORIGINS. Não use '*' nem confunda CORS com rede nativa"
    fi
    r=$(curl -sSI -m 8 -X OPTIONS -H "Origin: https://cors-nao-autorizado.invalid" \
        -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type,authorization' \
        "$BASE/auth/login" 2>/dev/null || true)
    if grep -qi 'access-control-allow-origin' <<<"$r"; then
        fail "CORS respondeu a uma origem pública não autorizada" "remova curingas e deixe somente as origens reais do frontend em CORS_ORIGINS/CORS_ORIGIN_REGEX"
    else
        pass "origem pública não autorizada não recebe acesso CORS"
    fi
fi

# ───────────────────────────────────────────────────── 5. Metro / bundle
echo "── 5. O app em si (Metro na :$METRO_PORT + bundle servido)"
METRO=$(curl -sS -m 2 -o /dev/null -w '%{http_code}' "http://localhost:$METRO_PORT" 2>/dev/null || true)
if [ "$METRO" = "200" ]; then
    pass "Metro (npx expo start) responde em http://localhost:$METRO_PORT"
    BUNDLE=""
    for path in "/index.bundle?platform=web&dev=true&minify=false" "/node_modules/expo-router/entry.bundle?platform=web&dev=true&minify=false"; do
        resp=$(curl -sS -m 60 "http://localhost:$METRO_PORT$path" 2>/dev/null | head -c 12000000 || true)
        if grep -q '__BUNDLE_START_TIME__' <<<"$resp"; then BUNDLE="$resp"; break; fi
    done
    if [ -n "$BUNDLE" ]; then
        if grep -q 'resolverApiURL' <<<"$BUNDLE" || grep -q 'hostUri' <<<"$BUNDLE"; then
            pass "bundle do Metro contém o AUTO-DETECTOR (resolverApiURL/hostUri) — celular vai resolver o IP sozinho"
        elif grep -q '"http://localhost:8000"' <<<"$BUNDLE" && ! grep -q 'hostUri' <<<"$BUNDLE"; then
            fail "bundle servido está CONGELADO em localhost (mesmo com .env limpo? então é cache):" "npx expo start -c"
        else
            info "bundle principal válido; o resolvedor pode estar em chunk lazy — confira no console do Metro: '[smart-parking] API_URL = ...'"
        fi
    else
        info "bundle de dev não inspecionado (endpoints padrão não respondem) — vale o log do Metro: '[smart-parking] API_URL = ...'"
    fi
else
    warn "Metro não está de pé na :$METRO_PORT"
    printf '    %s→ para o app:  cd src/frontend/smart-parking && npx expo start   (w=web, QR=nativo; --tunnel se o celular não enxergar a rede)%s\n' "$AZUL" "$FIM"
fi
# bundle EXPORTADO (web production) — fingerprint do congelamento
for f in $DIST_JS_GLOB; do
    [ -e "$f" ] || continue
    if grep -q 'hostUri' "$f" 2>/dev/null; then
        pass "dist exportado tem o detector vivo (hostUri presente)"
    elif grep -q 'http://localhost:8000' "$f" 2>/dev/null; then
        fail "dist exportado está CONGELADO em localhost:8000 (QA-101 no build web)" "reexporte SEM o override ativo:  rm dist -r && npx expo export --platform web  (ou simplesmente use o Metro na 8081)"
    fi
    break
done

# ─────────────────────────────────────────────────────────── 6. Docker
echo "── 6. Containers relevantes (se a rota for Docker)"
for c in smartparking-postgres smartparking-backend smartparking-nginx; do
    st=$(docker inspect -f '{{.State.Status}}{{if .State.Health}}/{{.State.Health.Status}}{{end}}' "$c" 2>/dev/null || true)
    [ -z "$st" ] && { info "$c: não existe (ok se você roda só run-dev.sh)"; continue; }
    case "$st" in
        running/healthy|running) pass "$c: $st" ;;
        *) fail "$c: $st" "docker logs $c --tail 30" ;;
    esac
done

# ───────────────────────────────────────────────────────────── veredito
echo
printf '%s═══ VEREDITO: %d ok · %d atenção · %d crítico ═══%s\n' "$NEGR" "$OKS" "$WARNS" "$CRITS" "$FIM"
if [ "$CRITS" -eq 0 ]; then
    printf '%s✅ API E CONFIGURAÇÃO LOCAL VALIDADAS — sem bloqueio detectado pelo verificador.%s\n' "$VERDE" "$FIM"
    printf '   Teste físico ainda necessário: abrir o QR do Metro e conferir [smart-parking] API_URL no aparelho.\n'
    exit 0
else
    printf '%s❌ HÁ BLOQUEIO — resolva o primeiro ✘ acima e rode de novo (é sempre 1 coisa: .env, porta, firewall ou backend parado).%s\n' "$VERM" "$FIM"
    [ "$FIX" = 0 ] && [ "$ENV_DIRTY" = 1 ] && printf '   Dica: ./scripts/check_conexao.sh --fix resolve o item 1 sozinho.\n'
    exit 1
fi
