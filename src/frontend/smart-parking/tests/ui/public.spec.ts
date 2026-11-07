import {
  expect,
  expectSemOverflowHorizontal,
  gotoLogin,
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
  const vaga = page.getByRole("button", { name: "Vaga A-01 — livre" });
  await expect(vaga).toBeVisible();
  await expect(page.getByRole("button", { name: "Vaga A-03 — ocupada" })).toBeVisible();
  const caixaVaga = await vaga.boundingBox();
  expect(caixaVaga?.width).toBeGreaterThanOrEqual(44);
  expect(caixaVaga?.height).toBeGreaterThanOrEqual(44);
  await expectSemOverflowHorizontal(page);

  expect(chamadasApi.length).toBeGreaterThan(0);
  for (const url of chamadasApi) {
    expect(new URL(url).origin, url).toBe("http://127.0.0.1:8000");
  }
});


test("seletor de shopping flutua sobre o conteúdo, é acessível e fecha com Escape", async ({ page }) => {
  await page.goto("/");
  const seletor = page.getByRole("button", { name: /Selecionar shopping:/ });
  await expect(seletor).toBeVisible();
  await expect(seletor).toHaveAttribute("aria-expanded", "false");

  await seletor.click();
  await expect(seletor).toHaveAttribute("aria-expanded", "true");
  const lista = page.getByRole("list", { name: "Lista de shoppings" });
  await expect(lista).toBeVisible();
  expect(await lista.evaluate((element) => getComputedStyle(element).position)).toBe("absolute");

  const caixaSeletor = await seletor.boundingBox();
  const caixaLista = await lista.boundingBox();
  expect(caixaLista?.y).toBeGreaterThanOrEqual(
    (caixaSeletor?.y ?? 0) + (caixaSeletor?.height ?? 0) - 2,
  );
  await expect(page.getByRole("button", { name: /Shopping QA Norte/ }).first()).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(lista).toHaveCount(0);
  await expect(seletor).toHaveAttribute("aria-expanded", "false");
  await expectSemOverflowHorizontal(page);
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


test("login em 900px usa coluna única e em 1024px mantém o split sem overflow", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await gotoLogin(page);
  await expect(page.getByText("Bem-vindo ao Smart Parking")).toBeVisible();
  await expect(
    page.getByText("Monitoramento inteligente de vagas em shoppings de Manaus, em tempo real."),
  ).toHaveCount(0);
  await expectSemOverflowHorizontal(page);

  await page.setViewportSize({ width: 1024, height: 900 });
  await gotoLogin(page);
  await expect(page.getByText("Acesse sua conta para continuar")).toBeVisible();
  await expectSemOverflowHorizontal(page);
});
