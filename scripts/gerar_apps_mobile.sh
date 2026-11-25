#!/usr/bin/env bash
# Build EAS: APK Android e TestFlight iOS. Executar na conta Expo do projeto.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
PLATAFORMA="${1:-}"

case "$PLATAFORMA" in
  android|ios|ambos) ;;
  *)
    echo "Uso: EXPO_PUBLIC_API_URL_MOBILE=https://API_PUBLICA bash scripts/gerar_apps_mobile.sh android|ios|ambos" >&2
    exit 2
    ;;
esac

if [[ -z "${EXPO_PUBLIC_API_URL_MOBILE:-}" ]]; then
  echo "FALHA: configure EXPO_PUBLIC_API_URL_MOBILE como URL HTTPS REAL da API, acessível ao público." >&2
  exit 2
fi

node "$RAIZ/scripts/mobile_release_preflight.cjs" --check-api
cd "$APP"
npm ci --no-audit --no-fund

if ! npx --yes eas-cli@latest whoami; then
  echo "Autentique-se no Expo/EAS: npx eas-cli@latest login" >&2
  exit 2
fi
if ! node "$RAIZ/scripts/mobile_release_preflight.cjs" --require-eas-project; then
  echo "Primeiro build: vincule o projeto verdadeiro no Expo/EAS."
  npx --yes eas-cli@latest init
fi
node "$RAIZ/scripts/mobile_release_preflight.cjs" --require-eas-project --check-api

configurar_url_eas() {
  local ambiente="$1"
  npx --yes eas-cli@latest env:set \
    --name EXPO_PUBLIC_API_URL_MOBILE \
    --value "$EXPO_PUBLIC_API_URL_MOBILE" \
    --environment "$ambiente" \
    --visibility plaintext
}

if [[ "$PLATAFORMA" == "android" || "$PLATAFORMA" == "ambos" ]]; then
  configurar_url_eas preview
  echo "Compilando APK Android para aparelho físico via EAS..."
  npx --yes eas-cli@latest build --platform android --profile preview --wait
  echo "O link real do APK está no painel Expo EAS do build concluído."
fi

if [[ "$PLATAFORMA" == "ios" || "$PLATAFORMA" == "ambos" ]]; then
  configurar_url_eas production
  echo "Compilando iOS para distribuição TestFlight."
  echo "Requer Apple Developer, assinatura e App Store Connect já autorizados."
  npx --yes eas-cli@latest build --platform ios --profile production --auto-submit --wait
  echo "Confira o processamento e distribuição no App Store Connect / TestFlight."
fi
