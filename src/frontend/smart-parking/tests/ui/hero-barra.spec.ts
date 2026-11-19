import { expect, expectSemOverflowHorizontal, test } from "./helpers";

test("barra de sincronizacao fica junto do Hero e nao desloca o CTA", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();

  const hero = page.locator(".sp-hero");
  const barra = page.getByTestId("hero-barra-atualizacao");
  const cta = page.getByRole("button", { name: /Ver Vagas Disponíveis/ });
  await expect(barra).toBeVisible();
  await expect(cta).toBeEnabled();

  const caixaHero = await hero.boundingBox();
  const caixaBarra = await barra.boundingBox();
  const caixaCTA = await cta.boundingBox();
  expect(caixaHero).not.toBeNull();
  expect(caixaBarra).not.toBeNull();
  expect(caixaCTA).not.toBeNull();
  expect(caixaBarra!.y).toBeGreaterThan(caixaCTA!.y + caixaCTA!.height);
  expect(caixaBarra!.y + caixaBarra!.height).toBeLessThanOrEqual(
    caixaHero!.y + caixaHero!.height + 1,
  );
  await expectSemOverflowHorizontal(page);
});

test("a Home revalida em 1500 ms e anima somente durante requisicoes reais", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();

  let chamadas = 0;
  await page.route("**/api/estacionamentos", async (route) => {
    chamadas += 1;
    // Simula latencia da API para verificar estado animado por tempo real.
    await new Promise((resolve) => setTimeout(resolve, 650));
    await route.continue();
  });

  await expect.poll(() => chamadas, { timeout: 6500 }).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId("hero-barra-indeterminada")).toBeVisible({
    timeout: 5000,
  });
  await expect(
    page.getByText("Vagas sincronizadas · nova consulta a cada 1,5 s"),
  ).toBeVisible({ timeout: 5000 });
  await expect(page.getByRole("button", { name: /Ver Vagas Disponíveis/ })).toBeEnabled();
});

test("prefers-reduced-motion mantém barra e texto sem deslocamento animado", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();

  await page.route("**/api/estacionamentos", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 900));
    await route.continue();
  });
  const indicador = page.getByTestId("hero-barra-indeterminada");
  await expect(indicador).toBeVisible({ timeout: 5500 });
  const primeiro = await indicador.evaluate((el) => getComputedStyle(el).transform);
  await page.waitForTimeout(170);
  const segundo = await indicador.evaluate((el) => getComputedStyle(el).transform);
  expect(segundo).toBe(primeiro);
});
