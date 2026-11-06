import {
  expect,
  expectSemOverflowHorizontal,
  login,
  test,
} from "./helpers";


test("motorista reserva e cancela pela UI e a vaga volta a ficar livre na API", async ({ page }) => {
  const dialogs: string[] = [];
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.accept();
  });

  await login(page, "motorista@smartparking.com", "motor123");
  await expect(page).toHaveURL(/\/$/);

  const lista = await page.request.get("/api/estacionamentos");
  expect(lista.ok()).toBeTruthy();
  const estacionamentos = (await lista.json()) as Array<{ id: string; nome: string }>;
  const centro = estacionamentos.find((item) => item.nome === "Shopping QA Centro");
  if (!centro) throw new Error("Shopping QA Centro ausente no seed de UI");

  await page.goto(`/shopping/${centro.id}`);
  await page.getByRole("button", { name: "Vaga A-02 — livre" }).click();
  await page.getByRole("button", { name: "Reservar por 2h", exact: true }).click();

  await expect(page).toHaveURL(/\/reservas$/);
  await expect(page.getByText(/Vaga A-02/)).toBeVisible();
  await expect(page.getByText("Confirmada", { exact: true })).toBeVisible();
  expect(dialogs.some((message) => message.includes("A-02 reservada"))).toBeTruthy();

  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(page.getByText("Cancelada", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancelar", exact: true })).toHaveCount(0);
  expect(dialogs.some((message) => message.includes("voltou a ficar livre"))).toBeTruthy();

  const mapa = await page.request.get(`/api/estacionamentos/${centro.id}/vagas`);
  expect(mapa.ok()).toBeTruthy();
  const dados = (await mapa.json()) as {
    vagas: Array<{ codigo: string; status: string }>;
  };
  const a02 = dados.vagas.find((vaga) => vaga.codigo === "A-02");
  expect(a02?.status).toBe("livre");
  await expectSemOverflowHorizontal(page);
});
