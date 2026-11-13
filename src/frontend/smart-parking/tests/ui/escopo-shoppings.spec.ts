/**
 * Controle de usuários: cada papel só vê os shoppings vinculados.
 *
 * A lista do painel vem de /api/admin/estacionamentos (filtrada no servidor),
 * e as rotas de dados também são escopadas — esconder na UI não basta.
 */
import type { Page } from "@playwright/test";
import type { Estacionamento } from "../../src/types/api";
import { expect, login, test } from "./helpers";

const CENTRO = "Shopping QA Centro";
const NORTE = "Shopping QA Norte";

async function nomesDasLinhas(page: Page) {
  const linhas = page.locator('[data-testid^="shopping-linha-"]');
  // A lista vem da API: espera a primeira linha antes de medir, senão o
  // placeholder "Carregando shoppings…" gera um array vazio por corrida.
  await expect(linhas.first()).toBeVisible({ timeout: 15_000 });
  const textos = await linhas.allInnerTexts();
  return textos.map((t: string) => t.split("\n")[0].trim());
}

test("admin vê todos os shoppings e a opção 'Todos'", async ({ page }) => {
  await login(page, "admin@smartparking.com", "admin123");
  await expect(page).toHaveURL(/\/dashboard$/);

  await expect(page.getByRole("button", { name: "Selecionar Todos os shoppings" })).toBeVisible();
  await expect(page.getByText("Somente o administrador altera esta lista")).toBeVisible();
  const nomes = await nomesDasLinhas(page);
  expect(nomes).toContain("Todos os shoppings");
  expect(nomes).toContain(CENTRO);
  expect(nomes).toContain(NORTE);

  await page.getByRole("button", { name: `Selecionar ${CENTRO}` }).click();
  await expect(page.getByRole("button", { name: `Selecionar ${CENTRO}` })).toBeVisible();
  await page.getByRole("button", { name: "Selecionar Todos os shoppings" }).click();
});

test("gestor vê SOMENTE os 2 shoppings vinculados — nunca 'Todos'", async ({ page }) => {
  await login(page, "gestor@smartparking.com", "gestor123");
  await expect(page).toHaveURL(/\/dashboard$/);

  await expect(page.getByRole("button", { name: "Selecionar Todos os shoppings" })).toHaveCount(0);
  const nomes = await nomesDasLinhas(page);
  expect(nomes).toHaveLength(2);
  expect(nomes).toContain(CENTRO);
  expect(nomes).toContain(NORTE);

  // Alternar entre os próprios é permitido.
  await page.getByRole("button", { name: `Selecionar ${NORTE}` }).click();
  await expect(page.getByRole("button", { name: `Selecionar ${NORTE}` })).toBeVisible();
});

test("financeiro vê UM shopping, travado, sem 'Todos'", async ({ page }) => {
  await login(page, "financeiro@smartparking.com", "financ123");
  await expect(page).toHaveURL(/\/dashboard$/);

  await expect(page.getByRole("button", { name: "Selecionar Todos os shoppings" })).toHaveCount(0);
  const nomes = await nomesDasLinhas(page);
  expect(nomes).toHaveLength(1);
  expect(nomes[0]).toContain(CENTRO);
  await expect(page.getByText(/travado/i).first()).toBeVisible();

  // Linha travada não é ação de seleção.
  await expect(page.getByRole("button", { name: `Selecionar ${CENTRO}` })).toHaveCount(0);
});

test("API não entrega shopping alheio nem dados gerenciais de outro", async ({ page, request }) => {
  await login(page, "financeiro@smartparking.com", "financ123");
  await expect(page).toHaveURL(/\/dashboard$/);

  const lista: Estacionamento[] = await (await request.get("/api/estacionamentos")).json();
  const alheio = (lista as Estacionamento[]).find((e: Estacionamento) => e.nome === NORTE);
  expect(alheio, "seed deve ter um shopping alheio ao financeiro").toBeTruthy();
  const alheioId = (alheio as Estacionamento).id;

  const sessao = await request.post("/auth/login", {
    data: { email: "financeiro@smartparking.com", senha: "financ123" },
  });
  const { access_token } = await sessao.json();
  const headers = { Authorization: `Bearer ${access_token}` };

  const vitrine = await request.get("/api/estacionamentos", { headers });
  expect(vitrine.status()).toBe(200);
  expect((await vitrine.json() as Estacionamento[]).map((e: Estacionamento) => e.nome)).toEqual([CENTRO]);

  const mapaAlheio = await request.get(`/api/estacionamentos/${alheioId}/vagas`, { headers });
  expect(mapaAlheio.status()).toBe(403);

  const eventosAlheios = await request.get("/api/admin/eventos", {
    headers,
    params: { estacionamento_id: alheioId },
  });
  expect(eventosAlheios.status()).toBe(403);
});

test("admin não consegue criar 2 financeiros no mesmo shopping", async ({ request }) => {
  const sessao = await request.post("/auth/login", {
    data: { email: "admin@smartparking.com", senha: "admin123" },
  });
  const { access_token } = await sessao.json();
  const headers = { Authorization: `Bearer ${access_token}` };
  const lista: Estacionamento[] = await (await request.get("/api/estacionamentos")).json();

  const criado = await request.post("/api/admin/usuarios", {
    headers,
    data: {
      nome: "Financeiro Duplicado",
      email: "financeiro.duplicado@teste.dev",
      senha: "senha123",
      role: "financeiro",
      estacionamento_id: lista[0].id,
    },
  });
  expect(criado.status()).toBe(409);
  expect((await criado.json()).detail.toLowerCase()).toContain("já possui");
});
