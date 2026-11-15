"""Permissões efetivas por papel, verificadas pela API e pelo banco."""

from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import ConfiguracaoPreco, Reserva, TipoUsuario


def test_gestor_admin_e_financeiro_nos_shoppings(client, db, fab):
    proprio, alheio = fab.est(nome="Shopping próprio"), fab.est(nome="Shopping alheio")
    andar_proprio, andar_alheio = fab.andar(proprio), fab.andar(alheio)
    gestor = fab.token(fab.usuario(role=TipoUsuario.GESTOR, est=proprio))
    financeiro = fab.token(fab.usuario(role=TipoUsuario.FINANCEIRO, est=proprio))
    admin = fab.token(fab.usuario(role=TipoUsuario.ADMIN))

    for cabecalho, esperado in ((gestor, [proprio.id]), (financeiro, [proprio.id]), (admin, [proprio.id, alheio.id])):
        resposta = client.get("/api/admin/estacionamentos", headers=cabecalho)
        assert resposta.status_code == 200
        ids = {e["id"] for e in resposta.json()}
        if cabecalho is admin:
            assert set(esperado) <= ids  # a base compartilhada pode ter outros shoppings de testes anteriores
        else:
            assert ids == set(esperado)

    assert client.put(f"/api/admin/estacionamentos/{proprio.id}", json={"nome": "Atualizado"}, headers=gestor).status_code == 200
    db.expire_all()
    assert db.get(type(proprio), proprio.id).nome == "Atualizado"
    assert client.put(f"/api/admin/estacionamentos/{alheio.id}", json={"nome": "Invasão"}, headers=gestor).status_code == 403
    assert client.put(f"/api/admin/estacionamentos/{proprio.id}", json={"taxa_hora": 1}, headers=gestor).status_code == 403
    assert client.post("/api/admin/andares", json={"estacionamento_id": alheio.id, "numero_andar": 2, "capacidade": 3}, headers=gestor).status_code == 403
    assert client.post("/api/admin/vagas/lote", json={"andar_id": andar_alheio.id, "quantidade": 1}, headers=gestor).status_code == 403
    assert client.post("/api/admin/vagas/lote", json={"andar_id": andar_proprio.id, "quantidade": 1}, headers=gestor).status_code == 201
    assert client.put(f"/api/admin/estacionamentos/{proprio.id}", json={"nome": "Financeiro não edita"}, headers=financeiro).status_code == 403
    assert client.put(f"/api/admin/estacionamentos/{alheio.id}", json={"nome": "Admin edita"}, headers=admin).status_code == 200

    preco = {"estacionamento_id": proprio.id, "tipo_vaga": "comum", "valor_hora": 12}
    assert client.post("/api/admin/financeiro/precos", json=preco, headers=gestor).status_code == 403
    assert client.post("/api/admin/financeiro/precos", json=preco, headers=financeiro).status_code == 201
    assert db.query(ConfiguracaoPreco).filter_by(estacionamento_id=proprio.id).one().valor_hora == 12
    assert client.post("/api/admin/financeiro/precos", json={**preco, "estacionamento_id": alheio.id}, headers=financeiro).status_code == 403
    assert client.post("/api/admin/financeiro/precos", json={**preco, "estacionamento_id": alheio.id}, headers=admin).status_code == 201
    assert client.get("/api/admin/eventos", headers=financeiro).status_code == 200
    assert client.get("/api/admin/eventos", params={"estacionamento_id": alheio.id}, headers=financeiro).status_code == 403
    assert client.get("/api/relatorios/fluxo", params={"periodo": "diario", "estacionamento_id": proprio.id}, headers=gestor).status_code == 200
    assert client.get("/api/relatorios/fluxo", params={"periodo": "diario", "estacionamento_id": alheio.id}, headers=gestor).status_code == 403
    assert client.post("/api/admin/financeiro/caixa/abrir", json={"estacionamento_id": proprio.id, "valor_inicial": 0}, headers=gestor).status_code == 403


def test_reserva_e_historico_pertencem_ao_motorista(client, db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    motorista = fab.usuario()
    outro = fab.usuario()
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=est)
    agora = utc_agora()
    dados = {"vaga_id": vaga.id, "horario_inicio": agora.isoformat(), "horario_fim": (agora + timedelta(hours=2)).isoformat()}
    assert client.post("/api/reservas", json=dados, headers=fab.token(gestor)).status_code == 403
    resposta = client.post("/api/reservas", json=dados, headers=fab.token(motorista))
    assert resposta.status_code == 201, resposta.text
    reserva_id = resposta.json()["id"]
    assert db.get(Reserva, reserva_id).usuario_id == motorista.id
    assert client.get("/api/reservas/minhas", headers=fab.token(outro)).json() == []
    assert client.delete(f"/api/reservas/{reserva_id}", headers=fab.token(outro)).status_code == 403
    assert client.delete(f"/api/reservas/{reserva_id}", headers=fab.token(motorista)).status_code == 200
    assert [r["status"] for r in client.get("/api/reservas/minhas", headers=fab.token(motorista)).json()] == ["cancelada"]
