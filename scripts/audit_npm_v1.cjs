#!/usr/bin/env node
"use strict";

/**
 * Auditoria da V1: o npm audit continua executando no CI, porém uma única
 * vulnerabilidade upstream SEM VERSÃO CORRIGIDA é acompanhada com exceção
 * temporária e restrita, sem ocultar novas vulnerabilidades.
 *
 * GHSA-fc5q-39xc-vjpf / CVE-2026-112366 (picomatch <= 4.0.7).
 * 39 pacotes são a propagação de UMA causa no relatório de 17/11/2026.
 * Não usar npm audit fix --force: o npm sugere downgrade do SDK 58.
 */
const { spawnSync } = require("node:child_process");

const ADVISORY_ID = "GHSA-fc5q-39xc-vjpf";
const ADVISORY_URL = "https://github.com/advisories/" + ADVISORY_ID;
const EXPIRY_UTC = "2026-12-18T00:00:00.000Z";
const MAX_IMPACTED_PACKAGES = 39;

function verifyReport(report, now = new Date()) {
  if (!report || typeof report !== "object" || report.error) {
    throw new Error("npm audit retornou resposta inválida ou erro: " + JSON.stringify(report?.error));
  }
  const entries = report.vulnerabilities;
  if (!entries || typeof entries !== "object" || Array.isArray(entries)) {
    throw new Error("npm audit sem campo vulnerabilities verificável");
  }
  const names = Object.keys(entries);
  if (names.length === 0) {
    return { clean: true, total: 0 };
  }
  if (now.getTime() >= Date.parse(EXPIRY_UTC)) {
    throw new Error(
      "Exceção " + ADVISORY_ID + " expirada em " + EXPIRY_UTC +
      ". Verificar release de picomatch e renovar apenas após revisão de segurança.",
    );
  }
  if (names.length > MAX_IMPACTED_PACKAGES) {
    throw new Error(
      "Aumento da superfície afetada: " + names.length + " pacotes (limite aprovado: " +
      MAX_IMPACTED_PACKAGES + ").",
    );
  }
  if (!Object.prototype.hasOwnProperty.call(entries, "picomatch")) {
    throw new Error("Vulnerabilidade não relacionada à exceção única de picomatch");
  }

  // O grafo do npm audit tem ciclos legítimos (metro ⇄ metro-config ⇄
  // metro-transform-worker). Não tratá-los como erro: validar TODAS as
  // causas diretas e exigir caminho de cada pacote até o advisory raiz.
  for (const name of names) {
    const item = entries[name];
    if (!item || !Array.isArray(item.via) || item.via.length === 0) {
      throw new Error("Causa não comprovada para vulnerabilidade em " + name);
    }
    if (item.severity !== "high") {
      throw new Error("Severidade fora do escopo da exceção em " + name + ": " + item.severity);
    }
    for (const via of item.via) {
      if (typeof via === "string") {
        if (!Object.prototype.hasOwnProperty.call(entries, via)) {
          throw new Error("Dependência vulnerável desconhecida: " + name + " → " + via);
        }
      } else if (
        !via || typeof via !== "object" ||
        name !== "picomatch" ||
        via.name !== "picomatch" ||
        via.url !== ADVISORY_URL ||
        via.severity !== "high"
      ) {
        throw new Error("Novo advisory sem exceção explícita em " + name + ": " + JSON.stringify(via));
      }
    }
  }

  function reachesAdvisory(name, seen = new Set()) {
    if (name === "picomatch") return true;
    if (seen.has(name)) return false;
    const next = new Set(seen);
    next.add(name);
    return entries[name].via.some(
      (via) => typeof via === "string" && reachesAdvisory(via, next),
    );
  }
  for (const name of names) {
    if (!reachesAdvisory(name)) {
      throw new Error("Pacote sem cadeia até a exceção picomatch: " + name);
    }
  }

  const meta = report.metadata?.vulnerabilities;
  if (
    !meta || meta.total !== names.length || meta.critical !== 0 ||
    meta.moderate !== 0 || meta.low !== 0 || meta.info !== 0 ||
    meta.high !== names.length
  ) {
    throw new Error("Resumo npm audit divergente; investigar antes de aprovar: " + JSON.stringify(meta));
  }
  return { clean: false, total: names.length };
}

function test() {
  const known = {
    vulnerabilities: {
      picomatch: {
        severity: "high",
        via: [{ name: "picomatch", url: ADVISORY_URL, severity: "high" }],
      },
      "expo": { severity: "high", via: ["picomatch"] },
    },
    metadata: { vulnerabilities: { total: 2, high: 2, critical: 0, moderate: 0, low: 0, info: 0 } },
  };
  const assert = require("node:assert/strict");
  assert.deepEqual(verifyReport({ vulnerabilities: {} }), { clean: true, total: 0 });
  assert.deepEqual(verifyReport(known, new Date("2026-11-17T20:00:00Z")), { clean: false, total: 2 });
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const unknown = clone(known);
  unknown.vulnerabilities.expo.via.push({ name: "expo", severity: "high", url: "https://github.com/advisories/GHSA-other" });
  assert.throws(() => verifyReport(unknown, new Date("2026-11-17T20:00:00Z")), /Novo advisory/);
  assert.throws(() => verifyReport(known, new Date("2026-12-18T00:00:00Z")), /expirada/);
  const extra = clone(known);
  extra.vulnerabilities.other = { severity: "moderate", via: ["picomatch"] };
  extra.metadata.vulnerabilities.total = 3;
  extra.metadata.vulnerabilities.moderate = 1;
  assert.throws(() => verifyReport(extra, new Date("2026-11-17T20:00:00Z")), /Severidade/);
  const noRoot = clone(known);
  delete noRoot.vulnerabilities.picomatch;
  assert.throws(() => verifyReport(noRoot, new Date("2026-11-17T20:00:00Z")), /não relacionada/);
  console.log("✔ Política de auditoria: 6 cenários aprovados");
}

function main() {
  if (process.argv.includes("--self-test")) return test();
  const result = spawnSync("npm", ["audit", "--json", "--audit-level=moderate"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
    timeout: 150000,
    windowsHide: true,
  });
  if (result.error || (result.status !== 0 && result.status !== 1)) {
    throw new Error("Falha de execução npm audit: " + (result.error?.message || result.stderr || result.status));
  }
  let report;
  try {
    report = JSON.parse(result.stdout);
  } catch (e) {
    throw new Error("Saída npm audit não é JSON: " + String(e) + "; " + String(result.stderr).slice(0,800));
  }
  const check = verifyReport(report);
  if (check.clean) {
    console.log("✔ npm audit: nenhuma vulnerabilidade identificada");
    return;
  }
  const message =
    "npm audit detectou " + check.total + " pacotes afetados exclusivamente por " +
    ADVISORY_ID + " (picomatch, sem release corrigido até a verificação). " +
    "Exceção temporária até " + EXPIRY_UTC + "; qualquer novo advisory faz o CI falhar.";
  console.warn(message);
  console.log("::warning title=V1 npm audit — exceção temporária::" + message);
  console.log("Referência: " + ADVISORY_URL);
}

try {
  main();
} catch (e) {
  console.error("✖ Segurança — CI bloqueado: " + e.message);
  process.exitCode = 1;
}

module.exports = { verifyReport };
