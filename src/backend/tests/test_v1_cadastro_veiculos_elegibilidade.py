"""Fluxos V1: cadastro com veículo, credencial pendente e vaga compatível."""
from datetime import datetime, timedelta, timezone

from models.db_models import AuditoriaCredencial, CredencialEstacionamento, TipoUsuario, TipoVaga


def _reserva(client, headers, vaga_id, veiculo_id=None):
    ini = datetime.now(timezone.utc) + timedelta(minutes=10)
    return client.post(
        "/api/reservas",
        json={
            "vaga_id": vaga_id,
            "horario_inicio": ini.isoformat(),
            "horario_fim": (ini + timedelta(hours=2)).isoformat(),
            **({"veiculo_id": veiculo_id} if veiculo_id else {}),
        },
        headers=headers,
    )


def test_cadastro_cria_veiculo_e_solicitacao_pcd_pendente(client, db):
    email = f"v1-{datetime.now(timezone.utc).timestamp()}@test.dev"
    cadastro = client.post(
        "/auth/registrar",
        json={
            "nome": "Motorista teste",
            "email": email,
            "senha": "senhasegura123",
            "telefone": "92999999999",
            "beneficio_solicitado": "pcd",
            "is_pcd": False,
            "veiculo": {
                "placa": "ABC1D23",
                "categoria": "carro",
                "motorizacao": "eletrico",
                "modelo": "Carro QA",
            },
        },
    )
    assert cadastro.status_code == 201, cadastro.text
    uid = cadastro.json()["id"]
    login = client.post("/auth/login", json={"email": email, "senha": "senhasegura123"})
    assert login.status_code == 200, login.text
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    veiculos = client.get("/auth/veiculos", headers=h)
    assert veiculos.status_code == 200, veiculos.text
    assert len(veiculos.json()) == 1
    assert veiculos.json()[0]["motorizacao"] == "eletrico"
    assert veiculos.json()[0]["principal"] is True
    cred = client.get("/auth/credenciais", headers=h)
    assert cred.status_code == 200
    assert [(c["tipo"], c["status"]) for c in cred.json()] == [("pcd", "pendente")]
    assert db.query(CredencialEstacionamento).filter_by(usuario_id=uid).count() == 1


def test_solicitacao_idoso_exige_60_anos(client, fab):
    usuario = fab.usuario()
    h = fab.token(usuario)
    r = client.put("/auth/me", json={"data_nascimento": "2000-01-01"}, headers=h)
    assert r.status_code == 200, r.text
    pedido = client.post("/auth/credenciais/solicitar", json={"tipo": "idoso"}, headers=h)
    assert pedido.status_code == 422
    r = client.put("/auth/me", json={"data_nascimento": "1950-01-01"}, headers=h)
    assert r.status_code == 200
    pedido = client.post("/auth/credenciais/solicitar", json={"tipo": "idoso"}, headers=h)
    assert pedido.status_code == 201, pedido.text
    assert pedido.json()["status"] == "pendente"


def test_credencial_aprovada_por_admin_com_auditoria_habilita_pcd(client, db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est), codigo="PCD", tipo=TipoVaga.PCD)
    usuario = fab.usuario()
    admin = fab.usuario(role=TipoUsuario.ADMIN)
    usuario.is_pcd = True  # legado não é autorização
    db.commit()
    user_headers = fab.token(usuario)
    admin_headers = fab.token(admin)
    assert _reserva(client, user_headers, vaga.id).status_code == 403

    pedido = client.post("/auth/credenciais/solicitar", json={"tipo": "pcd"}, headers=user_headers)
    assert pedido.status_code == 201
    cid = pedido.json()["id"]
    assert _reserva(client, user_headers, vaga.id).status_code == 403

    tentativa = client.post(
        f"/api/admin/credenciais/{cid}/avaliar",
        json={
            "decisao": "aprovado", "justificativa": "Credencial física apresentada",
            "metodo_verificacao": "conferencia_presencial", "referencia_oficial": "cred-001",
        },
        headers=user_headers,
    )
    assert tentativa.status_code == 403
    decisao = client.post(
        f"/api/admin/credenciais/{cid}/avaliar",
        json={
            "decisao": "aprovado", "justificativa": "Credencial física apresentada",
            "metodo_verificacao": "conferencia_presencial", "referencia_oficial": "cred-001",
        },
        headers=admin_headers,
    )
    assert decisao.status_code == 200, decisao.text
    assert _reserva(client, user_headers, vaga.id).status_code == 201
    auditorias = db.query(AuditoriaCredencial).filter_by(credencial_id=cid).all()
    assert len(auditorias) == 1
    assert auditorias[0].acao == "aprovado"
    cred = db.get(CredencialEstacionamento, cid)
    assert len(cred.referencia_hash) == 64
    assert cred.referencia_hash != "cred-001"


