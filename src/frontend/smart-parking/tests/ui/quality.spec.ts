import type { Locator } from "@playwright/test";
import { expect, gotoLogin, test } from "./helpers";

async function estilo(botao: Locator) {
  return botao.evaluate((element: HTMLElement) => {
    const css = getComputedStyle(element);
    return {
      background: css.backgroundColor,
      color: css.color,
      transitionProperty: css.transitionProperty,
      transitionDuration: css.transitionDuration,
      boxShadow: css.boxShadow,
      transform: css.transform,
      height: element.getBoundingClientRect().height,
    };
  });
}

const botoesPrimarios = [
  { rota: "/login", nome: "Entrar", login: true },
  { rota: "/", nome: "Entrar", login: false },
  { rota: "/explorar", nome: "Criar conta grátis", login: false },
];

for (const cenario of botoesPrimarios) {
  test(`botão ${cenario.nome} em ${cenario.rota} tem cor, foco e transição consistentes`, async ({ page }) => {
    if (cenario.login) await gotoLogin(page);
    else await page.goto(cenario.rota);

    const botao = page.getByRole("button", { name: cenario.nome, exact: true }).first();
    await expect(botao).toBeVisible();
    const normal = await estilo(botao);

    await botao.hover();
    await expect.poll(async () => (await estilo(botao)).background).toBe("rgb(29, 78, 216)");
    const hover = await estilo(botao);
    await page.mouse.down();
    await expect.poll(async () => (await estilo(botao)).background).toBe("rgb(30, 64, 175)");
    const pressed = await estilo(botao);
    // Sai do alvo antes de soltar: mede :active sem disparar a navegação.
    await page.mouse.move(0, 0);
    await page.mouse.up();
    await page.keyboard.press("Tab");
    await botao.focus();
    const focado = await estilo(botao);

    test.info().annotations.push({
      type: "estilos-medidos",
      description: JSON.stringify({ normal, hover, pressed, focado }),
    });
    const transiciona = (propriedade: string) =>
      normal.transitionProperty === "all" || normal.transitionProperty.includes(propriedade);
    expect(normal.background).toBe("rgb(37, 99, 235)");
    expect(hover.background).toBe("rgb(29, 78, 216)");
    expect(pressed.background).toBe("rgb(30, 64, 175)");
    expect(transiciona("background-color")).toBeTruthy();
    expect(transiciona("transform")).toBeTruthy();
    expect(normal.transitionDuration).toContain("0.15s");
    expect(focado.boxShadow).not.toBe("none");
    expect(normal.height).toBeGreaterThanOrEqual(44);
  });
}

test("botão branco do mapa tem contraste e label sincronizado com hover/foco", async ({ page }) => {
  const lista = await page.request.get("/api/estacionamentos");
  const estacionamentos = (await lista.json()) as Array<{ id: string; nome: string }>;
  const centro = estacionamentos.find((item) => item.nome === "Shopping QA Centro");
  if (!centro) throw new Error("Shopping QA Centro ausente no seed");
  await page.goto(`/shopping/${centro.id}`);

  const botao = page.getByRole("button", { name: "Destacar no mapa", exact: true });
  const label = botao.getByText("Destacar no mapa", { exact: true });
  await expect(botao).toBeVisible();
  expect(await botao.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe(
    "rgb(255, 255, 255)",
  );
  expect(await label.evaluate((element) => getComputedStyle(element).color)).toBe(
    "rgb(37, 99, 235)",
  );
  expect(await label.evaluate((element) => getComputedStyle(element).transitionProperty)).toContain(
    "color",
  );

  await botao.hover();
  await expect.poll(() =>
    botao.evaluate((element) => getComputedStyle(element).backgroundColor),
  ).toBe("rgb(239, 246, 255)");
  await expect.poll(() =>
    label.evaluate((element) => getComputedStyle(element).color),
  ).toBe("rgb(29, 78, 216)");

  await page.mouse.move(0, 0);
  await page.keyboard.press("Tab");
  await botao.focus();
  await expect.poll(() =>
    label.evaluate((element) => getComputedStyle(element).color),
  ).toBe("rgb(29, 78, 216)");
  expect(await botao.evaluate((element) => getComputedStyle(element).boxShadow)).not.toBe("none");
  await page.screenshot({
    path: test.info().outputPath("botao-mapa-foco.png"),
    fullPage: true,
  });
});

test("loading mantém nome acessível e informa estado ocupado", async ({ page }) => {
  await gotoLogin(page);
  await page.getByLabel("E-mail ou telefone", { exact: true }).fill("admin@smartparking.com");
  await page.getByLabel("Senha", { exact: true }).fill("admin123");
  await page.route("**/auth/login", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500));
    await route.continue();
  });

  const entrar = page.getByRole("button", { name: "Entrar", exact: true });
  await entrar.click();
  await expect(entrar).toBeDisabled();
  await expect(entrar).toHaveAttribute("aria-busy", "true");
  await expect(entrar).toHaveAccessibleName("Entrar");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("campos inválidos e alternância de senha são compreensíveis para leitor de tela", async ({ page }) => {
  await gotoLogin(page);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  const email = page.getByLabel("E-mail ou telefone", { exact: true });
  await expect(email).toHaveAccessibleName("E-mail ou telefone");
  await expect(email).toHaveAttribute("aria-invalid", "true");
  await expect(email).toHaveAttribute("aria-required", "true");
  await expect(page.getByText("Informe seu e-mail ou telefone")).toBeVisible();

  const mostrar = page.getByRole("button", { name: "Mostrar senha" });
  await expect(mostrar).toBeVisible();
  await mostrar.click();
  await expect(page.getByRole("button", { name: "Ocultar senha" })).toBeVisible();
});

