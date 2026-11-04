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
  local temp="${RUNNER_TEMP:-/tmp}"
  trap - EXIT
  adb shell logcat -d -t 4000 >"$LOGCAT" 2>/dev/null || true
  if (( status != 0 )); then
    printf '\n== Diagnóstico do dispositivo ==\n'
    # O Maestro já terminou neste ponto: agora uiautomator/screencap não
    # concorrem com o driver. A hierarquia explícita evita depender do formato
    # de evidências de uma versão específica do Maestro.
    adb shell dumpsys activity activities >"$temp/android-activities.txt" 2>/dev/null || true
    adb shell dumpsys window windows >"$temp/android-windows.txt" 2>/dev/null || true
    adb shell dumpsys cpuinfo >"$temp/android-cpuinfo.txt" 2>/dev/null || true
    adb shell ps -A >"$temp/android-processes.txt" 2>/dev/null || true
    adb shell uiautomator dump /sdcard/smartparking-window.xml >/dev/null 2>&1 || true
    adb pull /sdcard/smartparking-window.xml "$temp/smartparking-window.xml" >/dev/null 2>&1 || true
    adb exec-out screencap -p >"/tmp/smartparking-failure-android.png" 2>/dev/null || true

    printf '\n== CPU e processo/Activity ==\n'
    head -n 50 "$temp/android-cpuinfo.txt" 2>/dev/null || true
    grep -E 'mResumedActivity|topResumedActivity|Application Error|AppErrorDialog|aerr_|com\.anonymous\.smartparking' \
      "$temp/android-activities.txt" "$temp/android-windows.txt" 2>/dev/null | tail -n 120 || true
    grep -E 'com\.anonymous\.smartparking|com\.android\.systemui|com\.android\.phone' \
      "$temp/android-processes.txt" 2>/dev/null || true

    printf '\n== App e estabilidade no logcat ==\n'
    grep -Ei 'maestro|AndroidRuntime|FATAL EXCEPTION|ANR in|ReactNativeJS|OkHttp|10\.0\.2\.2|cleartext|NetworkSecurity|lowmemory|out of memory|watchdog|SystemServer|System UI' \
      "$LOGCAT" | tail -n 300 || true

    printf '\n== Hierarquia explícita do AVD ==\n'
    if [[ -s "$temp/smartparking-window.xml" ]]; then
      grep -Eo '(text|content-desc|resource-id|bounds)="[^"]*"' \
        "$temp/smartparking-window.xml" | tail -n 240 || true
    else
      printf 'Nenhuma hierarquia XML foi produzida.\n'
    fi

    # Sem isto, uma falha de UI escondia se a API foi chamada e o que estava
    # realmente visível no aparelho. Não contém headers nem tokens.
    printf '\n== Últimas linhas da API ==\n'
    tail -n 160 "$API_LOG" || true
    printf '\n== Evidências do Maestro ==\n'
    find "$HOME/.maestro/tests" -maxdepth 7 -type f -printf '%p (%s bytes)\n' 2>/dev/null | tail -n 100 || true
    while IFS= read -r -d '' hierarquia; do
      printf '\n== Textos e IDs de %s ==\n' "$hierarquia"
      python3 - "$hierarquia" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as arquivo:
    raiz = json.load(arquivo)

def visitar(no):
    atributos = no.get("attributes", {})
    visiveis = {
        chave: atributos[chave]
        for chave in ("text", "content-desc", "resource-id", "bounds")
        if chave in atributos
    }
    if visiveis:
        print(json.dumps(visiveis, ensure_ascii=False))
    for filho in no.get("children", []):
        visitar(filho)

visitar(raiz)
PY
    done < <(find "$HOME/.maestro/tests" -type f -path '*/screen-hierarchy/*.json' -print0 2>/dev/null)
  fi
  exit "$status"
}
trap finalizar EXIT

printf '== AVD ==\n'
adb shell getprop ro.build.version.release
adb shell getprop ro.product.cpu.abi
adb shell getprop ro.build.version.sdk

printf '\n== Estado do AVD antes da instalação ==\n'
# PSI (/proc/pressure/*) não é legível pelo shell em todos os Androids; usar
# somente diagnósticos que funcionam no AVD, sem transformar ausência em erro.
adb shell getprop sys.boot_completed
adb shell dumpsys activity activities | grep -m 1 'topResumedActivity' || true
adb shell dumpsys cpuinfo | head -n 30 || true

bash "$RAIZ/scripts/android_native_config_ci.sh"

printf '\n== Instalação do APK release já compilado ==\n'
APK="$APP/android/app/build/outputs/apk/release/app-release.apk"
test -f "$APK"
adb install -r "$APK"
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
