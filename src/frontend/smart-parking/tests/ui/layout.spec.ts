/**
 * Auditoria de layout/UI em runtime (rod.14).
 *
 * Jornadas functional (auth/public/quality/...) verificam COMPORTAMENTO.
 * Este spec verifica a FORMA em que a UI chega ao usuário: nenhuma rota pode
 * estourar a viewport, ter elementos fora de posição, botões com menos de
 * 44px, texto com contraste abaixo do AA, botão sem transição ou animação
 * inline no primeiro frame. Roda em 7 viewports, de 360px a 1920px.
 */
import type { Page } from "@playwright/test";
import { expect, login, test } from "./helpers";

const VIEWPORTS = [
  { width: 360, height: 740, nome: "mobile-360" },
  { width: 390, height: 844, nome: "mobile-390" },
  { width: 768, height: 1024, nome: "tablet-768" },
  { width: 900, height: 900, nome: "tablet-900" },
  { width: 1024, height: 768, nome: "desktop-1024" },
  { width: 1440, height: 900, nome: "desktop-1440" },
  { width: 1920, height: 1080, nome: "desktop-1920" },
] as const;

const AUDITORIA = () => {
  const parse = (s: string) => {
    const m = String(s || "").match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  type Cor = { r: number; g: number; b: number; a: number };
  const compor = (f: Cor, b: Cor): Cor => ({
    r: f.r * f.a + b.r * (1 - f.a),
    g: f.g * f.a + b.g * (1 - f.a),
    b: f.b * f.a + b.b * (1 - f.a),
    a: 1,
  });
  const fundo = (el: Element): Cor => {
    const pilha: Cor[] = [];
    let n: Element | null = el;
    while (n) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) pilha.push(c);
      if (c && c.a >= 0.999) break;
      n = n.parentElement;
    }
    let base: Cor = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = pilha.length - 1; i >= 0; i--) base = compor(pilha[i], base);
    return base;
  };
  const lum = (c: Cor) => {
    const f = (x: number) => {
      const v = x / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const razao = (a: Cor, b: Cor) => {
    const l1 = lum(a);
    const l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const visivel = (el: Element) => {
    const c = getComputedStyle(el);
    if (c.display === "none" || c.visibility === "hidden" || parseFloat(c.opacity) < 0.05)
      return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const direto = (el: Element) =>
    Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent?.trim() ?? "")
      .join(" ")
      .trim();
  const folhaTexto = (el: Element) => {
    if (direto(el)) return el;
    for (const f of Array.from(el.querySelectorAll("*"))) if (direto(f) && visivel(f)) return f;
    return el;
  };
  const corte = (s: string, n = 42) => (s || "").slice(0, n);

  const largura = window.innerWidth;
  const docLargura = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  const interativos = Array.from(document.querySelectorAll('button,a,[role="button"]')).filter(visivel);
  const fora: unknown[] = [];
  const alvos: unknown[] = [];
  const contraste: unknown[] = [];
  const semTransicao: string[] = [];
  const invisiveis: string[] = [];

  for (const el of interativos) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const nome = corte(el.getAttribute("aria-label") || el.getAttribute("placeholder") || direto(el) || el.textContent || "");
    const folha = folhaTexto(el);
    const cf = getComputedStyle(folha);
    const bg = fundo(folha);
    const fg = parse(cf.color) || { r: 0, g: 0, b: 0, a: 1 };
    const ratio = razao(compor(fg, bg), bg);
    const fs = parseFloat(cf.fontSize);
    const fw = parseInt(cf.fontWeight) || 400;
    const limite = fs >= 24 || (fs >= 18.66 && fw >= 700) ? 3 : 4.5;
    if (r.width < 43.5 || r.height < 43.5)
      alvos.push({ nome, w: Math.round(r.width), h: Math.round(r.height) });
    if (ratio < limite - 0.01)
      contraste.push({ nome, ratio: +ratio.toFixed(2), cor: cf.color, fs });
    if (cs.transitionDuration === "0s" || cs.transitionDuration === "") semTransicao.push(nome);
    if (parseFloat(cs.opacity) < 0.05) invisiveis.push(nome);
    if (r.right > largura + 1.5 || r.left < -1.5)
      fora.push({ nome, left: Math.round(r.left), right: Math.round(r.right) });
  }

  const textos = Array.from(
    document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,span,label,div,li,td,th"),
  ).filter(visivel);
  for (const el of textos) {
    const t = direto(el);
    if (!t || t.length < 2) continue;
    const cs = getComputedStyle(el);
    const bg = fundo(el);
    const fg = parse(cs.color);
    if (!fg) continue;
    const ratio = razao(compor(fg, bg), bg);
    const fs = parseFloat(cs.fontSize);
    const fw = parseInt(cs.fontWeight) || 400;
    const limite = fs >= 24 || (fs >= 18.66 && fw >= 700) ? 3 : 4.5;
    if (ratio < limite - 0.01)
      contraste.push({ nome: corte(t), ratio: +ratio.toFixed(2), cor: cs.color, fs });
  }

  const opacityZero = Array.from(document.querySelectorAll("[style]")).filter((e) =>
    /opacity:\s*0(?:\s|;|$)/.test(e.getAttribute("style") || ""),
  ).length;
  const corpo = document.body.innerText || "";
  return {
    overflow: docLargura > largura + 1,
    docLargura,
    largura,
    fora,
    alvos,
    contraste,
    semTransicao,
    invisiveis,
    opacityZero,
    erroReact: /Something went wrong|Unexpected Application Error/i.test(corpo),
    corpoVazio: corpo.trim().length < 20,
  };
};

async function resetarLimiter(page: Page) {
  const resposta = await page.request.post(
    process.env.UI_TEST_RESET_URL || "http://127.0.0.1:8010/__ui_test/reset-rate-limit",
    {
      headers: {
        "X-UI-Test-Token": process.env.UI_TEST_RESET_TOKEN || "smart-parking-ui-local-tests",
      },
    },
  );
  expect(resposta.status(), "reset do rate limiter entre navegações").toBe(200);
}

async function auditar(page: Page, rota: string, viewport: string) {
  await page.waitForFunction(() => document.body.innerText.trim().length > 30);
  await page.waitForFunction(
    () => !/Carregando|Validando|Aguarde/i.test(document.body.innerText),
    undefined,
    { timeout: 10_000 },
  );
  const d = await page.evaluate(AUDITORIA);
  const ctx = `${rota} @ ${viewport}`;
  expect(d.overflow, `${ctx}: documento ${d.docLargura}px em viewport ${d.largura}px`).toBe(false);
  expect(d.fora, `${ctx}: elementos interativos fora da viewport`).toEqual([]);
  expect(d.alvos, `${ctx}: alvos de toque menores que 44px`).toEqual([]);
  expect(d.contraste, `${ctx}: texto com contraste abaixo do AA`).toEqual([]);
  expect(d.semTransicao, `${ctx}: botões/links sem transição`).toEqual([]);
  expect(d.invisiveis, `${ctx}: botões invisíveis`).toEqual([]);
  expect(d.opacityZero, `${ctx}: animação inline no primeiro frame`).toBe(0);
  expect(d.erroReact, `${ctx}: tela de erro React`).toBe(false);
  expect(d.corpoVazio, `${ctx}: tela vazia`).toBe(false);
}

for (const vp of VIEWPORTS) {
  test(`layout, cores, estados e botões em todas as rotas @ ${vp.nome}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    const lista = await page.request.get("/api/estacionamentos");
    const estacionamentos = (await lista.json()) as Array<{ id: string }>;
    const shoppingId = estacionamentos[0]?.id;
    expect(shoppingId, "seed de estacionamentos disponível").toBeTruthy();

    const publicas = [
      "/",
      "/login",
      "/cadastro",
      "/explorar",
      `/shopping/${shoppingId}`,
      "/rota-inexistente",
    ];
    for (const rota of publicas) {
      await resetarLimiter(page);
      await page.goto(rota);
      await auditar(page, rota, vp.nome);
    }

    await login(page, "admin@smartparking.com", "admin123");
    await expect(page).not.toHaveURL(/\/login$/);
    for (const rota of ["/dashboard", "/perfil", "/reservas", "/simulador", "/simulador-qr"]) {
      await resetarLimiter(page);
      await page.goto(rota);
      await auditar(page, rota, vp.nome);
    }
  });
}

test("404 próprio explica o erro, quebra a URL e oferece ações de 44px", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto("/rota-inexistente");
  await expect(page.getByText("Página não encontrada")).toBeVisible();
  await expect(page.getByText(/O endereço que você abriu não existe/)).toBeVisible();
  for (const nome of ["Voltar ao Início", "Explorar shoppings"]) {
    const botao = page.getByRole("button", { name: nome, exact: true });
    await expect(botao).toBeVisible();
    const caixa = await botao.boundingBox();
    expect(caixa?.width).toBeGreaterThanOrEqual(44);
    expect(caixa?.height).toBeGreaterThanOrEqual(44);
  }
  const medidas = await page.evaluate(() => ({
    doc: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    vp: window.innerWidth,
  }));
  expect(medidas.doc).toBeLessThanOrEqual(medidas.vp + 1);
  await page.getByRole("button", { name: "Voltar ao Início", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("menu compacto do header abre, é acessível e fecha com Escape", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await page.goto("/");
  const menu = page.locator('[id="menu-toggle"]');
  await expect(menu).toBeVisible();
  await expect(menu).toHaveAttribute("aria-label", "Abrir menu de navegação");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  const painel = page.getByRole("menu", { name: "Menu de navegação" });
  await expect(painel).toBeVisible();
  expect(await painel.evaluate((el) => getComputedStyle(el).position)).toBe("absolute");
  await expect(painel.getByRole("link", { name: "Reservar Vaga" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(painel).toHaveCount(0);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
});
