"""Regras de vínculo usuário ↔ shopping (tenant isolation).

- Gestor pode ter VÁRIOS shoppings e só enxerga os seus.
- Financeiro tem exatamente UM shopping; no máximo UMA conta financeira
  por shopping (409 com mensagem clara).
- Admin global vê todos, mas ninguém do painel vê shopping alheio — nem
  pelas rotas públicas de vitrine/mapa (BOLA fechado).
"""

from models.db_models import TipoUsuario, Usuario, usuario_estacionamentos


def _headers(db, fab):
    # Admin criado POR TESTE: o bootstrap padrão pode ter sido apagado por
    # testes de exclusão que rodaram antes, então não depender da ordem.
    return fab.token(fab.usuario(role=TipoUsuario.ADMIN))


def _vincular(db, usuario, *estacionamentos):
    for est in estacionamentos:
        db.execute(
            usuario_estacionamentos.insert().values(
                usuario_id=usuario.id, estacionamento_id=est.id
            )
        )
    db.commit()


def test_gestor_com_varios_shoppings_ve_apenas_os_seus(client, db, fab):
    a, b, c = fab.est(nome="Shop A"), fab.est(nome="Shop B"), fab.est(nome="Shop C")
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=a)
    _vincular(db, gestor, a, b)
    h = fab.token(gestor)

    r = client.get("/api/estacionamentos", headers=h)
    assert r.status_code == 200
    assert {e["nome"] for e in r.json()} == {"Shop A", "Shop B"}

    rp = client.get("/api/admin/estacionamentos", headers=h)
    assert rp.status_code == 200
    assert {e["nome"] for e in rp.json()} == {"Shop A", "Shop B"}

    # dados gerenciais do segundo vínculo: permitido
    assert client.get("/api/admin/eventos", params={"estacionamento_id": b.id}, headers=h).status_code == 200
    # shopping de terceiro: 403, não "lista vazia"
    assert client.get("/api/admin/eventos", params={"estacionamento_id": c.id}, headers=h).status_code == 403
    # mapa público de shopping alheio também é bloqueado para papel de painel
    assert client.get(f"/api/estacionamentos/{c.id}/vagas", headers=h).status_code == 403
    # ...e o do próprio continua acessível
    assert client.get(f"/api/estacionamentos/{b.id}/vagas", headers=h).status_code == 200


def test_financeiro_tem_apenas_um_shopping(client, db, fab):
    a, b = fab.est(nome="F-A"), fab.est(nome="F-B")
    fin = fab.usuario(role=TipoUsuario.FINANCEIRO, est=a)
    _vincular(db, fin, a)
    h = fab.token(fin)

    r = client.get("/api/estacionamentos", headers=h)
    assert r.status_code == 200
    assert [e["nome"] for e in r.json()] == ["F-A"]

    # /auth/me expõe a lista de vínculos para a UI travar o seletor
    me = client.get("/auth/me", headers=h)
    assert me.status_code == 200
    assert me.json()["estacionamento_ids"] == [a.id]

    assert client.get(f"/api/estacionamentos/{b.id}/vagas", headers=h).status_code == 403


def test_admin_global_ve_todos_os_shoppings(client, db, fab):
    fab.est(nome="Shop A")
    fab.est(nome="Shop B")
    h = _headers(db, fab)
    nomes = {e["nome"] for e in client.get("/api/admin/estacionamentos", headers=h).json()}
    assert {"Shop A", "Shop B"} <= nomes


def test_anonimo_e_motorista_continuam_vendo_vitrine_completa(client, db, fab):
    fab.est(nome="Shop A")
    fab.est(nome="Shop B")
    assert len(client.get("/api/estacionamentos").json()) >= 2
    motorista = fab.usuario(role=TipoUsuario.USUARIO)
    nomes = {e["nome"] for e in client.get("/api/estacionamentos", headers=fab.token(motorista)).json()}
    assert {"Shop A", "Shop B"} <= nomes


