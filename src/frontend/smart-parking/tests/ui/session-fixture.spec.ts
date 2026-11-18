import { expect, test } from "./helpers";

test("sessão QA exige segredo, conta seed e senha válida", async ({ request }) => {
  const url = process.env.UI_TEST_SESSION_URL || "http://127.0.0.1:8010/__ui_test/session";
  const headers = {
    "X-UI-Test-Token": process.env.UI_TEST_RESET_TOKEN || "smart-parking-ui-local-tests",
  };
  const valido = { email: "motorista@smartparking.com", senha: "motor123" };
  const semToken = await request.post(url, { data: valido });
  expect(semToken.status()).toBe(403);

  const desconhecido = await request.post(url, {
    headers, data: { email: "alguem@fora-do-seed.example", senha: "senha" },
  });
  expect(desconhecido.status()).toBe(403);

  const senhaErrada = await request.post(url, {
    headers, data: { email: valido.email, senha: "senha-errada" },
  });
  expect(senhaErrada.status()).toBe(401);

  const resposta = await request.post(url, { headers, data: valido });
  expect(resposta.status()).toBe(200);
  const sessao = await resposta.json();
  expect(sessao.access_token).toBeTruthy();
  expect(sessao.refresh_token).toBeTruthy();
  const me = await request.get("/auth/me", {
    headers: { Authorization: `Bearer ${sessao.access_token}` },
  });
  expect(me.status()).toBe(200);
  expect((await me.json()).email).toBe(valido.email);
});
