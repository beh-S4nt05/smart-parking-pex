#!/usr/bin/env bash
# Smart Parking — limpeza segura de branches antigas.
# Dry-run por padrão; --apply arquiva commits divergentes e apaga as 34 branches.
# Requer GitHub CLI autenticado com permissão de escrita no repositório.
set -Eeuo pipefail

REPO="beh-S4nt05/smart-parking-pex"
AUDIT_MAIN="707a1137c424bb8ca020133ef8acfb43e1db344f"
TAG_PREFIX="archive/2026-11-16"
APPLY=0
if [[ "${1:-}" == "--apply" && $# -eq 1 ]]; then
  APPLY=1
elif [[ $# -ne 0 && "${1:-}" != "--dry-run" ]]; then
  echo "Uso: $0 [--dry-run|--apply]" >&2
  exit 2
fi

fail() { echo "ERRO: $*" >&2; exit 1; }
command -v gh >/dev/null || fail "GitHub CLI não instalado (gh)"
gh auth status >/dev/null 2>&1 || fail "Faça login com: gh auth login"

declare -a LEGADAS=()
declare -A SHA_AUDITADO=() AHEAD=() EXISTE=()
while IFS='|' read -r branch sha ahead; do
  [[ -n "$branch" ]] || continue
  [[ "$branch" != "main" && "$branch" != "develop/v2" ]] || fail "Ref protegida no inventário"
  LEGADAS+=("$branch")
  SHA_AUDITADO["$branch"]="$sha"
  AHEAD["$branch"]="$ahead"
done <<'INVENTARIO_CONGELADO'
arena/acf78b1a-smart-parking-pex|c453ba63d46561f324d12c08853f17c725ace76c|0
arena/db7d0055-smart-parking-pex|07329c5618be3b8ab32eda1c543ec3d9a98bdb71|0
arena/e79f62a3-smart-parking-pex|cd390cb7b22353e3e387daa6b26675895be34b1a|0
arena/e120c38b-smart-parking-pex|c6308825ca7df23653abb5430f1dd6f77eaa214b|0
arena/fab11479-smart-parking-pex|bc30b755f180e9af7b4891abda279a6e1336381e|0
arena/1d7ed9f2-smart-parking-pex|7848ed93a9841958e66173860f281d362c12905a|0
arena/11a57e13-smart-parking-pex|e93a1b6159015cb04b1bcf18c345b6229251eda1|0
arena/83cd58bc-smart-parking-pex|fbe0f879e828652588cad337897c7521dfd4be8d|0
arena/992f9160-smart-parking-pex|2c04f016ba82cc0a87edd3cf9869767b28aa5610|0
arena/03867a8c-smart-parking-pex|cd72220a7345932f544ad8cb8d25a7e885d3998e|0
arena/71109ddc-smart-parking-pex|9b050dc889ac95736e142f32f5640c73e4802453|0
automation/expo-sdk-update|d090db39cd9821df3a7161f6b0dcaf595a801e5d|1
codex/center-panel-link|c5a8b759b1f82a53b38e397fdf62a8668bbe6970|2
codex/frontend-responsive-layout|c34162aa1719666b3b4513e5fae1b6f92210a6f9|0
codex/restore-parking-access-and-register-exit|9bef533e0a363e82d62bbbbad1514e434eb62c14|8
codex/role-matrix-shopping-finance-driver|21056a306292092edae155374c1945756e4dcacf|7
codex/ux-flow-rebuild|0dd8ade96b777b3e250289ed59a7c50896a8c0fa|13
docs/scope-driver-vehicle-eligibility|5e90d25eb057e1b9f4f954074c05dc30929fd569|0
feat/mobile-premium-presentation|c468efa9ae64cf79caf42a2a335f9ddd484202dc|0
feat/v1-multi-vehicle-management|21e373ef8dc327ffae7a9c79eb650031f106e1ce|0
feat/v1-registration-vehicle-benefits|cfd2a494882a76b8b4b58bc124797f8c32edebbd|13
feat/v1-vehicles-credentials-db|b2421cac6999ba27272720302552dcc80d585c58|0
fix/mobile-auth-web-hero-layout|cc042e187008bae52b7ea357c03e5fa1cde55894|0
fix/mobile-consistency-web-hero|59001b7f0b0504a757bd678d25f194a8d0c01387|0
fix/mobile-scroll-reserva-bordas|0889fd3a9e8f67ff2ec67de83bd807aa5f54f760|2
fix/simulador-lote-timezone-500|106bb1e2d3c30d04cac4e64da0c2a674e58e9951|0
fix/simulador-qr-http-500|106bb1e2d3c30d04cac4e64da0c2a674e58e9951|0
fix/v1-login-registered-users-shared-phone|19ba4c796edd1fd35304bae672af0c2a7f64f41f|0
security/v1-60-identity-mfa|8d87d996985d61656b64049c63af2913eb8da500|1
security/v1-61-sessions|eef50348a1629101ca70834219cb0d3a862a0fe3|1
security/v1-62-rbac-scope|d0b47837aa5671b6b044db7d13b0e869d24b0a39|0
security/v1-63-sensor-integrity|d60f6b05c57f5298915bce964b05b5c2533cd2fc|8
security/v1-64-pilot-hardening|67e81e3c6621d5bde92a573448e6251375db3d13|17
security/v1-65-audit-incidents|0bd68eab1c42dd04de94c98bcb5c7a3ab092fa9b|14
INVENTARIO_CONGELADO

[[ ${#LEGADAS[@]} -eq 34 ]] || fail "Inventário inesperado"
main_sha="$(gh api "repos/$REPO/branches/main" --jq '.commit.sha')" || fail "Falha lendo main"
[[ "$main_sha" == "$AUDIT_MAIN" ]] || fail "A main mudou desde a auditoria; refaça comparações antes de excluir branches!"
gh api "repos/$REPO/branches/develop/v2" --jq '.commit.sha' >/dev/null || fail "develop/v2 não existe"

# Abortamos se existir PR aberto: não destruir o HEAD de revisão em andamento.
open_prs="$(gh api --paginate "repos/$REPO/pulls?state=open&per_page=100" --jq '.[].number')" ||
  fail "Não foi possível consultar os PRs abertos"
[[ -z "$open_prs" ]] || fail "Existem PRs abertos: $open_prs"

# Não exclua refs novas/desconhecidas; elas não passaram pela auditoria.
nomes="$(gh api --paginate "repos/$REPO/branches?per_page=100" --jq '.[].name')" ||
  fail "Não foi possível enumerar as branches"
while IFS= read -r branch; do
  [[ -n "$branch" ]] || continue
  if [[ "$branch" == "main" || "$branch" == "develop/v2" ]]; then
    continue
  fi
  [[ -v SHA_AUDITADO["$branch"] ]] || fail "Branch nova não auditada: $branch"
  EXISTE["$branch"]=1
done <<< "$nomes"

echo "Repositório: $REPO"
echo "main: $main_sha"
echo "Alvo: somente main + develop/v2"
echo "Branches antigas detectadas: ${#EXISTE[@]}"
for branch in "${LEGADAS[@]}"; do
  [[ -v EXISTE["$branch"] ]] || continue
  atual="$(gh api "repos/$REPO/git/ref/heads/$branch" --jq '.object.sha')" ||
    fail "Não foi possível verificar $branch"
  [[ "$atual" == "${SHA_AUDITADO[$branch]}" ]] ||
    fail "O HEAD de $branch mudou: esperado ${SHA_AUDITADO[$branch]}, atual $atual"
  if (( AHEAD["$branch"] > 0 )); then
    echo "  ARQUIVAR E EXCLUIR: $branch (${AHEAD[$branch]} commits fora da main)"
  else
    echo "  EXCLUIR (ancestral): $branch"
  fi
done

if (( ! APPLY )); then
  echo ""
  echo "Nenhuma alteração realizada (dry-run)."
  echo "Para executar: bash scripts/limpar-branches-legadas.sh --apply"
  exit 0
fi

# 1. Criar e verificar tags dos HEADs divergentes ANTES de remover qualquer branch.
for branch in "${LEGADAS[@]}"; do
  (( AHEAD["$branch"] > 0 )) || continue
  ref="refs/tags/$TAG_PREFIX/$branch"
  api="repos/$REPO/git/ref/tags/$TAG_PREFIX/$branch"
  if atual_tag="$(gh api "$api" --jq '.object.sha' 2>/dev/null)"; then
    [[ "$atual_tag" == "${SHA_AUDITADO[$branch]}" ]] ||
      fail "Tag $ref existente aponta para outro commit: $atual_tag"
  else
    gh api --method POST "repos/$REPO/git/refs" \
      -f ref="$ref" -f sha="${SHA_AUDITADO[$branch]}" >/dev/null ||
      fail "Não foi possível criar tag $ref"
    [[ "$(gh api "$api" --jq '.object.sha')" == "${SHA_AUDITADO[$branch]}" ]] ||
      fail "Tag $ref falhou na verificação"
  fi
  echo "Arquivado: $ref"
done

# 2. Apagar apenas branches verificadas, nunca main/develop/v2.
for branch in "${LEGADAS[@]}"; do
  [[ -v EXISTE["$branch"] ]] || continue
  atual="$(gh api "repos/$REPO/git/ref/heads/$branch" --jq '.object.sha')" ||
    fail "Ref $branch não pôde ser relida antes da exclusão"
  [[ "$atual" == "${SHA_AUDITADO[$branch]}" ]] ||
    fail "Ref $branch mudou durante a execução; interrompendo"
  gh api --method DELETE "repos/$REPO/git/refs/heads/$branch" >/dev/null ||
    fail "Não foi possível excluir $branch"
  echo "Excluída: $branch"
done

# 3. Verificação do resultado final.
restantes="$(gh api --paginate "repos/$REPO/branches?per_page=100" --jq '.[].name' | sort)" ||
  fail "Não foi possível fazer verificação final"
esperado="$(printf 'develop/v2\nmain\n' | sort)"
[[ "$restantes" == "$esperado" ]] ||
  fail "Limpeza parcial: branches finais diferentes de main + develop/v2: $restantes"
echo "SUCESSO: somente main e develop/v2 permanecem; commits divergentes arquivados em tags."
