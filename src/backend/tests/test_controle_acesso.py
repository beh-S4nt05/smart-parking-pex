"""Matriz executável de autenticação, RBAC e isolamento entre tenants (BOLA)."""

from datetime import timedelta

import pytest

from core.security import criar_token
from core.timeutils import utc_agora
from models.db_models import (
    FechamentoCaixa,
    Historico,
    Pagamento,
    Reserva,
    StatusPagamento,
    StatusReserva,
    StatusVaga,
    TipoUsuario,
    Usuario,
)


def _sem_vazamento_interno(response):
    texto = response.text.lower()
    assert response.status_code < 500, response.text
    assert "traceback" not in texto
    assert "sqlalchemy" not in texto


@pytest.mark.parametrize(
    ("metodo", "url", "corpo"),
    [
        ("GET", "/auth/me", None),
        ("PUT", "/auth/me", {"nome": "Sem Sessão"}),
        ("PUT", "/auth/senha", {"senha_atual": "antiga123", "nova_senha": "nova123"}),
        ("POST", "/auth/logout", None),
        ("GET", "/api/reservas/minhas", None),
        ("DELETE", "/api/reservas/id-inexistente", None),
        (
            "POST",
            "/api/reservas",
            {
                "vaga_id": "id-inexistente",
                "horario_inicio": "2030-01-01T10:00:00Z",
                "horario_fim": "2030-01-01T12:00:00Z",
            },
        ),
        ("PATCH", "/api/vagas/id-inexistente/status", {"status": "livre"}),
        ("PATCH", "/api/vagas/lote/status", {"vaga_ids": ["id"], "status": "livre"}),
        ("GET", "/api/relatorios/fluxo?periodo=diario", None),
        ("GET", "/api/relatorios/ocupacao?periodo=diario", None),
        ("GET", "/api/relatorios/ocupacao-historica?periodo=diario", None),
        ("GET", "/api/relatorios/rotacao?periodo=diario", None),
        ("GET", "/api/relatorios/fluxo/csv?periodo=diario", None),
        ("GET", "/api/relatorios/financeiro/csv?periodo=diario", None),
        ("GET", "/api/admin/usuarios", None),
        ("GET", "/api/admin/dashboard", None),
        ("GET", "/api/admin/gestor/dashboard", None),
        ("GET", "/api/admin/sensores", None),
        ("GET", "/api/admin/financeiro/resumo?periodo=diario", None),
        ("POST", "/api/admin/financeiro/pagamento/id/confirmar", None),
        ("POST", "/api/admin/financeiro/pagamento/gerar-pix?historico_id=id", None),
    ],
)
def test_rota_protegida_exige_autenticacao(client, metodo, url, corpo):
    response = client.request(metodo, url, json=corpo)
    assert response.status_code == 401, (metodo, url, response.text)
    assert "access_token" not in response.text
    _sem_vazamento_interno(response)


@pytest.mark.parametrize("role", [TipoUsuario.USUARIO, TipoUsuario.GESTOR, TipoUsuario.FINANCEIRO])
@pytest.mark.parametrize(
    ("metodo", "url"),
    [
        ("GET", "/api/admin/usuarios"),
        ("GET", "/api/admin/dashboard"),
        ("GET", "/api/admin/sensores"),
        ("GET", "/api/admin/simulador/sessoes"),
        ("POST", "/api/admin/estacionamentos"),
        ("POST", "/api/admin/vagas"),
        ("PATCH", "/api/admin/usuarios/id/promover-admin"),
    ],
)
def test_admin_global_nao_pode_ser_substituído_por_outro_papel(client, fab, role, metodo, url):
    est = fab.est()
    usuario = fab.usuario(role=role, est=est if role != TipoUsuario.USUARIO else None)
    corpo = None
    if url == "/api/admin/estacionamentos":
        corpo = {"nome": "Tentativa sem privilégio", "total_andares": 1, "total_vagas": 0}
    elif url == "/api/admin/vagas":
        corpo = {"andar_id": "id", "codigo": "X1", "tipo": "comum"}

    response = client.request(metodo, url, json=corpo, headers=fab.token(usuario))

    assert response.status_code == 403, (role, metodo, url, response.text)
    _sem_vazamento_interno(response)


