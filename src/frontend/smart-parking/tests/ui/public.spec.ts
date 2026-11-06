import {
  expect,
  expectSemOverflowHorizontal,
  test,
} from "./helpers";


test("home usa API same-origin, CTA visível e mapa público navegável", async ({ page }) => {
  const chamadasApi: string[] = [];
  page.on("response", (response) => {
    if (response.url().includes("/api/")) chamadasApi.push(response.url());
  });

  await page.goto("/");

  await expect(page.getByText(/Encontre Vagas de/).first()).toBeVisible();
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect(page.getByText("Shopping QA Norte").first()).toBeVisible();

  const cta = page.getByRole("button", { name: /Ver Vagas Disponíveis/ });
  await expect(cta).toBeVisible();
  await expect(cta).toBeEnabled();
  const estilo = await cta.evaluate((element) => {
    const computed = getComputedStyle(element);
    return { fundo: computed.backgroundColor, altura: element.getBoundingClientRect().height };
  });
  expect(estilo.fundo).toBe("rgb(37, 99, 235)");
  expect(estilo.altura).toBeGreaterThanOrEqual(44);
  await expectSemOverflowHorizontal(page);

  await cta.click();
  await expect(page).toHaveURL(/\/shopping\/[^/]+$/);
  await expect(page.getByText("Shopping QA Centro", { exact: true }).last()).toBeVisible();
  await expect(page.getByRole("button", { name: "Vaga A-01 — livre" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Vaga A-03 — ocupada" })).toBeVisible();
  await expectSemOverflowHorizontal(page);

  expect(chamadasApi.length).toBeGreaterThan(0);
  for (const url of chamadasApi) {
    expect(new URL(url).origin, url).toBe("http://127.0.0.1:8000");
  }
});


test("explorar filtra shoppings, apresenta vazio e abre o resultado", async ({ page }) => {
  await page.goto("/explorar");
  const busca = page.getByPlaceholder("Buscar por shopping ou bairro…");
  await expect(busca).toBeVisible();
  await expect(page.getByText("Shopping QA Centro")).toBeVisible();

  await busca.fill("Norte");
  await expect(page.getByText("Shopping QA Norte")).toBeVisible();
  await expect(page.getByText("Shopping QA Centro")).toHaveCount(0);

  await busca.fill("shopping que não existe");
  await expect(page.getByText("Nenhum shopping encontrado")).toBeVisible();

  await busca.fill("Norte");
  await page.getByText("Shopping QA Norte").click();
  await expect(page).toHaveURL(/\/shopping\/[^/]+$/);
  await expect(page.getByRole("button", { name: "Vaga C-01 — livre" })).toBeVisible();
});


test("viewport móvel mantém login e home sem overflow e com ações alcançáveis", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");

  await expect(page.getByText("Bem-vindo ao Smart Parking")).toBeVisible();
  const entrar = page.getByRole("button", { name: "Entrar", exact: true });
  await expect(entrar).toBeVisible();
  const caixa = await entrar.boundingBox();
  expect(caixa?.height).toBeGreaterThanOrEqual(44);
  await expectSemOverflowHorizontal(page);

  await page.getByRole("button", { name: /Início/ }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Ver Vagas Disponíveis/ })).toBeVisible();
  await expectSemOverflowHorizontal(page);
});
