#!/usr/bin/env bash
# Executado DENTRO do android-emulator-runner, com AVD já iniciado.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
API_LOG="${API_LOG:-${RUNNER_TEMP:-/tmp}/smartparking-api.log}"
LOGCAT="${RUNNER_TEMP:-/tmp}/android-logcat.txt"

trap 'adb shell logcat -d -t 800 >"$LOGCAT" 2>/dev/null || true' EXIT

printf '== AVD ==\n'
adb shell getprop ro.build.version.release
adb shell getprop ro.product.cpu.abi
adb shell getprop ro.build.version.sdk

printf '\n== Política cleartext materializada no projeto usado no build ==\n'
MANIFEST="$APP/android/app/src/main/AndroidManifest.xml"
REDE="$APP/android/app/src/main/res/xml/smartparking_network_security.xml"
test -f "$MANIFEST"
test -f "$REDE"
grep -q 'android:usesCleartextTraffic="false"' "$MANIFEST"
grep -q 'android:networkSecurityConfig="@xml/smartparking_network_security"' "$MANIFEST"
grep -q '<base-config cleartextTrafficPermitted="false"' "$REDE"
grep -q '<domain includeSubdomains="false">10.0.2.2</domain>' "$REDE"
test "$(grep -c '<domain ' "$REDE")" -eq 1
printf '✔ somente 10.0.2.2 tem exceção; base e demais hosts ficam bloqueados.\n'

printf '\n== Build e instalação do APK release no AVD ==\n'
cd "$APP/android"
./gradlew installRelease \
  -PreactNativeArchitectures=x86_64 \
  --no-daemon \
  --stacktrace
adb shell pm list packages | grep -q 'package:com.anonymous.smartparking'
printf '✔ com.anonymous.smartparking instalado.\n'

printf '\n== Jornada de UI no Android ==\n'
cd "$RAIZ"
maestro test scripts/maestro/android-api-flow.yaml

printf '\n== Evidência independente nos logs da API ==\n'
grep -q 'GET /api/estacionamentos HTTP/1.1" 200' "$API_LOG"
grep -q 'POST /auth/login HTTP/1.1" 200' "$API_LOG"
grep -q 'GET /auth/me HTTP/1.1" 200' "$API_LOG"
grep -q 'GET /api/admin/dashboard HTTP/1.1" 200' "$API_LOG"
printf '✔ Home, login, restauração de sessão e dashboard protegido retornaram 200.\n'
printf '✔ VALIDAÇÃO ANDROID EMULATOR CONCLUÍDA.\n'
