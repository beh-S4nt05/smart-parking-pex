#!/usr/bin/env node
/**
 * Guard de regressão: nenhuma regra de `transition` pode chegar ao runtime
 * NATIVO do app (iOS/Android).
 *
 * Reprodução do bug (2026-11-13): o `react-native-css-interop@0.2.7` (NativeWind
 * v4) transforma `transition` em animações com Reanimated. Para `box-shadow` e
 * `transform`, o estilo vira um ARRAY CONGELADO; `processTransition` chama
 * `assignToTarget` com `arrayMergeStyle: "push"` e o Hermes lança
 * "TypeError: cannot add a new property" no boot (Card -> StatusPanel -> Index).
 *
 * A correção: `transition`/`transform`/`duration`/`ease`/`motion-reduce:*` só
 * geram CSS na plataforma Web (variante `web:` + `@media (display-mode: browser)`,
 * que é FALSE em iOS/Android — conditions.js: value === "native" ||
 * Platform.OS === value). No nativo o feedback de toque continua vindo do
 * `Animated` do RN core.
 *
 * O guard COMPILE o CSS real com o Tailwind CLI (NATIVEWIND_OS=ios/android) e
 * com o próprio compilador do css-interop, então não depende de emulador.
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const front = path.resolve(__dirname, "../src/frontend/smart-parking");
const input = path.resolve(front, "assets/Styles/global.css");
const out = path.join(os.tmpdir(), "sp-css-native-guard.css");

function compilar(platform) {
  execFileSync(
    "npx",
    ["tailwindcss", "-i", input, "-o", out],
    {
      cwd: front,
      env: { ...process.env, NATIVEWIND_OS: platform, BROWSERSLIST_ENV: "native" },
      stdio: "pipe",
    },
  );
  return fs.readFileSync(out, "utf8");
}

function mediaTrue(cond, platform) {
  if (!cond) return true;
  if (cond.type === "operation") return cond.conditions.every((x) => mediaTrue(x, platform));
  if (
    cond.type === "feature" &&
    cond.value?.type === "plain" &&
    cond.value.name === "display-mode"
  ) {
    const v = cond.value.value?.value;
    return v === "native" || platform === v;
  }
  return true;
}

function regrasComTransicao(css, platform) {
  // require resolve a partir do frontend: node_modules está lá, e o script
  // vive em scripts/ (fora do scope de node_modules do frontend).
  const { createRequire } = require("node:module");
  const frontRequire = createRequire(path.join(front, "index.js"));
  const { cssToReactNativeRuntime } = frontRequire("react-native-css-interop/dist/css-to-rn");
  const compiled = cssToReactNativeRuntime(css, {
    ignorePropertyWarningRegex: ["^--tw-"],
    grouping: ["^group(/.*)?"],
  }).rules || {};

  const aceito = [];
  for (const [nome, grupo] of Object.entries(compiled)) {
    for (const [tipo, arr] of Object.entries(grupo)) {
      if (!Array.isArray(arr)) continue;
      for (const regra of arr) {
        if (!regra.transition) continue;
        const medias = regra.media || [];
        if (medias.length === 0 || medias.every((m) => mediaTrue(m.condition, platform))) {
          aceito.push(`${nome}.${tipo}`);
        }
      }
    }
  }
  return aceito;
}


function removerBlocosMedia(css) {
  // Remove blocos @media completos (contagem de colchetes: os @media têm
  // regras com {} aninhadas). Uma regex não-greedy pararia no primeiro }.
  let out = "";
  let i = 0;
  while (i < css.length) {
    const idx = css.indexOf("@media", i);
    if (idx === -1) {
      out += css.slice(i);
      break;
    }
    out += css.slice(i, idx);
    const open = css.indexOf("{", idx);
    if (open === -1) break;
    let depth = 1;
    let j = open + 1;
    while (j < css.length && depth > 0) {
      const c = css[j];
      if (c === "{") depth += 1;
      else if (c === "}") depth -= 1;
      j += 1;
    }
    i = j;
  }
  return out;
}

function semComentarios(css) {
  // Tailwind preserva comentários CSS na saída; o analisador só deve ver
  // regras declarativas (fora de /* ... */).
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

const erros = [];

for (const platform of ["ios", "android"]) {
  const css = semComentarios(compilar(platform));

  // 1. CSS compilado para a plataforma não deve declarar transições
  //    FORA de qualquer bloco @media (regras dentro de @media (display-mode:
  //    browser) são condicionadas e o css-interop não as coleta — a verificação
  //    definitiva está no passo 3, que usa o compilador real).
  const foraDeMedia = removerBlocosMedia(css);
  const declaradas = foraDeMedia
    .split("\n")
    .filter((l) => /transition(-property|-duration|-timing-function)?\s*:/.test(l))
    .map((l) => l.trim());
  if (declaradas.length) {
    erros.push(`${platform}: CSS declara transição fora de @media: ${declaradas.slice(0, 5).join(" | ")}`);
  }

  // 3. Aplicar o compilador REAL e simular testRule no runtime nativo.
  const aceito = regrasComTransicao(css, platform);
  if (aceito.length) {
    erros.push(
      `${platform}: runtime nativo aceitaria ${aceito.length} transições: ${aceito
        .slice(0, 6)
        .join(", ")}`,
    );
  }
}

// 4. A WEB deve manter as transições (caso contrário perde-se o feedback).
const cssWeb = compilar("web");
if (!/\.web\\:transition-colors/.test(cssWeb) && !/transition-property:/.test(cssWeb)) {
  erros.push("web: perdeu as classes de transição (variante web:)");
}

if (erros.length) {
  console.error("FALHA: transições presentes no bundle nativo — causa crash no Android/iOS");
  for (const e of erros) console.error("  - " + e);
  process.exit(1);
}
console.log("OK: zero transições no bundle nativo (iOS/Android); Web mantida.");
