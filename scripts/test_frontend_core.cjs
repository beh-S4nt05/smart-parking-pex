#!/usr/bin/env node
/* Testes das decisões puras de autenticação, sem novo pacote/npm install. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require(path.join(
  __dirname,
  "../src/frontend/smart-parking/node_modules/typescript",
));

const arquivo = path.join(
  __dirname,
  "../src/frontend/smart-parking/src/services/authFlow.ts",
);
const js = ts.transpileModule(fs.readFileSync(arquivo, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
  fileName: arquivo,
}).outputText;
const modulo = { exports: {} };
new Function("require", "module", "exports", js)(require, modulo, modulo.exports);
const { destinoAposLogin, erroRevogaSessao } = modulo.exports;

let total = 0;
function test(nome, fn) {
  fn();
  total += 1;
  console.log(`✔ ${nome}`);
}

test("rede/timeout/429/500 não revogam a sessão cacheada", () => {
  for (const erro of [
    new Error("Network Error"),
    { code: "ECONNABORTED" },
    { response: { status: 429 } },
    { response: { status: 500 } },
    { response: { status: 503 } },
  ]) {
    assert.equal(erroRevogaSessao(erro), false);
  }
});

test("401 e 403 revogam depois da tentativa de refresh", () => {
  assert.equal(erroRevogaSessao({ response: { status: 401 } }), true);
  assert.equal(erroRevogaSessao({ response: { status: 403 } }), true);
});

test("login mantém destino interno permitido e token do QR", () => {
  assert.equal(
    destinoAposLogin("/simulador?sessao=abc123", "admin"),
    "/simulador?sessao=abc123",
  );
  assert.equal(destinoAposLogin("/reservas", "usuario"), "/reservas");
});

test("login aplica destino por papel quando next é ausente ou proibido", () => {
  assert.equal(destinoAposLogin(undefined, "admin"), "/dashboard");
  assert.equal(destinoAposLogin(undefined, "usuario"), "/");
  assert.equal(destinoAposLogin("/dashboard", "usuario"), "/");
  assert.equal(destinoAposLogin("/simulador?sessao=abc", "gestor"), "/dashboard");
});

test("next externo ou que gere loop nunca é usado", () => {
  for (const destino of [
    "https://evil.example/phish",
    "//evil.example/phish",
    "/login",
    "/cadastro",
    "/\\evil.example",
  ]) {
    assert.equal(destinoAposLogin(destino, "usuario"), "/");
  }
});

console.log(`Frontend core: ${total} grupos OK`);
