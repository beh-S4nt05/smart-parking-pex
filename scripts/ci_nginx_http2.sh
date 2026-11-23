#!/usr/bin/env bash
# Teste integrado do Nginx HTTP origin e template HTTPS/h2, sem banco do projeto.
# Executado em runner GitHub com Docker, OpenSSL e curl.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NET="smartparking-nginx-http2-ci-${GITHUB_RUN_ID:-local}"
CERTS="$(mktemp -d)"
BACKEND="smartparking-http2-backend-${GITHUB_RUN_ID:-local}"
NGINX="smartparking-http2-proxy-${GITHUB_RUN_ID:-local}"
cleanup() {
  docker rm -f "$NGINX" "$BACKEND" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$CERTS"
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
docker run -d --rm --name "$BACKEND" --network "$NET" \
  --network-alias backend python:3.12-alpine \
  python -m http.server 8000 --bind 0.0.0.0 >/dev/null

docker build -q -t smartparking-nginx:http2-ci src/nginx >/dev/null

echo "Validando configuração HTTP/1.1 do Nginx ativo..."
docker run --rm --network "$NET" smartparking-nginx:http2-ci nginx -t

echo "Testando HTTPS opt-in com certificado autoassinado descartável..."
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -keyout "$CERTS/privkey.pem" -out "$CERTS/fullchain.pem" \
  -subj "/CN=piloto.example.test" >/dev/null 2>&1

docker run --rm --network "$NET" \
  -v "$ROOT/src/nginx/https.conf.example:/etc/nginx/conf.d/https.conf:ro" \
  -v "$CERTS:/etc/nginx/ssl:ro" \
  smartparking-nginx:http2-ci nginx -t

docker run -d --rm --name "$NGINX" --network "$NET" \
  -p "127.0.0.1:18080:80" -p "127.0.0.1:18443:443" \
  -v "$ROOT/src/nginx/https.conf.example:/etc/nginx/conf.d/https.conf:ro" \
  -v "$CERTS:/etc/nginx/ssl:ro" \
  smartparking-nginx:http2-ci >/dev/null

for _ in $(seq 1 25); do
  if curl -fsS --http1.1 --max-time 2 http://127.0.0.1:18080/ >/dev/null; then break; fi
  sleep 1
done

HTTP1="$(curl -fsS --http1.1 -o /dev/null -w '%{http_version}:%{http_code}' http://127.0.0.1:18080/)"
[ "$HTTP1" = "1.1:200" ] || { echo "HTTP local inesperado: $HTTP1"; exit 1; }
echo "OK: Nginx HTTP origin 1.1 -> backend de teste (200)."

# Na porta 443 do template, curl deve negociar HTTP/2 com ALPN.
# --resolve evita depender de DNS externo; -k só para cert EFEMERO de CI.
HTTP2="$(curl -fsS -k --http2 -o /dev/null -w '%{http_version}:%{http_code}' \
  --resolve 'piloto.example.test:18443:127.0.0.1' \
  --noproxy '*' \
  https://piloto.example.test:18443/)"
[ "$HTTP2" = "2:200" ] || { echo "HTTPS/ALPN inesperado: $HTTP2"; exit 1; }
echo "OK: TLS com HTTP/2 via ALPN -> backend de teste (200)."
