import { expect, test } from "./helpers";
import { destinoConferidoManaus, urlComoChegar } from "../../src/services/rotasShoppings";

const shoppings = [
  ["Amazonas Shopping", "Djalma Batista, 482"],
  ["Manauara Shopping", "Ypiranga Monteiro, 1300"],
  ["Sumaúma Park Shopping", "Noel Nutels, 1762"],
  ["Ponta Negra Shopping", "Coronel Teixeira, 5705"],
  ["Millennium Shopping", "Djalma Batista, 1661"],
  ["Studio 5 Festival Mall", "Rodrigo Otávio, 3555"],
  ["Shopping Manaus ViaNorte", "Bento Rodrigues, 3541"],
  ["Shopping Phelippe Daou", "Camapuã, 2939"],
] as const;

test("oito shoppings reais abrem Google Maps DIRECTIONS e nunca busca/coordenadas antigas", async () => {
  for (const [nome, trecho] of shoppings) {
    const url = urlComoChegar({
      nome,
      endereco: "Endereço antigo e incorreto",
      latitude: -3.0405,
      longitude: -60.018,
    });
    expect(url, nome).toBeTruthy();
    const destino = new URL(url!);
    expect(destino.protocol).toBe("https:");
    expect(destino.hostname).toBe("www.google.com");
    expect(destino.pathname).toBe("/maps/dir/");
    expect(destino.searchParams.get("api")).toBe("1");
    expect(destino.searchParams.get("travelmode")).toBe("driving");
    expect(destino.searchParams.get("dir_action")).toBe("navigate");
    expect(destino.searchParams.get("destination")).toContain(trecho);
    expect(destino.searchParams.get("destination")).toContain("Manaus - AM");
    expect(destino.searchParams.has("origin")).toBe(false);
    expect(destino.searchParams.has("key")).toBe(false);
  }
});

test("alias legado Shopping Norte aponta ViaNorte, não Camapuã", async () => {
  const real = destinoConferidoManaus("Shopping Norte");
  expect(real?.nomeGoogle).toBe("Shopping Manaus ViaNorte");
  const url = new URL(urlComoChegar({
    nome: "Shopping Norte",
    endereco: "Av. Camapuã, 1480",
    latitude: -3.0474,
    longitude: -59.9876,
  })!);
  expect(url.searchParams.get("destination")).toContain("Bento Rodrigues, 3541");
  expect(url.searchParams.get("destination")).not.toContain("Camapuã");
  expect(url.searchParams.get("destination_place_id")).toBe("ChIJU52AdrUZbJIR185TfEOjAHQ");
});

test("cadastros manuais usam coordenadas válidas ou endereço, jamais zero e NaN", async () => {
  const coords = new URL(urlComoChegar({
    nome: "Shopping de Teste",
    latitude: -3.11,
    longitude: -60.02,
  })!);
  expect(coords.searchParams.get("destination")).toBe("-3.11,-60.02");
  const endereco = new URL(urlComoChegar({
    nome: "Shopping de Teste",
    endereco: "Av. Exemplo, 10 - Manaus - AM",
    latitude: 0,
    longitude: 0,
  })!);
  expect(endereco.searchParams.get("destination")).toContain("Av. Exemplo, 10");
  expect(urlComoChegar({
    nome: "Shopping de Teste",
    latitude: Number.NaN,
    longitude: -60,
  })).toBeNull();
  expect(urlComoChegar(null)).toBeNull();
});

test("botão Como chegar aparece na tela de mapa da V1 web", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Shopping QA Centro").first()).toBeVisible();
  await page.getByRole("button", { name: /Ver Vagas Disponíveis/ }).click();
  const rota = page.getByRole("button", { name: /Como chegar.*Google Maps/ });
  await expect(rota).toBeVisible();
});
