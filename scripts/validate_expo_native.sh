#!/usr/bin/env bash
# Valida bundles Hermes e geração CNG sem deixar artefatos nativos no Git.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/smart-parking-expo.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

cd "$APP"
node "$RAIZ/scripts/check_expo_sdk.cjs"
npx expo install --check
npx tsc --noEmit

# Android/iOS geram bytecode Hermes; Web permanece no mesmo portão para evitar
# que uma atualização nativa regreda a plataforma já funcional.
npx expo export --platform all --clear --output-dir "$TMP/export"
test -f "$TMP/export/index.html"
find "$TMP/export/_expo/static/js/android" -name '*.hbc' -print -quit | grep -q .
find "$TMP/export/_expo/static/js/ios" -name '*.hbc' -print -quit | grep -q .

# O prebuild roda numa cópia e reutiliza somente node_modules. Assim ele valida
# plugins, ícones e configuração nativa sem adicionar android/ios ao repositório.
mkdir -p "$TMP/prebuild"
tar \
  --exclude=node_modules --exclude=.expo --exclude=dist \
  --exclude=android --exclude=ios --exclude=.env --exclude='.env.*' \
  -cf - . | tar -xf - -C "$TMP/prebuild"
ln -s "$APP/node_modules" "$TMP/prebuild/node_modules"
(
  cd "$TMP/prebuild"
  CI=1 npx expo prebuild --no-install --platform all
)
test -f "$TMP/prebuild/android/app/build.gradle"
test -f "$TMP/prebuild/ios/Podfile"

printf '✔ Expo nativo: export Android/iOS/Web e prebuild Android/iOS aprovados.\n'
