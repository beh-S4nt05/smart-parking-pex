"""PR61: sessions are owned, revocable, and refresh tokens are single-use."""
def test_list_and_revoke_only_own_sessions(client, fab):
    user = fab.usuario(senha="senha-sessao123")
    other = fab.usuario(senha="senha-outra123")
    login = client.post("/auth/login", json={"email": user.email, "senha": "senha-sessao123"})
    assert login.status_code == 200, login.text
    tokens = login.json()
    header = {"Authorization": "Bearer " + tokens["access_token"]}
    rows = client.get("/auth/sessoes", headers=header)
    assert rows.status_code == 200
    sid = rows.json()[0]["id"]
    assert rows.json()[0]["ativa"] is True
    other_header = fab.token(other)
    assert client.delete(f"/auth/sessoes/{sid}", headers=other_header).status_code == 404
    assert client.delete(f"/auth/sessoes/{sid}", headers=header).status_code == 204
    assert client.get("/auth/me", headers=header).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_rotation_denies_old_refresh(client, fab):
    user = fab.usuario(senha="senha-rotacao123")
    login = client.post("/auth/login", json={"email": user.email, "senha": "senha-rotacao123"})
    assert login.status_code == 200
    token1 = login.json()["refresh_token"]
    novo = client.post("/auth/refresh", json={"refresh_token": token1})
    assert novo.status_code == 200, novo.text
    token2 = novo.json()["refresh_token"]
    assert token2 != token1
    assert client.post("/auth/refresh", json={"refresh_token": token1}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": token2}).status_code == 401