@pytest.mark.parametrize("role", [TipoUsuario.USUARIO, TipoUsuario.FINANCEIRO])
def test_apenas_admin_ou_gestor_operam_status_das_vagas(client, db, fab, role):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    usuario = fab.usuario(role=role, est=est if role == TipoUsuario.FINANCEIRO else None)

    response = client.patch(
        f"/api/vagas/{vaga.id}/status",
        json={"status": "ocupada", "origem": "manual"},
        headers=fab.token(usuario),
    )

    assert response.status_code == 403
    db.expire_all()
    assert db.get(type(vaga), vaga.id).status == StatusVaga.LIVRE


@pytest.mark.parametrize(
    "url",
    [
        "/api/relatorios/fluxo?periodo=diario",
        "/api/relatorios/ocupacao?periodo=diario",
        "/api/relatorios/ocupacao-historica?periodo=diario",
        "/api/relatorios/rotacao?periodo=diario",
        "/api/relatorios/fluxo/csv?periodo=diario",
        "/api/relatorios/financeiro/csv?periodo=diario",
        "/api/admin/financeiro/resumo?periodo=diario",
    ],
)
def test_motorista_nao_lê_relatorios_ou_financeiro_do_painel(client, fab, url):
    response = client.get(url, headers=fab.token(fab.usuario()))
    assert response.status_code == 403
    _sem_vazamento_interno(response)


def test_gestor_não_altera_vagas_de_outro_estacionamento(client, db, fab):
    est_a = fab.est(nome="Tenant A - vagas")
    est_b = fab.est(nome="Tenant B - vagas")
    vaga_a = fab.vaga(fab.andar(est_a))
    vaga_b = fab.vaga(fab.andar(est_b))
    gestor_a = fab.usuario(role=TipoUsuario.GESTOR, est=est_a)
    headers = fab.token(gestor_a)

    unica = client.patch(
        f"/api/vagas/{vaga_b.id}/status",
        json={"status": "ocupada", "origem": "manual"},
        headers=headers,
    )
    lote = client.patch(
        "/api/vagas/lote/status",
        json={"vaga_ids": [vaga_a.id, vaga_b.id], "status": "ocupada", "origem": "manual"},
        headers=headers,
    )

    assert unica.status_code == 403
    assert lote.status_code == 403
    db.expire_all()
    assert db.get(type(vaga_a), vaga_a.id).status == StatusVaga.LIVRE
    assert db.get(type(vaga_b), vaga_b.id).status == StatusVaga.LIVRE

    propria = client.patch(
        f"/api/vagas/{vaga_a.id}/status",
        json={"status": "ocupada", "origem": "manual"},
        headers=headers,
    )
    assert propria.status_code == 200, propria.text


def test_reservas_são_isoladas_por_proprietário(client, db, fab):
    est = fab.est()
    andar = fab.andar(est)
    dono = fab.usuario()
    outro = fab.usuario()
    agora = utc_agora()
    reserva_dono = Reserva(
        usuario_id=dono.id,
        vaga_id=fab.vaga(andar).id,
        horario_inicio=agora + timedelta(minutes=10),
        horario_fim=agora + timedelta(hours=2),
        status=StatusReserva.CONFIRMADA,
    )
    reserva_outro = Reserva(
        usuario_id=outro.id,
        vaga_id=fab.vaga(andar).id,
        horario_inicio=agora + timedelta(minutes=10),
        horario_fim=agora + timedelta(hours=2),
        status=StatusReserva.CONFIRMADA,
    )
    db.add_all([reserva_dono, reserva_outro])
    db.commit()

    lista_dono = client.get("/api/reservas/minhas", headers=fab.token(dono))
    lista_outro = client.get("/api/reservas/minhas", headers=fab.token(outro))

    assert lista_dono.status_code == 200
    assert lista_outro.status_code == 200
    assert {item["id"] for item in lista_dono.json()} == {reserva_dono.id}
    assert {item["id"] for item in lista_outro.json()} == {reserva_outro.id}
    assert client.delete(
        f"/api/reservas/{reserva_outro.id}", headers=fab.token(dono)
    ).status_code == 403
    db.refresh(reserva_outro)
    assert reserva_outro.status == StatusReserva.CONFIRMADA


