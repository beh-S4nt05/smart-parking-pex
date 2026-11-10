/* Servidor somente para QA: export estático + proxy same-origin para a API. */
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../src/frontend/smart-parking/dist");
const port = Number(process.env.UI_WEB_PORT || 8000);
const apiPort = Number(process.env.UI_API_PORT || 8010);
const apiPrefix = /^\/(?:api(?:\/|$)|auth(?:\/|$)|health$|docs(?:\/|$)|redoc(?:\/|$)|openapi\.json$)/;
const mime = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function proxy(req, res) {
  const upstream = http.request(
    {
      hostname: "127.0.0.1",
      port: apiPort,
      path: req.url,
      method: req.method,
      headers: { ...req.headers, host: `127.0.0.1:${apiPort}` },
    },
    (response) => {
      res.writeHead(response.statusCode || 502, response.headers);
      response.pipe(res);
    },
  );
  upstream.on("error", (error) => {
    res.writeHead(502, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: `API de QA indisponível: ${error.code}` }));
  });
  req.pipe(upstream);
}

function candidateFiles(pathname) {
  const clean = pathname === "/" ? "/index" : pathname.replace(/\/$/, "");
  const candidatos = [
    `.${clean}`,
    `.${clean}.html`,
    `.${clean}/index.html`,
  ];
  // Rotas dinâmicas do Expo Router são pré-renderizadas em `[id].html`.
  // Sem este mapeamento, /shopping/<uuid> caía em index.html e o cliente
  // hidratava uma árvore diferente (React #418 / tela em branco).
  if (/^\/shopping\/[^/]+$/.test(clean)) candidatos.push("./shopping/[id].html");
  // 404 real: servir +not-found.html em vez de index.html evita mismatch de
  // hidratação e mantém a tela "Unmatched Route" utilizável.
  candidatos.push("./+not-found.html");
  return candidatos;
}

function serve(req, res) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, "http://ui.test").pathname);
  } catch {
    res.writeHead(400);
    res.end("URL inválida");
    return;
  }

  for (const candidate of candidateFiles(pathname)) {
    const file = path.resolve(root, candidate);
    if (!file.startsWith(`${root}${path.sep}`) || !fs.existsSync(file)) continue;
    if (!fs.statSync(file).isFile()) continue;
    res.writeHead(200, {
      "Content-Type": mime[path.extname(file)] || "application/octet-stream",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    fs.createReadStream(file).pipe(res);
    return;
  }
  res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("Arquivo não encontrado");
}

const server = http.createServer((req, res) => {
  if (req.url === "/__ui_health") {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("ok");
    return;
  }
  if (apiPrefix.test(req.url || "")) {
    proxy(req, res);
    return;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405);
    res.end();
    return;
  }
  serve(req, res);
});

server.listen(port, "0.0.0.0", () => {
  console.log(`UI QA: http://0.0.0.0:${port} → API 127.0.0.1:${apiPort}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
