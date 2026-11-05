import { expect, login, test } from "./helpers";

test("XSS armazenado no perfil é renderizado como texto e não executa", async ({ page }) => {
  const payload = "<svg/onload=window.__smartParkingXss=true>";
  await login(page, "motorista@smartparking.com", "motor123");
  await expect(page).toHaveURL(/\/$/);

  try {
    await page.goto("/perfil");
    const nome = page.getByLabel("Nome completo", { exact: true });
    await expect(nome).toHaveValue("Motorista QA");
    await nome.fill(payload);
    const respostaSalva = page.waitForResponse(
      (response) => response.url().endsWith("/auth/me") && response.request().method() === "PUT",
    );
    const dialogoSalvo = page.waitForEvent("dialog");
    await page.getByRole("button", { name: "Salvar alterações", exact: true }).click();
    expect((await respostaSalva).status()).toBe(200);
    await (await dialogoSalvo).accept();

    // Prova que o valor voltou do banco, não apenas do estado React da tela.
    await page.reload();
    await expect(page.getByText(payload, { exact: true }).first()).toBeVisible();
    await expect(page.locator("[onload], [onerror]")).toHaveCount(0);
    expect(
      await page.evaluate(() =>
        (window as unknown as Record<string, unknown>).__smartParkingXss,
      ),
    ).toBeUndefined();
  } finally {
    const token = await page.evaluate(() => localStorage.getItem("smartparking_access_token"));
    if (token) {
      const restaurado = await page.request.put("/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
        data: { nome: "Motorista QA" },
      });
      expect(restaurado.status()).toBe(200);
    }
  }
});