def test_veiculo_de_outro_usuario_nao_pode_ser_usado_em_reserva(client, fab):
    est = fab.est()
    comum = fab.vaga(fab.andar(est), tipo=TipoVaga.COMUM)
    dono = fab.usuario()
    outro = fab.usuario()
    criacao = client.post("/auth/veiculos", json={
        "placa": "ABC1D23", "categoria": "carro", "motorizacao": "combustao"
    }, headers=fab.token(dono))
    assert criacao.status_code == 201, criacao.text
    vid = criacao.json()["id"]
    assert _reserva(client, fab.token(outro), comum.id, vid).status_code == 403


def test_moto_e_eletrico_sao_dimensionados_independentemente(client, db, fab):
    est = fab.est()
    andar = fab.andar(est)
    vaga_moto = fab.vaga(andar, codigo="MOTO", tipo=TipoVaga.MOTO)
    vaga_carro_ev = fab.vaga(andar, codigo="EV", tipo=TipoVaga.ELETRICO)
    usuario = fab.usuario()
    h = fab.token(usuario)
    moto = client.post("/auth/veiculos", json={
        "placa": "MOT1A23", "categoria": "moto", "motorizacao": "eletrico"
    }, headers=h).json()["id"]
    carro = client.post("/auth/veiculos", json={
        "placa": "CAR1A23", "categoria": "carro", "motorizacao": "eletrico"
    }, headers=h).json()["id"]
    assert _reserva(client, h, vaga_moto.id, carro).status_code == 422
    assert _reserva(client, h, vaga_carro_ev.id, moto).status_code == 422
    assert _reserva(client, h, vaga_moto.id, moto).status_code == 201
    assert _reserva(client, h, vaga_carro_ev.id, carro).status_code == 201


def test_credencial_expirada_nao_autoriza_e_pode_ser_renovada(client, db, fab):
    from datetime import date

    est = fab.est()
    vaga = fab.vaga(fab.andar(est), codigo="PCD-VENCIDA", tipo=TipoVaga.PCD)
    u = fab.usuario()
    db.add(CredencialEstacionamento(
        usuario_id=u.id, tipo="pcd", status="aprovado", validade=date(2020, 1, 1)
    ))
    db.commit()
    h = fab.token(u)
    assert _reserva(client, h, vaga.id).status_code == 403
    lista = client.get("/auth/credenciais", headers=h)
    assert lista.status_code == 200
    assert lista.json()[0]["status"] == "expirado"
    pedido = client.post("/auth/credenciais/solicitar", json={"tipo": "pcd"}, headers=h)
    assert pedido.status_code == 201, pedido.text
    assert pedido.json()["status"] == "pendente"


def _veiculo(client, headers, placa, categoria="carro", motorizacao="combustao", modelo=None):
    return client.post("/auth/veiculos", json={
        "placa": placa, "categoria": categoria,
        "motorizacao": motorizacao, "modelo": modelo,
    }, headers=headers)


