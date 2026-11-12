import { login, expect, test } from "./helpers";

// Capturas reais para revisar o layout de cada rota: do celular 4" à TV 23"+.
for (const viewport of [
  { width: 320, height: 700, name: "celular-compacto" },
  { width: 390, height: 844, name: "celular" },
  { width: 768, height: 1024, name: "tablet" },
  { width: 1024, height: 768, name: "notebook" },
  { width: 1440, height: 900, name: "desktop" },
  { width: 2560, height: 1440, name: "tv" },
]) {
  test(`preview das telas em ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);

    const capturar = async (rota: string, nome: string) => {
      await page.goto(rota);
      await page.waitForFunction(() => document.body.innerText.trim().length > 30);
      await page.waitForFunction(
        () => !/Carregando|Validando|Aguarde/i.test(document.body.innerText),
        undefined,
        { timeout: 10_000 },
      );
      if (nome === "simulador-qr") {
        await page.getByText("Shopping QA Centro", { exact: true }).first().click();
        await expect(page.getByText("1º andar")).toBeVisible();
      }
      await page.screenshot({
        path: test.info().outputPath(`preview-${viewport.name}-${nome}.png`),
        fullPage: true,
        animations: "disabled",
      });
    };

    await capturar("/", "inicio");
    await capturar("/explorar", "explorar");

    await login(page, "admin@smartparking.com", "admin123");
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText("Visão geral em tempo real")).toBeVisible();

    for (const [rota, nome] of [
      ["/dashboard", "dashboard"],
      ["/perfil", "perfil"],
      ["/reservas", "reservas"],
      ["/simulador", "simulador"],
      ["/simulador-qr", "simulador-qr"],
    ]) {
      await capturar(rota, nome);
    }
  });
}
