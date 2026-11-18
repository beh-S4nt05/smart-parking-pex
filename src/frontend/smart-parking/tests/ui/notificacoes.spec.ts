/** Verifica a central REAL da V1 (API FastAPI, sessão JWT e UI), não um mock de notificações. */
import { expect, login, test } from "./helpers";

test("central não apresenta notificações de outra conta sem autenticação", async ({ page }) => {
  await page.goto("/notificacoes");
  await expect(page.getByText("Entre na sua conta para ver notificações.")).toBeVisible();
  await expect(page.getByText("Central de notificações")).toHaveCount(0);
});

test("motorista abre a central, consulta preferências reais e navega pelo sino", async ({ page }) => {
  await login(page, "motorista@smartparking.com", "motor123");
  await expect(page).toHaveURL(/\/$/);
  await page.getByRole("button", { name: /Abrir notificações/ }).first().click();
  await expect(page).toHaveURL(/\/notificacoes$/);
  await expect(page.getByText("Central de notificações")).toBeVisible();
  await expect(page.getByText("Vagas acompanhadas", { exact: true })).toBeVisible();
  await expect(page.getByText("Preferências", { exact: true })).toBeVisible();
  await expect(page.getByText("Reservas, cancelamentos e expirações")).toBeVisible();
  await expect(page.getByRole("button", { name: "Marcar todas como lidas" })).toBeVisible();
  const token = await page.evaluate(() => localStorage.getItem("smartparking_access_token"));
  expect(token).toBeTruthy();
  const response = await page.request.get("/api/notificacoes/preferencias", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  expect((await response.json()).reservas).toBe(true);
});