def test_garagem_multiplos_veiculos_edicao_principal_e_restauracao(client, db, fab):
    usuario = fab.usuario()
    h = fab.token(usuario)

    a = _veiculo(client, h, "ABC1D23")
    b = _veiculo(client, h, "DEF2E34", categoria="moto", motorizacao="eletrico")
    assert a.status_code == 201, a.text
    assert b.status_code == 201, b.text
    id_a, id_b = a.json()["id"], b.json()["id"]
    assert a.json()["principal"] is True
    assert b.json()["principal"] is False

    trocado = client.put(f"/auth/veiculos/{id_b}/principal", headers=h)
    assert trocado.status_code == 200, trocado.text
    assert trocado.json()["principal"] is True
    lista = client.get("/auth/veiculos", headers=h).json()
    assert [v["id"] for v in lista] == [id_b, id_a]
    assert [v["principal"] for v in lista] == [True, False]
    db.refresh(usuario)
    assert usuario.placa_veiculo == "DEF2E34"

    atualizado = client.put(f"/auth/veiculos/{id_b}", json={
        "placa": "GHI3F45", "categoria": "carro",
        "motorizacao": "hibrido", "modelo": "Sedan atualizado",
    }, headers=h)
    assert atualizado.status_code == 200, atualizado.text
    assert atualizado.json()["placa"] == "GHI3F45"
    assert atualizado.json()["motorizacao"] == "hibrido"
    db.refresh(usuario)
    assert usuario.placa_veiculo == "GHI3F45"

    duplicado = client.put(f"/auth/veiculos/{id_b}", json={
        "placa": "ABC1D23", "categoria": "carro", "motorizacao": "combustao",
    }, headers=h)
    assert duplicado.status_code == 409

    remove = client.delete(f"/auth/veiculos/{id_b}", headers=h)
    assert remove.status_code == 204, remove.text
    lista = client.get("/auth/veiculos", headers=h).json()
    assert len(lista) == 1
    assert lista[0]["id"] == id_a
    assert lista[0]["principal"] is True
    db.refresh(usuario)
    assert usuario.placa_veiculo == "ABC1D23"

    restaurado = _veiculo(client, h, "GHI3F45", "moto", "eletrico")
    assert restaurado.status_code == 201, restaurado.text
    assert restaurado.json()["id"] == id_b
    assert restaurado.json()["principal"] is False


def test_garagem_nao_permita_alterar_veiculos_de_outra_conta(client, fab):
    dono = fab.usuario()
    outro = fab.usuario()
    h_dono, h_outro = fab.token(dono), fab.token(outro)
    veiculo = _veiculo(client, h_dono, "JKL4G56").json()
    vid = veiculo["id"]
    atualizacao = client.put(f"/auth/veiculos/{vid}", json={
        "placa": "MNO5H67", "categoria": "carro", "motorizacao": "eletrico",
    }, headers=h_outro)
    assert atualizacao.status_code == 404
    assert client.put(f"/auth/veiculos/{vid}/principal", headers=h_outro).status_code == 404
    assert client.delete(f"/auth/veiculos/{vid}", headers=h_outro).status_code == 404
    assert client.get("/auth/veiculos", headers=h_outro).json() == []
    assert client.get("/auth/veiculos", headers=h_dono).json()[0]["placa"] == "JKL4G56"


def test_reserva_de_veiculo_escolhido_protege_edicao_e_exibe_placa(client, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est), codigo="CAR-G1", tipo=TipoVaga.COMUM)
    usuario = fab.usuario()
    h = fab.token(usuario)
    v1 = _veiculo(client, h, "PQR6J78")
    assert v1.status_code == 201, v1.text
    vid = v1.json()["id"]
    assert _reserva(client, h, vaga.id).status_code == 422
    reserva = _reserva(client, h, vaga.id, vid)
    assert reserva.status_code == 201, reserva.text
    assert reserva.json()["veiculo"]["placa"] == "PQR6J78"
    rid = reserva.json()["id"]

    alterar = client.put(f"/auth/veiculos/{vid}", json={
        "placa": "STU7K89", "categoria": "moto", "motorizacao": "eletrico",
    }, headers=h)
    assert alterar.status_code == 409
    assert client.delete(f"/auth/veiculos/{vid}", headers=h).status_code == 409

    modelo = client.put(f"/auth/veiculos/{vid}", json={
        "placa": "PQR6J78", "categoria": "carro",
        "motorizacao": "combustao", "modelo": "Modelo revisado",
    }, headers=h)
    assert modelo.status_code == 200, modelo.text

    historico = client.get("/api/reservas/minhas", headers=h)
    assert historico.status_code == 200, historico.text
    assert historico.json()[0]["veiculo"]["placa"] == "PQR6J78"
    assert historico.json()[0]["veiculo_id"] == vid

    assert client.delete(f"/api/reservas/{rid}", headers=h).status_code == 200
    assert client.delete(f"/auth/veiculos/{vid}", headers=h).status_code == 204
    hist_pos_remocao = client.get("/api/reservas/minhas", headers=h)
    assert hist_pos_remocao.json()[0]["veiculo"]["placa"] == "PQR6J78"
