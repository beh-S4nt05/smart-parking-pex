import {
  test as base,
  expect,
  type Page,
} from "@playwright/test";

export const test = base.extend({
  page: async ({ page }, use) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(`JS: ${error.message}`));
    page.on("response", (response) => {
      if (response.status() >= 500) {
        errors.push(`HTTP ${response.status()}: ${response.url()}`);
      }
    });
    await use(page);
    expect(errors, "Nenhum erro de runtime ou resposta 5xx durante a jornada").toEqual([]);
  },
});

export { expect };

// Cada jornada é independente, mas continua exercitando o limiter real. O
// controle só existe no wrapper scripts/ui_backend_server.py, nunca em main:app.
test.beforeEach(async ({ request }) => {
  const response = await request.post(
    process.env.UI_TEST_RESET_URL || "http://127.0.0.1:8010/__ui_test/reset-rate-limit",
    {
      headers: {
        "X-UI-Test-Token": process.env.UI_TEST_RESET_TOKEN || "smart-parking-ui-local-tests",
      },
    },
  );
  expect(response.status(), "Isolamento do rate limiter entre jornadas").toBe(200);
});

export async function gotoLogin(page: Page, url = "/login") {
  await page.goto(url);
  // O primeiro frame vem do pré-render. Espera o ramo responsivo já
  // hidratado para não preencher um input que a reconciliação ainda trocará.
  if ((page.viewportSize()?.width ?? 0) >= 900) {
    await expect(page.getByText("Acesse sua conta para continuar")).toBeVisible();
  } else {
    await expect(page.getByText("Bem-vindo ao Smart Parking")).toBeVisible();
  }
}

export async function login(page: Page, email: string, senha: string) {
  await gotoLogin(page);
  await page.getByLabel("E-mail ou telefone", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(senha);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
}

export async function expectSemOverflowHorizontal(page: Page) {
  const medidas = await page.evaluate(() => ({
    conteudo: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    viewport: window.innerWidth,
  }));
  expect(
    medidas.conteudo,
    `documento com ${medidas.conteudo}px em viewport de ${medidas.viewport}px`,
  ).toBeLessThanOrEqual(medidas.viewport + 1);
}
