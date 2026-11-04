#!/usr/bin/env bash
# Confere a política de rede no projeto nativo que origina o APK de QA.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$RAIZ/src/frontend/smart-parking"
MANIFEST="$APP/android/app/src/main/AndroidManifest.xml"
REDE="$APP/android/app/src/main/res/xml/smartparking_network_security.xml"

printf '== Política cleartext materializada no projeto usado no build ==\n'
test -f "$MANIFEST"
test -f "$REDE"
grep -q 'android:usesCleartextTraffic="false"' "$MANIFEST"
grep -q 'android:networkSecurityConfig="@xml/smartparking_network_security"' "$MANIFEST"
grep -q '<base-config cleartextTrafficPermitted="false"' "$REDE"
grep -q '<domain includeSubdomains="false">10.0.2.2</domain>' "$REDE"
test "$(grep -c '<domain ' "$REDE")" -eq 1
printf '✔ somente 10.0.2.2 tem exceção; base e demais hosts ficam bloqueados.\n'
