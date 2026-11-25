#!/usr/bin/env node
"use strict";
/**
 * Portão de publicação mobile. Não imprime segredos nem habilita fallback localhost.
 * Uso: EXPO_PUBLIC_API_URL_MOBILE=https://api.exemplo.com node scripts/mobile_release_preflight.cjs --check-api
 * CI:  node scripts/mobile_release_preflight.cjs --self-test
 */
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const raiz = path.resolve(__dirname, "..");
const app = path.join(raiz, "src/frontend/smart-parking");
const args = new Set(process.argv.slice(2));

function validarURLPublica(valor) {
  if (typeof valor !== "string" || !valor.trim()) {
    throw new Error("EXPO_PUBLIC_API_URL_MOBILE ausente. Configure a URL HTTPS PUBLICA da API FastAPI antes do build.");
  }
  let url;
  try { url = new URL(valor.trim()); }
  catch { throw new Error("EXPO_PUBLIC_API_URL_MOBILE: URL invalida."); }

  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  const partes = host.split(".");
  const ipv4 = partes.length === 4 && partes.every(p => /^(0|[1-9]\d{0,2})$/.test(p) && Number(p) <= 255);
  const priv = ipv4 && (
    Number(partes[0]) === 10 ||
    Number(partes[0]) === 127 ||
    (Number(partes[0]) === 172 && Number(partes[1]) >= 16 && Number(partes[1]) <= 31) ||
    (Number(partes[0]) === 192 && Number(partes[1]) === 168) ||
    (Number(partes[0]) === 169 && Number(partes[1]) === 254)
  );
  if (url.protocol !== "https:" || url.username || url.password ||
      url.search || url.hash || (url.pathname !== "/" && url.pathname !== "") ||
      ["localhost", "0.0.0.0", "::1"].includes(host) ||
      host.endsWith(".local") || host.endsWith(".lan") || priv) {
    throw new Error("API mobile deve ser HTTPS publico, com host valido, sem credenciais, caminho ou parametros (nunca localhost/LAN).");
  }
  if (!url.hostname.includes(".") && !ipv4) {
    throw new Error("API mobile deve ter um nome DNS publico acessivel externamente.");
  }
  return url.origin;
}

function configurarExpo() {
  const base = JSON.parse(fs.readFileSync(path.join(app, "app.json"), "utf8")).expo;
  const resultado = require(path.join(app, "app.config.js"))({ config: base });
  const eas = JSON.parse(fs.readFileSync(path.join(app, "eas.json"), "utf8"));
  assert.equal(resultado.android.package, "com.behs4nt05.smartparking");
  assert.equal(resultado.ios.bundleIdentifier, "com.behs4nt05.smartparking");
  assert.equal(eas.build.preview.android.buildType, "apk");
  assert.equal(eas.build.preview.environment, "preview");
  assert.equal(eas.build.production.environment, "production");
  assert.equal(eas.build.production.distribution, "store");
  assert.equal(eas.build.production.ios.simulator, false);
  return resultado;
}

async function verificarHealth(url) {
  let res;
  try {
    res = await fetch(url + "/health", {
      method: "GET", redirect: "error", signal: AbortSignal.timeout(10000),
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new Error("Nao foi possivel acessar GET /health da API publica por HTTPS. Revise DNS, Funnel e backend online.");
  }
  if (!res.ok) throw new Error("API publica /health retornou HTTP " + res.status + ", esperado 200.");
  const json = await res.json().catch(() => null);
  if (!json || json.status !== "ok") {
    throw new Error("API /health respondeu, mas nao retornou JSON com status=ok.");
  }
  console.log("OK: API real respondeu /health por HTTPS.");
}

async function main() {
  if (args.has("--self-test")) {
    assert.equal(validarURLPublica("https://api.exemplo.com"), "https://api.exemplo.com");
    assert.equal(validarURLPublica("https://smartparking.tailnet.ts.net/"), "https://smartparking.tailnet.ts.net");
    for (const v of ["", "http://api.exemplo.com", "http://localhost:8000",
      "https://localhost:8000", "https://192.168.0.12", "https://api.exemplo.com/path",
      "https://user:senha@api.exemplo.com", "ftp://example.com"]) {
      assert.throws(() => validarURLPublica(v));
    }
    configurarExpo();
    console.log("OK: preflight mobile (URL, Expo, EAS Android APK, iOS TestFlight).");
    return;
  }

  const url = validarURLPublica(process.env.EXPO_PUBLIC_API_URL_MOBILE);
  const expo = configurarExpo();
  if (args.has("--require-eas-project")) {
    const id = expo.extra?.eas?.projectId;
    if (!/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(String(id || ""))) {
      throw new Error("Projeto Expo nao vinculado ao EAS: rode 'npx eas-cli@latest init' e inclua extra.eas.projectId, ou defina EXPO_EAS_PROJECT_ID real.");
    }
  }
  console.log("OK: build mobile aponta para " + url + ".");
  console.log("OK: Android gera APK; iOS production gera IPA para TestFlight.");
  if (args.has("--check-api")) await verificarHealth(url);
}

main().catch(e => {
  console.error("FALHA preflight mobile: " + e.message);
  process.exitCode = 1;
});
