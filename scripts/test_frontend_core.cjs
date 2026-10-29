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

const arquivoApi = path.join(
  __dirname,
  "../src/frontend/smart-parking/src/services/apiBaseUrl.ts",
);
const jsApi = ts.transpileModule(fs.readFileSync(arquivoApi, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
  fileName: arquivoApi,
}).outputText;
const moduloApi = { exports: {} };
new Function("require", "module", "exports", jsApi)(
  require,
  moduloApi,
  moduloApi.exports,
);
const { limparUrlManual, resolverApiURLBase, validarUrlApi } = moduloApi.exports;

test("URL manual aceita HTTPS e HTTP somente em loopback/LAN", () => {
  assert.equal(
    validarUrlApi("https://api.parking.example.com/"),
    "https://api.parking.example.com",
  );
  for (const url of [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://10.0.2.2:8000",
    "http://172.18.0.2:8000",
    "http://192.168.1.14:8000",
    "http://169.254.0.21:8000",
    "http://servidor.local:8000",
  ]) {
    assert.equal(validarUrlApi(url), url);
  }
});

test("URL manual rejeita HTTP público, spoof de IP e protocolos arbitrários", () => {
  for (const url of [
    "http://api.parking.example.com",
    "http://192.168.1.14.evil.example:8000",
    "http://172.32.0.1:8000",
    "http://11.0.0.1:8000",
  ]) {
    assert.throws(() => validarUrlApi(url), /HTTP público/);
  }
  assert.throws(() => validarUrlApi("file:///tmp/api"), /protocolo/);
  assert.throws(() => validarUrlApi("não é uma URL"), /inválida/);
});

test("override mobile mantém prioridade e porta do Metro gera aviso", () => {
  let aviso = "";
  const url = resolverApiURLBase({
    ehWeb: false,
    envMobile: "http://192.168.1.20:8081/",
    envGlobal: "https://api.parking.example.com",
    ehAndroid: true,
    warn: (mensagem) => {
      aviso = mensagem;
    },
  });
  assert.equal(url, "http://192.168.1.20:8081");
  assert.match(aviso, /API roda na 8000/);
  assert.equal(limparUrlManual("", "TESTE"), "");
});

test("Expo Go usa o IP publicado pelo Metro sem congelar localhost", () => {
  assert.equal(
    resolverApiURLBase({
      ehWeb: false,
      ehAndroid: true,
      hostUri: "192.168.1.25:8081",
    }),
    "http://192.168.1.25:8000",
  );
  assert.equal(
    resolverApiURLBase({ ehWeb: false, ehAndroid: true, hostUri: "localhost:8081" }),
    "http://10.0.2.2:8000",
  );
  assert.equal(
    resolverApiURLBase({ ehWeb: false, ehAndroid: false }),
    "http://localhost:8000",
  );
});

test("Web mantém same-origin em produção e host atual em desenvolvimento", () => {
  assert.equal(
    resolverApiURLBase({
      ehWeb: true,
      location: { protocol: "https:", hostname: "parking.example.com", port: "" },
    }),
    "https://parking.example.com",
  );
  assert.equal(
    resolverApiURLBase({
      ehWeb: true,
      location: { protocol: "http:", hostname: "192.168.1.30", port: "8081" },
    }),
    "http://192.168.1.30:8000",
  );
  assert.equal(
    resolverApiURLBase({
      ehWeb: true,
      location: { protocol: "http:", hostname: "localhost", port: "8081" },
    }),
    "http://localhost:8000",
  );
});

console.log(`Frontend core: ${total} grupos OK`);
