// Publicacao Pages: permitir "Adicionar a Tela de Inicio" no iPhone/Android.
// Não registra Service Worker e NÃO promete Web Push/offline.
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const source = path.join(root, "src/frontend/smart-parking");
const dist = path.join(source, "dist");
const htmlPath = path.join(dist, "index.html");
const logoPath = path.join(source, "src/assets/imgs/Logo.png");

if (!fs.existsSync(htmlPath)) {
  throw new Error("Expo SPA nao exportou dist/index.html");
}
if (!fs.existsSync(logoPath)) {
  throw new Error("Icone do aplicativo nao encontrado");
}

const manifest = {
  id: "/",
  name: "Smart Parking",
  short_name: "Smart Parking",
  description: "Piloto academico de estacionamento inteligente em Manaus. Dados de vagas e precos simulados.",
  start_url: "/",
  scope: "/",
  display: "standalone",
  background_color: "#F8FAFC",
  theme_color: "#2563EB",
  lang: "pt-BR",
  icons: [{ src: "/smartparking-icon.png", type: "image/png", sizes: "any" }],
};
fs.copyFileSync(logoPath, path.join(dist, "smartparking-icon.png"));
fs.writeFileSync(
  path.join(dist, "manifest.webmanifest"),
  JSON.stringify(manifest, null, 2) + "\n",
);
const original = fs.readFileSync(htmlPath, "utf8");
if (!/<\/head>/i.test(original)) {
  throw new Error("index.html sem </head>, nao e seguro injetar o manifesto");
}
const tags = [
  '<meta name="theme-color" content="#2563EB">',
  '<meta name="apple-mobile-web-app-capable" content="yes">',
  '<meta name="apple-mobile-web-app-status-bar-style" content="default">',
  '<meta name="apple-mobile-web-app-title" content="Smart Parking">',
  '<link rel="manifest" href="/manifest.webmanifest">',
  '<link rel="apple-touch-icon" href="/smartparking-icon.png">',
].join("\n");
if (!original.includes('href="/manifest.webmanifest"')) {
  fs.writeFileSync(htmlPath, original.replace(/<\/head>/i, tags + "\n</head>"));
}
console.log("Web App Manifest + icon + modo standalone configurados no Pages.");
