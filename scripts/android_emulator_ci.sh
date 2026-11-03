#!/usr/bin/env bash
# Executado DENTRO do android-emulator-runner, com AVD já iniciado.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
API_LOG="${API_LOG:-${RUNNER_TEMP:-/tmp}/smartparking-api.log}"
LOGCAT="${RUNNER_TEMP:-/tmp}/android-logcat.txt"
SCRIPT_LOG="${RUNNER_TEMP:-/tmp}/android-emulator-script.log"

exec > >(tee "$SCRIPT_LOG") 2>&1

finalizar() {
  local status=$?
  trap - EXIT
  adb shell logcat -d -t 1200 >"$LOGCAT" 2>/dev/null || true
  if (( status != 0 )); then
    printf '\n== Diagnóstico do dispositivo ==\n'
    grep -Ei 'maestro|AndroidRuntime|FATAL EXCEPTION|BindException|ReactNativeJS|Expo' \
      "$LOGCAT" | tail -n 120 || true
  fi
  exit "$status"
}
trap finalizar EXIT

printf '== AVD ==\n'
adb shell getprop ro.build.version.release
adb shell getprop ro.product.cpu.abi
adb shell getprop ro.build.version.sdk

bash "$RAIZ/scripts/android_native_config_ci.sh"

printf '\n== Instalação do APK release já compilado ==\n'
APK="$APP/android/app/build/outputs/apk/release/app-release.apk"
test -f "$APK"
adb install -r --no-streaming "$APK"
adb shell pm list packages | grep -q 'package:com.anonymous.smartparking'
printf '✔ com.anonymous.smartparking instalado.\n'

printf '\n== Jornada de UI no Android ==\n'
cd "$RAIZ"
adb logcat -c
# A porta é aberta no dispositivo; 7001 evita a faixa efêmera 32768–60999.
MAESTRO_DRIVER_STARTUP_TIMEOUT=120000 \
  maestro test --driver-host-port 7001 scripts/maestro/android-api-flow.yaml

printf '\n== Evidência independente nos logs da API ==\n'
verificar_api() {
  local rota="$1"
  if ! grep -q "$rota" "$API_LOG"; then
    printf '✘ Não encontrei 200 para: %s\n' "$rota"
    tail -n 120 "$API_LOG" || true
    return 1
  fi
  printf '✔ %s\n' "$rota"
}
verificar_api 'GET /api/estacionamentos HTTP/1.1" 200'
verificar_api 'POST /auth/login HTTP/1.1" 200'
verificar_api 'GET /auth/me HTTP/1.1" 200'
verificar_api 'GET /api/admin/dashboard HTTP/1.1" 200'
printf '✔ Home, login, restauração de sessão e dashboard protegido retornaram 200.\n'
printf '✔ VALIDAÇÃO ANDROID EMULATOR CONCLUÍDA.\n'
