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
  // O split azul do login só existe em desktop real (>= 1024px); em 900px
  // o layout é de coluna única para não sobrepor o formulário.
  if ((page.viewportSize()?.width ?? 0) >= 1024) {
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

/**
 * Sessão real para testes que NÃO estão testando o formulário de login.
 * Evita a corrida de hidratação do React entre jornadas. Respeita HTTP 429,
 * sem desligar o rate limiter e sem engolir 401/403/5xx.
 */
export async function loginViaApi(page: Page, email: string, senha: string) {
  const autenticar = () => page.request.post("/auth/login", {
    data: { email, senha },
  });
  let response = await autenticar();
  if (response.status() === 429) {
    const segundos = Number(response.headers()["retry-after"]);
    const espera = Number.isFinite(segundos) && segundos > 0
      ? Math.min(Math.ceil(segundos) * 1000 + 1200, 65_000)
      : 61_000;
    await new Promise<void>((resolve) => setTimeout(resolve, espera));
    response = await autenticar();
  }
  expect(response.status(), "Autenticação real de QA via API").toBe(200);
  const sessao = (await response.json()) as {
    access_token: string;
    refresh_token: string;
    user: unknown;
  };
  expect(sessao.access_token).toBeTruthy();
  await page.addInitScript(({ access, refresh, user }) => {
    localStorage.setItem("smartparking_access_token", access);
    localStorage.setItem("smartparking_refresh_token", refresh);
    if (user) localStorage.setItem("smartparking_user_cache", JSON.stringify(user));
  }, { access: sessao.access_token, refresh: sessao.refresh_token, user: sessao.user });
}