test("mapa reflete mudança externa em até 8 segundos sem reload", async ({ page }) => {
  const lista = await page.request.get("/api/estacionamentos");
  const estacionamentos = (await lista.json()) as Array<{ id: string; nome: string }>;
  const centro = estacionamentos.find((item) => item.nome === "Shopping QA Centro");
  if (!centro) throw new Error("Shopping QA Centro ausente no seed");

  await page.goto(`/shopping/${centro.id}`);
  await expect(page.getByRole("button", { name: "Vaga A-01 — livre" })).toBeVisible();

  const autenticacao = await page.request.post("/auth/login", {
    data: { email: "admin@smartparking.com", senha: "admin123" },
  });
  expect(autenticacao.ok()).toBeTruthy();
  const { access_token: token } = await autenticacao.json();
  const headers = { Authorization: `Bearer ${token}` };
  const mapa = await page.request.get(`/api/estacionamentos/${centro.id}/vagas`);
  const dados = await mapa.json();
  const vaga = dados.vagas.find((item: { codigo: string }) => item.codigo === "A-01");

  await page.request.patch(`/api/vagas/${vaga.id}/status`, {
    headers,
    data: { status: "ocupada", origem: "manual" },
  }).then((response) => expect(response.ok()).toBeTruthy());
  const inicio = Date.now();
  try {
    await expect(page.getByRole("button", { name: "Vaga A-01 — ocupada" })).toBeVisible({ timeout: 8_000 });
    test.info().annotations.push({ type: "latencia-tempo-real", description: `${Date.now() - inicio}ms` });
  } finally {
    await page.request.patch(`/api/vagas/${vaga.id}/status`, {
      headers,
      data: { status: "livre", origem: "manual" },
    });
  }
});

test("queda da API preserva cache, informa stale data e recupera sem reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("sp:cache:estacionamentos"))).not.toBeNull();

  await page.route("**/api/estacionamentos", (route) => route.abort("failed"));
  await page.reload();
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect(page.getByText(/mostrando a última leitura/i)).toBeVisible();

  await page.unroute("**/api/estacionamentos");
  await expect(page.getByText(/mostrando a última leitura/i)).toHaveCount(0, { timeout: 12_000 });
  await expect(page.getByText("Shopping QA Norte").first()).toBeVisible();
});

test("pintura inicial e API concorrente respeitam orçamento de desempenho", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  const fcp = await page.evaluate(() =>
    performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0,
  );

  const inicio = performance.now();
  const respostas = await Promise.all(
    Array.from({ length: 24 }, (_, indice) =>
      page.request.get(indice % 2 === 0 ? "/api/estacionamentos" : "/health"),
    ),
  );
  const duracoes = await Promise.all(
    respostas.map(async (resposta) => {
      expect(resposta.status()).toBe(200);
      return resposta.timing().responseEnd;
    }),
  );
  const total = performance.now() - inicio;
  duracoes.sort((a, b) => a - b);
  const p95 = duracoes[Math.min(duracoes.length - 1, Math.floor(duracoes.length * 0.95))];
  const metricas = { fcpMs: Math.round(fcp), p95Ms: Math.round(p95), lote24Ms: Math.round(total) };
  console.log("MÉTRICAS_DESEMPENHO", JSON.stringify(metricas));
  await test.info().attach("desempenho.json", {
    body: JSON.stringify(metricas),
    contentType: "application/json",
  });

  expect(fcp).toBeGreaterThan(0);
  expect(fcp).toBeLessThan(4_000);
  expect(p95).toBeLessThan(1_000);
  expect(total).toBeLessThan(5_000);
});
