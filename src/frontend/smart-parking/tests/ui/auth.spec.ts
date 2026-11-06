import {
  expect,
  gotoLogin,
  login,
  test,
} from "./helpers";


test("login valida campos, contém SQL injection e motorista não entra no painel", async ({ page }) => {
  await gotoLogin(page);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByText("Informe seu e-mail ou telefone")).toBeVisible();
  await expect(page.getByText("Informe sua senha")).toBeVisible();

  await page.getByLabel("E-mail ou telefone", { exact: true }).fill(
    "admin@smartparking.com' OR '1'='1' --",
  );
  await page.getByLabel("Senha", { exact: true }).fill("qualquer");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByText("E-mail/telefone ou senha incorretos")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("smartparking_access_token"))).toBeNull();

  await page.getByLabel("E-mail ou telefone", { exact: true }).fill("motorista@smartparking.com");
  await page.getByLabel("Senha", { exact: true }).fill("senha-errada");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByText("E-mail/telefone ou senha incorretos")).toBeVisible();

  await page.getByLabel("Senha", { exact: true }).fill("motor123");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Minhas reservas").first()).toBeVisible();

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Visão geral em tempo real")).toHaveCount(0);
});


test("cadastro em duas etapas valida dados e cria sessão de motorista", async ({ page }) => {
  const email = `ui.${Date.now()}@teste.dev`;
  await page.goto("/cadastro");

  await page.getByLabel("Nome completo", { exact: true }).fill("Usuário UI Playwright");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Telefone", { exact: true }).fill("92999998888");
  await page.getByLabel("Senha", { exact: true }).fill("senha-forte123");
  await page.getByLabel("Confirmar senha", { exact: true }).fill("senha-diferente");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await expect(page.getByText("As senhas não coincidem")).toBeVisible();

  await page.getByLabel("Confirmar senha", { exact: true }).fill("senha-forte123");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await expect(page.getByText("Se quiser, cadastre seu veículo agora")).toBeVisible();

  await page.getByLabel(/Modelo do carro/).fill("Onix 1.0");
  await page.getByLabel(/Placa/).fill("XX");
  await page.getByRole("button", { name: "Criar conta", exact: true }).click();
  await expect(page.getByText(/Placa inválida/)).toBeVisible();

  await page.getByLabel(/Placa/).fill("ABC1D23");
  await page.getByRole("checkbox", { name: "Sou pessoa com deficiência (PCD)" }).click();
  await page.getByRole("button", { name: "Criar conta", exact: true }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Minhas reservas").first()).toBeVisible();
  await expect(page.getByText("Usuário").first()).toBeVisible();
});


test("admin acessa dados reais do painel e encerra a sessão", async ({ page }) => {
  await login(page, "admin@smartparking.com", "admin123");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Visão geral em tempo real")).toBeVisible();

  await page.getByText("Usuários", { exact: true }).click();
  await expect(page.getByText("motorista@smartparking.com")).toBeVisible();
  await expect(page.getByRole("button", { name: /Novo usuário/ })).toBeVisible();

  await page.getByText("Estacionamentos", { exact: true }).click();
  await expect(page.getByRole("button", { name: /Novo estacionamento/ })).toBeVisible();
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();

  await page.getByText("Encerrar sessão", { exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("smartparking_access_token"))).toBeNull();
});


test("gestor não recebe ações exclusivas do admin global", async ({ page }) => {
  await login(page, "gestor@smartparking.com", "gestor123");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Simulador QR", { exact: true })).toHaveCount(0);

  await page.getByText("Usuários", { exact: true }).click();
  await expect(
    page.getByText("Gestão de usuários é exclusiva do administrador global."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /Novo usuário/ })).toHaveCount(0);

  await page.getByText("Estacionamentos", { exact: true }).click();
  await expect(page.getByRole("button", { name: /Novo estacionamento/ })).toHaveCount(0);
});


test("financeiro acessa relatórios sem receber ações do admin global", async ({ page }) => {
  await login(page, "financeiro@smartparking.com", "financ123");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Simulador QR", { exact: true })).toHaveCount(0);

  await page.getByText("Relatórios", { exact: true }).click();
  await expect(page.getByText("Financeiro do período", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "CSV financeiro" })).toBeVisible();

  await page.getByText("Usuários", { exact: true }).click();
  await expect(
    page.getByText("Gestão de usuários é exclusiva do administrador global."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /Novo usuário/ })).toHaveCount(0);
});


test("next externo não vira open redirect depois do login", async ({ page }) => {
  await gotoLogin(page, "/login?next=https%3A%2F%2Fevil.example%2Froubo");
  await page.getByLabel("E-mail ou telefone", { exact: true }).fill("admin@smartparking.com");
  await page.getByLabel("Senha", { exact: true }).fill("admin123");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  expect(new URL(page.url()).origin).toBe("http://127.0.0.1:8000");
});
