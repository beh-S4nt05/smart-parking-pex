/** Regressão V1: painel de operação acompanha reservas reais sem refresh manual. */
import { expect, loginViaApi, test } from "./helpers";

test("home mostra loading enquanto a API ainda busca shoppings", async ({ page }) => {
  await page.route("**/api/estacionamentos", async route => {
    await new Promise(resolve => setTimeout(resolve, 1200));
    await route.continue();
  });
  await page.goto("/");
  await expect(page.getByText("Carregando estacionamentos e vagas...")).toBeVisible();
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await expect(page.getByText("Carregando estacionamentos e vagas...")).toHaveCount(0);
});

test("reserva e cancelamento do motorista atualizam KPI e sinos do admin sem reload", async ({ page, request }) => {
  await loginViaApi(page, "admin@smartparking.com", "admin123");
  await page.goto("/dashboard");
  await expect(page.getByRole("button", { name: "Selecionar Shopping QA Centro" })).toBeVisible();
  await page.getByRole("button", { name: "Selecionar Shopping QA Centro" }).click();
  const indicador = page.getByText("Vagas livres", { exact: true }).locator("..").locator(".sp-kpi-valor");
  await expect(indicador).toBeVisible();
  const livresAntes = Number((await indicador.innerText()).trim());
  expect(Number.isFinite(livresAntes)).toBeTruthy();

  const shoppingsResp = await request.get("/api/estacionamentos");
  expect(shoppingsResp.status()).toBe(200);
  const shoppings = (await shoppingsResp.json()) as Array<{ id: string; nome: string }>;
  const centro = shoppings.find(s => s.nome === "Shopping QA Centro");
  expect(centro).toBeTruthy();
  const mapaResp = await request.get(`/api/estacionamentos/${centro!.id}/vagas`);
  expect(mapaResp.status()).toBe(200);
  const mapa = (await mapaResp.json()) as { vagas: Array<{ id: string; status: string; tipo: string }> };
  const vaga = mapa.vagas.find(v => v.status === "livre" && v.tipo === "comum");
  expect(vaga).toBeTruthy();

  const sessao = await request.post(
    process.env.UI_TEST_SESSION_URL || "http://127.0.0.1:8010/__ui_test/session",
    {
      headers: { "X-UI-Test-Token": process.env.UI_TEST_RESET_TOKEN || "smart-parking-ui-local-tests" },
      data: { email: "motorista@smartparking.com", senha: "motor123" },
    },
  );
  expect(sessao.status()).toBe(200);
  const { access_token: tokenMotorista } = await sessao.json() as { access_token: string };
  const headers = { Authorization: `Bearer ${tokenMotorista}` };
  const veiculosResp = await request.get("/auth/veiculos", { headers });
  expect(veiculosResp.status()).toBe(200);
  const veiculos = (await veiculosResp.json()) as Array<{ id: string }>;
  const agora = Date.now();
  const reservaResp = await request.post("/api/reservas", {
    headers,
    data: {
      vaga_id: vaga!.id,
      horario_inicio: new Date(agora + 60_000).toISOString(),
      horario_fim: new Date(agora + 7_200_000).toISOString(),
      ...(veiculos.length > 0 ? { veiculo_id: veiculos[0].id } : {}),
    },
  });
  expect(reservaResp.status(), await reservaResp.text()).toBe(201);
  const reserva = await reservaResp.json() as { id: string };

  // Verifica a revalidação causada pelo feed (1,5s), sem page.reload().
  await expect(indicador).toHaveText(String(livresAntes - 1), { timeout: 12000 });

  const cancelada = await request.delete(`/api/reservas/${reserva.id}`, { headers });
  expect(cancelada.status(), await cancelada.text()).toBe(200);
  await expect(indicador).toHaveText(String(livresAntes), { timeout: 12000 });

  const sino = page.getByRole("button", { name: /Abrir notificações/ }).first();
  await expect(sino).toBeVisible();
  await sino.click();
  await expect(page).toHaveURL(/\/notificacoes$/);
  await expect(page.getByText("Nova reserva", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Reserva cancelada", { exact: true }).first()).toBeVisible();
});