def test_objetos_financeiros_respeitam_tenant_e_proprietário(client, db, fab):
    est_a = fab.est(nome="Tenant financeiro A")
    est_b = fab.est(nome="Tenant financeiro B")
    financeiro_a = fab.usuario(role=TipoUsuario.FINANCEIRO, est=est_a)
    gestor_a = fab.usuario(role=TipoUsuario.GESTOR, est=est_a)
    dono_b = fab.usuario()
    outro_motorista = fab.usuario()
    vaga_b = fab.vaga(fab.andar(est_b))
    historico = Historico(
        estacionamento_id=est_b.id,
        vaga_id=vaga_b.id,
        usuario_id=dono_b.id,
        entrada_em=utc_agora() - timedelta(hours=1),
    )
    db.add(historico)
    db.flush()
    pagamento = Pagamento(
        historico_id=historico.id,
        estacionamento_id=est_b.id,
        usuario_id=dono_b.id,
        valor_bruto=10,
        valor_total=10,
        metodo_pagamento="pix",
        status_pagamento=StatusPagamento.PENDENTE,
    )
    caixa = FechamentoCaixa(estacionamento_id=est_b.id, usuario_abertura_id=dono_b.id)
    db.add_all([pagamento, caixa])
    db.commit()
    headers = fab.token(financeiro_a)

    chamadas = [
        client.post(
            f"/api/admin/financeiro/calcular-tarifa?historico_id={historico.id}",
            json={},
            headers=headers,
        ),
        client.post(
            "/api/admin/financeiro/pagamento/registrar",
            json={"historico_id": historico.id, "metodo_pagamento": "dinheiro"},
            headers=headers,
        ),
        client.post(
            f"/api/admin/financeiro/pagamento/gerar-pix?historico_id={historico.id}",
            headers=headers,
        ),
        client.post(f"/api/admin/financeiro/pagamento/{pagamento.id}/confirmar", headers=headers),
        client.post(
            f"/api/admin/financeiro/caixa/{caixa.id}/fechar", json={}, headers=headers
        ),
        client.post(
            f"/api/admin/financeiro/calcular-tarifa?historico_id={historico.id}",
            json={},
            headers=fab.token(gestor_a),
        ),
        client.post(
            f"/api/admin/financeiro/pagamento/gerar-pix?historico_id={historico.id}",
            headers=fab.token(outro_motorista),
        ),
    ]

    assert [response.status_code for response in chamadas] == [403] * len(chamadas)
    for response in chamadas:
        _sem_vazamento_interno(response)
    db.expire_all()
    assert db.query(Pagamento).filter(Pagamento.historico_id == historico.id).count() == 1
    assert db.get(Pagamento, pagamento.id).status_pagamento == StatusPagamento.PENDENTE
    assert db.get(FechamentoCaixa, caixa.id).fechado is False


def test_cadastro_público_ignora_escalacao_de_papel_e_desativacao(client, db):
    import uuid

    email = f"mass-assignment-{uuid.uuid4().hex[:10]}@teste.dev"
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "Usuário sem privilégio",
            "email": email,
            "senha": "senha-segura123",
            "role": "admin",
            "is_ativo": False,
            "estacionamento_id": "tenant-injetado",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == TipoUsuario.USUARIO.value
    assert response.json()["is_ativo"] is True
    assert response.json()["estacionamento_id"] is None
    usuario = db.query(Usuario).filter(Usuario.email == email).one()
    assert usuario.role == TipoUsuario.USUARIO.value
    assert usuario.estacionamento_id is None


def test_token_adulterado_refresh_como_access_e_usuario_desativado(client, db, fab):
    usuario = fab.usuario()
    access = criar_token(usuario.id, "access")
    refresh = criar_token(usuario.id, "refresh")

    adulterado = access[:-1] + ("A" if access[-1] != "A" else "B")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {adulterado}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {refresh}"}).status_code == 401

    usuario.is_ativo = False
    db.commit()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 403


def test_relatorio_público_não_expoe_registros_mesmo_com_token_admin(client, fab):
    admin = fab.usuario(role=TipoUsuario.ADMIN)
    response = client.get(
        "/api/relatorios/fluxo/publico?periodo=diario", headers=fab.token(admin)
    )

    assert response.status_code == 200
    assert "registros" not in response.json()
    assert "placa" not in response.text.lower()
    assert "valor_total" not in response.text
