import { CHAVE_CACHE_ANONIMO } from "../../src/services/cacheChaves";
import { expect, gotoLogin, test } from "./helpers";

test("cache corrompido não impede boot nem substitui a resposta real", async ({ page }) => {
  await page.addInitScript((chave) => {
    localStorage.setItem(chave, "{json-incompleto");
  }, CHAVE_CACHE_ANONIMO);
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect(page.getByText("Shopping QA Norte").first()).toBeVisible();
  await expect(page.getByText(/API indisponível|Sem conexão/i)).toHaveCount(0);
});

test("botão respeita prefers-reduced-motion sem perder a mudança de cor", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await gotoLogin(page);
  const entrar = page.getByRole("button", { name: "Entrar", exact: true });
  const propriedade = await entrar.evaluate(
    (element) => getComputedStyle(element).transitionProperty,
  );
  expect(propriedade).toBe("none");

  await entrar.hover();
  await expect.poll(() =>
    entrar.evaluate((element) => getComputedStyle(element).backgroundColor),
  ).toBe("rgb(29, 78, 216)");
  await page.mouse.down();
  expect(await entrar.evaluate((element) => getComputedStyle(element).transform)).toBe("none");
  await page.mouse.move(0, 0);
  await page.mouse.up();
});

test("API lenta não acumula polling concorrente do mapa", async ({ page }) => {
  const lista = await page.request.get("/api/estacionamentos");
  const estacionamentos = (await lista.json()) as Array<{ id: string; nome: string }>;
  const centro = estacionamentos.find((item) => item.nome === "Shopping QA Centro");
  if (!centro) throw new Error("Shopping QA Centro ausente no seed");
  await page.goto(`/shopping/${centro.id}`);
  await expect(page.getByRole("button", { name: "Vaga A-01 — livre" })).toBeVisible();

  let ativas = 0;
  let maximoAtivas = 0;
  let total = 0;
  await page.route(`**/api/estacionamentos/${centro.id}/vagas`, async (route) => {
    ativas += 1;
    total += 1;
    maximoAtivas = Math.max(maximoAtivas, ativas);
    await new Promise((resolve) => setTimeout(resolve, 6500));
    ativas -= 1;
    await route.continue();
  });

  await expect.poll(() => total, { timeout: 17_000 }).toBeGreaterThanOrEqual(2);
  expect(maximoAtivas).toBe(1);
  await expect.poll(() => ativas, { timeout: 10_000 }).toBe(0);
  await page.unroute(`**/api/estacionamentos/${centro.id}/vagas`);
});
