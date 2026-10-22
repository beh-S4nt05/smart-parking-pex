#!/bin/bash
# (ACH-20, 22/10) APOSENTADO: a forma canônica de subir o dev é src/run-dev.sh
# (banco no Docker + venv + hot-reload, sem conflito de porta na 8000 e sem
# depender do cwd de quem chama). Este script só delega, na âncora certa.
exec "$(cd "$(dirname "$0")/.." && pwd)/run-dev.sh" "$@"
