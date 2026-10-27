#!/usr/bin/env node
/**
 * Verifica o canal estável do Expo e os pins das dependências nativas.
 * `node scripts/check_expo_sdk.cjs repin` apenas lista specs exatas para o
 * instalador oficial desfazer os ranges que `expo install --fix` pode gravar.
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const app = path.join(root, "src/frontend/smart-parking");
const manifest = require(path.join(app, "package.json"));
const lock = require(path.join(app, "package-lock.json"));
const exact = /^\d+\.\d+\.\d+$/;

let bundled = {};
try {
  bundled = require(path.join(app, "node_modules/expo/bundledNativeModules.json"));
} catch {
  if (process.argv[2] !== "repin") {
    console.error("Expo não instalado. Execute npm ci em src/frontend/smart-parking.");
    process.exit(1);
  }
}

const managed = new Set([
  "expo",
  "babel-preset-expo",
  ...Object.keys(bundled),
]);
const direct = Object.entries({
  ...manifest.dependencies,
  ...manifest.devDependencies,
}).filter(([name]) => managed.has(name));

if (process.argv[2] === "repin") {
  for (const [name, range] of direct) {
    if (exact.test(range)) continue;
    const locked = lock.packages?.[`node_modules/${name}`]?.version;
    if (!locked || !exact.test(locked)) {
      console.error(`Não há versão estável no lockfile para repinar ${name}.`);
      process.exit(1);
    }
    console.log(`${name}@${locked}`);
  }
  process.exit(0);
}

const latest = execFileSync("npm", ["view", "expo", "version"], {
  encoding: "utf8",
  stdio: ["ignore", "pipe", "inherit"],
}).trim();
const current = manifest.dependencies?.expo;
const errors = [];

if (!exact.test(latest)) {
  errors.push(`Canal latest inesperado: ${latest}`);
}
if (current !== latest) {
  errors.push(
    `Expo desatualizado: projeto=${current}; latest=${latest}. ` +
      "Execute bash scripts/update_expo_sdk.sh.",
  );
}

for (const [name, range] of direct) {
  if (!exact.test(range)) {
    errors.push(`${name} deve ter pin exato, encontrado: ${range}`);
  }
  const locked = lock.packages?.[`node_modules/${name}`]?.version;
  if (!locked) {
    errors.push(`${name} não existe no package-lock.json`);
  }
}

const lockedExpo = lock.packages?.["node_modules/expo"]?.version;
if (lockedExpo !== current) {
  errors.push(`Lockfile divergente: expo=${lockedExpo}; manifest=${current}`);
}
const rootLockExpo = lock.packages?.[""]?.dependencies?.expo;
if (rootLockExpo !== current) {
  errors.push(`Raiz do lockfile divergente: expo=${rootLockExpo}; manifest=${current}`);
}

const installedPath = path.join(app, "node_modules/expo/package.json");
if (!fs.existsSync(installedPath)) {
  errors.push("node_modules ausente; execute npm ci antes da verificação");
} else if (require(installedPath).version !== current) {
  errors.push(
    `Instalação divergente: node_modules/expo=${require(installedPath).version}; manifest=${current}`,
  );
}

if (errors.length) {
  console.error(errors.map((error) => `✖ ${error}`).join("\n"));
  process.exit(1);
}

console.log(
  `✔ Expo SDK ${current} no canal latest; ${direct.length} pins nativos exatos; lockfile e instalação consistentes.`,
);
