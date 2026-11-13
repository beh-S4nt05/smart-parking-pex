#!/usr/bin/env node
/**
 * Guard da camada de estilos. Existir "tokens.ts" ou "recipes.ts" nao prova
 * nada: uma auditoria anterior encontrou tokens.ts sem nenhum importador e
 * 19 arquivos com imports mortos. Este script verifica o uso REAL.
 *
 *   1. theme.ts consome tokens.ts (nao e arquivo morto);
 *   2. os valores compartilhados entre tokens.ts e o :root do CSS batem;
 *   3. colors ainda expoe todas as chaves usadas pelas telas;
 *   4. nenhum .tsx importa uma receita que nao usa;
 *   5. nenhuma receita e composta com outra (sem cn/conflito de utilidades).
 *
 * Uso: node scripts/check_design_tokens.cjs   (exit 1 = divergencia)
 */
const fs = require("node:fs");
const path = require("node:path");

const raiz = path.resolve(__dirname, "..");
const front = path.join(raiz, "src/frontend/smart-parking");
const problemas = [];
const ler = (p) => fs.readFileSync(path.join(front, p), "utf8");

const tokens = ler("src/styles/tokens.ts");
const recipes = ler("src/styles/recipes.ts");
const css = ler("assets/Styles/global.css");
const theme = ler("src/theme.ts");

// 1. consumo real -----------------------------------------------------------
if (!/from ["'].*styles\/tokens["']/.test(theme)) {
  problemas.push("theme.ts nao importa styles/tokens.ts");
}
if (!/colors\s*=\s*tokens\.cor/.test(theme)) {
  problemas.push("theme.ts nao deriva colors de tokens.cor");
}

// 2. valores compartilhados (somente pares que representam o mesmo token) ---
const pares = [
  ["primary", "--sp-brand"],
  ["primaryDark", "--sp-brand-dark"],
  ["surface", "--sp-surface"],
];
for (const [chave, variavel] of pares) {
  const m = tokens.match(new RegExp(`\\b${chave}:\\s*"([^"]+)"`));
  const c = css.match(new RegExp(`${variavel}:\\s*([^;]+);`));
  if (!m) { problemas.push(`tokens.ts: ${chave} ausente`); continue; }
  if (!c) { problemas.push(`global.css: ${variavel} ausente`); continue; }
  if (m[1].toUpperCase() !== c[1].trim().toUpperCase()) {
    problemas.push(`${chave} (${m[1]}) != ${variavel} (${c[1].trim()})`);
  }
}

// 3. API de colors preservada ----------------------------------------------
const chavesNecessarias = ["primary", "primaryDark", "warning", "vagaLivre", "vagaOcupada", "vagaInativa"];
for (const chave of chavesNecessarias) {
  if (!new RegExp(`\\b${chave}:`).test(tokens)) problemas.push(`tokens.cor sem ${chave}`);
}

// 4/5. imports mortos e composicao proibida --------------------------------
function arquivos(dir, ext) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...arquivos(p, ext));
    else if (e.name.endsWith(ext)) out.push(p);
  }
  return out;
}
for (const arquivo of arquivos(path.join(front, "src"), ".tsx")) {
  const src = fs.readFileSync(arquivo, "utf8");
  const imp = src.match(/import \{([^}]+)\} from ["'][^"']*styles\/recipes["'];/);
  if (!imp) continue;
  const nomes = imp[1].split(",").map((s) => s.trim()).filter(Boolean);
  const corpo = src.slice(0, imp.index) + src.slice(imp.index + imp[0].length);
  const usado = (n) =>
    new RegExp("className=\\{\\s*" + n + "\\s*\\}").test(corpo) ||
    corpo.includes("className={`${" + n + "}") ||
    corpo.includes("${" + n + "} ${") ||
    new RegExp("=\\s*" + n + "\\s*;").test(corpo);
  const mortos = nomes.filter((n) => !usado(n));
  if (mortos.length) problemas.push(`${path.relative(raiz, arquivo)}: imports mortos [${mortos.join(", ")}]`);
  const srcSemComentario = src.replace(/\/\*[\s\S]*?\*\//g, "");
  if (/\bcn\(/.test(srcSemComentario)) problemas.push(`${path.relative(raiz, arquivo)}: usa cn() — composicao conflitante proibida`);
}
const recipesSemComentario = recipes.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
if (/\bcn\(|export function cn/.test(recipesSemComentario)) {
  problemas.push("recipes.ts exporta cn() — composicao conflitante proibida");
}

if (problemas.length) {
  console.error("FALHA na auditoria da camada de estilos:");
  for (const p of problemas) console.error("  - " + p);
  process.exit(1);
}
console.log("OK: tokens consumidos, valores sincronizados, zero imports mortos, zero cn()");
