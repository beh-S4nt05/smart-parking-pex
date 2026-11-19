#!/usr/bin/env bash
# Cria um timer systemd PERSISTENTE que encerra o piloto apos 14 dias.
# Execute no host Linux somente ao INICIAR o periodo de acesso publico:
# bash scripts/piloto_agendar_encerramento.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/piloto_encerrar.sh"
if [[ "$SCRIPT" =~ [[:space:]] ]]; then
  echo "Caminho do repositorio possui espacos: instale o piloto em uma pasta sem espacos." >&2
  exit 2
fi
if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemd indisponivel; nao e seguro deixar o piloto sem prazo automatico." >&2
  exit 2
fi
if [ ! -f "$SCRIPT" ]; then
  echo "Falta script de encerramento." >&2
  exit 2
fi
FIM="$(date -d '+14 days' '+%Y-%m-%d %H:%M:%S')" || exit 2
echo "Programando interrupcao PUBLICA para $FIM (fuso local do Linux)."
echo "Exige sudo; os arquivos ficam em /etc/systemd/system/ e sobrevivem a reinicios."
cat <<EOF | sudo tee /etc/systemd/system/smartparking-piloto-expira.service >/dev/null
[Unit]
Description=Desligar API publica Smart Parking piloto (limite 14 dias)
After=network-online.target docker.service tailscaled.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash $SCRIPT
TimeoutStartSec=180
Restart=on-failure
RestartSec=60
EOF
cat <<EOF | sudo tee /etc/systemd/system/smartparking-piloto-expira.timer >/dev/null
[Unit]
Description=Expiracao permanente do piloto Smart Parking

[Timer]
OnCalendar=$FIM
Persistent=true
AccuracySec=1min
Unit=smartparking-piloto-expira.service

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now smartparking-piloto-expira.timer
echo
echo "Confirme programacao e horario de execucao:"
systemctl list-timers smartparking-piloto-expira.timer --no-pager
echo "A pagina estatica do Cloudflare Pages continua precisando despublicacao manual."
