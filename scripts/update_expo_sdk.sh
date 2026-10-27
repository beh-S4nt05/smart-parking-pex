#!/usr/bin/env bash
# Atualiza pelo fluxo oficial do Expo e restaura pins exatos após o --fix.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
cd "$APP"

ATUAL="$(node -p "require('./package.json').dependencies.expo")"
LATEST="$(npm view expo version)"
printf 'Expo: instalado no manifest=%s · canal latest=%s\n' "$ATUAL" "$LATEST"

if [[ "$ATUAL" != "$LATEST" ]]; then
  # O CLI antigo instala o novo core; o --fix seguinte já usa o CLI atualizado.
  npx expo install "expo@$LATEST" -- --save-exact
fi

# Alinha React Native e módulos nativos à tabela do SDK instalado.
npx expo install --fix -- --save-exact

# O --fix pode gravar ~ nos pacotes recomendados. Reinstalar as versões já
# escolhidas pelo SDK com specs explícitas mantém o requisito de pins exatos.
mapfile -t REPIN < <(node "$RAIZ/scripts/check_expo_sdk.cjs" repin)
if ((${#REPIN[@]})); then
  printf 'Reaplicando pins exatos: %s\n' "${REPIN[*]}"
  npx expo install "${REPIN[@]}" -- --save-exact
fi

# Os manifests são executáveis no histórico do projeto; não incluir mudança de
# modo incidental causada pelas escritas do npm/Expo no diff da atualização.
chmod 755 package.json app.json

npx expo install --check
node "$RAIZ/scripts/check_expo_sdk.cjs"
printf 'Atualização Expo concluída. Rode npm run doctor e npm run check-native.\n'