def test_no_maximo_um_financeiro_por_shopping(client, db, fab):
    a, b = fab.est(nome="U-A"), fab.est(nome="U-B")
    fab.usuario(role=TipoUsuario.FINANCEIRO, est=a)
    h = _headers(db, fab)

    base = {"nome": "Outro Financeiro", "senha": "senha123", "role": "financeiro"}
    r = client.post(
        "/api/admin/usuarios",
        json={**base, "email": "outro@teste.dev", "estacionamento_id": a.id},
        headers=h,
    )
    assert r.status_code == 409
    assert "já possui" in r.json()["detail"].lower()

    # shopping diferente: permitido
    ok = client.post(
        "/api/admin/usuarios",
        json={**base, "email": "outro2@teste.dev", "estacionamento_id": b.id},
        headers=h,
    )
    assert ok.status_code == 201, ok.text

    # editar um gestor para financeiro do shopping já ocupado: 409
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=b)
    edit = client.put(
        f"/api/admin/usuarios/{gestor.id}",
        json={"role": "financeiro", "estacionamento_id": a.id, "estacionamento_ids": [a.id]},
        headers=h,
    )
    assert edit.status_code == 409


def test_financeiro_nao_aceita_lista_de_shoppings(client, db, fab):
    a, b = fab.est(nome="L-A"), fab.est(nome="L-B")
    h = _headers(db, fab)
    r = client.post(
        "/api/admin/usuarios",
        json={
            "nome": "Financeiro Multi", "email": "multi@teste.dev",
            "senha": "senha123", "role": "financeiro",
            "estacionamento_id": a.id, "estacionamento_ids": [a.id, b.id],
        },
        headers=h,
    )
    assert r.status_code == 400
    assert "uma conta" in r.json()["detail"].lower()


def test_criar_gestor_com_varios_vinculos(client, db, fab):
    a, b = fab.est(nome="G-A"), fab.est(nome="G-B")
    h = _headers(db, fab)
    r = client.post(
        "/api/admin/usuarios",
        json={
            "nome": "Gestor Multi", "email": "gestormulti@teste.dev",
            "senha": "senha123", "role": "gestor",
            "estacionamento_id": a.id, "estacionamento_ids": [a.id, b.id],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert set(r.json()["estacionamento_ids"]) == {a.id, b.id}

    gestor = db.query(Usuario).filter(Usuario.email == "gestormulti@teste.dev").first()
    assert client.get("/auth/me", headers=fab.token(gestor)).json()["estacionamento_ids"] == [a.id, b.id]


def test_atualizar_vinculos_do_gestor(client, db, fab):
    a, b, c = fab.est(nome="E-A"), fab.est(nome="E-B"), fab.est(nome="E-C")
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=a)
    _vincular(db, gestor, a)
    h = _headers(db, fab)

    r = client.put(
        f"/api/admin/usuarios/{gestor.id}",
        json={"estacionamento_id": b.id, "estacionamento_ids": [b.id, c.id]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estacionamento_id"] == b.id
    assert set(r.json()["estacionamento_ids"]) == {b.id, c.id}
    assert client.get("/api/admin/eventos", params={"estacionamento_id": a.id}, headers=fab.token(gestor)).status_code == 403


def test_admin_nao_remove_vinculo_sem_fornecer_nova_lista(client, db, fab):
    """O guard antigo (400) continua valendo com a N:N."""
    a = fab.est(nome="R-A")
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=a)
    _vincular(db, gestor, a)
    h = _headers(db, fab)
    r = client.put(
        f"/api/admin/usuarios/{gestor.id}",
        json={"estacionamento_id": None}, headers=h,
    )
    assert r.status_code == 400
    db.refresh(gestor)
    assert gestor.estacionamento_id == a.id


def test_excluir_shopping_promove_outro_vinculo_do_gestor(client, db, fab):
    a, b = fab.est(nome="D-A"), fab.est(nome="D-B")
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=a)
    _vincular(db, gestor, a, b)
    h = _headers(db, fab)

    r = client.delete(f"/api/admin/estacionamentos/{a.id}", headers=h)
    assert r.status_code == 200, r.text
    db.expire_all()
    sobrevivente = db.get(Usuario, gestor.id)
    assert sobrevivente is not None, "gestor com outro vínculo não pode ser apagado"
    assert sobrevivente.estacionamento_id == b.id


def test_relatorio_de_shopping_alheio_e_bloqueado(client, db, fab):
    a, b = fab.est(nome="Q-A"), fab.est(nome="Q-B")
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=a)
    _vincular(db, gestor, a)
    h = fab.token(gestor)
    assert client.get("/api/relatorios/fluxo", params={"periodo": "diario", "estacionamento_id": b.id}, headers=h).status_code == 403
    assert client.get("/api/relatorios/fluxo", params={"periodo": "diario", "estacionamento_id": a.id}, headers=h).status_code == 200
