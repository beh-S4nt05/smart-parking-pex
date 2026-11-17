import { expect, test } from "./helpers";

test("XSS armazenado no perfil é renderizado como texto e não executa", async ({ page }) => {
  const payload = "<svg/onload=window.__smartParkingXss=true>";

  // Testa XSS, não o formulário de login (coberto em auth.spec.ts).
  // A sessão é obtida da API REAL do Playwright, depois injetada ANTES do
  // bootstrap do React, evitando corrida de hidratação do login entre testes.
  const respostaLogin = await page.request.post("/auth/login", {
    data: { email: "motorista@smartparking.com", senha: "motor123" },
  });
  expect(respostaLogin.status(), "Login real do usuário QA").toBe(200);
  const sessao = (await respostaLogin.json()) as {
    access_token: string;
    refresh_token: string;
    user: unknown;
  };
  expect(sessao.access_token).toBeTruthy();
  await page.addInitScript(({ acesso, refresh, usuario }) => {
    localStorage.setItem("smartparking_access_token", acesso);
    localStorage.setItem("smartparking_refresh_token", refresh);
    if (usuario) {
      localStorage.setItem("smartparking_user_cache", JSON.stringify(usuario));
    }
  }, {
    acesso: sessao.access_token,
    refresh: sessao.refresh_token,
    usuario: sessao.user,
  });

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
