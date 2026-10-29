#!/usr/bin/env bash
# Valida bundles Hermes e geração CNG sem deixar artefatos nativos no Git.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/smart-parking-expo.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

cd "$APP"
node "$RAIZ/scripts/check_expo_sdk.cjs"
node "$RAIZ/scripts/test_frontend_core.cjs"
node "$RAIZ/scripts/test_local_network.cjs"
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
  env -u EXPO_PUBLIC_API_URL -u EXPO_PUBLIC_API_URL_MOBILE \
    CI=1 npx expo prebuild --no-install --platform all
)
test -f "$TMP/prebuild/android/app/build.gradle"
test -f "$TMP/prebuild/ios/Podfile"

REDE="$TMP/prebuild/android/app/src/main/res/xml/smartparking_network_security.xml"
MANIFEST="$TMP/prebuild/android/app/src/main/AndroidManifest.xml"
PLIST="$TMP/prebuild/ios/SmartParking/Info.plist"
test -f "$REDE"
grep -q 'android:usesCleartextTraffic="false"' "$MANIFEST"
grep -q 'android:networkSecurityConfig="@xml/smartparking_network_security"' "$MANIFEST"
grep -q '<base-config cleartextTrafficPermitted="false"' "$REDE"
if grep -q '<domain-config' "$REDE"; then
  echo '✘ Build sem URL local não pode conter exceção de domínio HTTP.' >&2
  exit 1
fi
python3 - "$PLIST" <<'PY'
import plistlib
import sys
with open(sys.argv[1], "rb") as arquivo:
    plist = plistlib.load(arquivo)
ats = plist.get("NSAppTransportSecurity", {})
assert ats.get("NSAllowsArbitraryLoads") is not True, "ATS arbitrário aberto"
assert ats.get("NSAllowsLocalNetworking") is not True, "LAN aberta sem host explícito"
PY

# Segundo CNG: uma URL LAN cria exceção SOMENTE para esse IP; o restante do
# Android continua bloqueado e o iOS recebe rede local, nunca ATS arbitrário.
rm -rf "$TMP/prebuild/android" "$TMP/prebuild/ios" "$TMP/prebuild/.expo"
(
  cd "$TMP/prebuild"
  env -u EXPO_PUBLIC_API_URL EXPO_PUBLIC_API_URL_MOBILE=http://192.168.1.44:8000 \
    CI=1 npx expo prebuild --no-install --platform all
)
grep -q '<base-config cleartextTrafficPermitted="false"' "$REDE"
grep -q '<domain includeSubdomains="false">192.168.1.44</domain>' "$REDE"
test "$(grep -c '<domain ' "$REDE")" -eq 1
python3 - "$PLIST" <<'PY'
import plistlib
import sys
with open(sys.argv[1], "rb") as arquivo:
    plist = plistlib.load(arquivo)
ats = plist.get("NSAppTransportSecurity", {})
assert ats.get("NSAllowsArbitraryLoads") is not True, "ATS arbitrário aberto"
assert ats.get("NSAllowsLocalNetworking") is True, "exceção LAN ausente"
assert plist.get("NSLocalNetworkUsageDescription"), "texto da permissão LAN ausente"
PY

printf '✔ Expo nativo: export Web/Hermes e CNG fechado/LAN restrito aprovados.\n'
