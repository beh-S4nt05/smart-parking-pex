"""Regressão da rodada 4 — exclusões sem órfão e guarda anti-lockout.

Cobre os buracos achados na auditoria do grafo de exclusão:
1. DELETE estacionamento purga SENSORES + EVENTOS (sem relationship no ORM —
   ficavam órfãos no SQLite dev), FECHAMENTOS de caixa antes dos usuários e
   desvincula RESERVAS/PAGAMENTOS dos gestores/financeiros da filial (na
   Postgres, FK RESTRICT derrubava o DELETE com 500).
2. Ordem historico.pagamento_id → NULL antes de apagar pagamentos (mesmo
   motivo: RESTRICT do FK).
3. Sessões do simulador (estado em memória) revogadas quando a filial morre.
4. Último admin ativo não pode ser rebaixado nem desativado por PUT próprio.
"""
import hashlib
from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import (
    FechamentoCaixa,
    Historico,
    Pagamento,
    Reserva,
    Sensor,
    SensorEvento,
    TipoUsuario,
    Usuario,
)


def _admin_h(db, fab, *, ultimo=False):
    admin = fab.usuario(role=TipoUsuario.ADMIN)
    if ultimo:  # zera concorrentes: a base de teste persiste entre testes
        db.query(Usuario).filter(
            Usuario.role == TipoUsuario.ADMIN.value, Usuario.id != admin.id
        ).delete(synchronize_session=False)
        db.commit()
    return admin, fab.token(admin)  # fab.token JA devolve o dict de headers


def _sensor(db, est, codigo):
    sensor = Sensor(
        estacionamento_id=est.id,
        codigo=codigo,
        chave_hash=hashlib.sha256(codigo.encode()).hexdigest(),
    )
    db.add(sensor)
    db.commit()
    return sensor


def _estadia_com_pagamento(db, fab, est):
    andar = fab.andar(est)
    vaga = fab.vaga(andar)
    agora = utc_agora()
    hist = Historico(
        estacionamento_id=est.id, vaga_id=vaga.id,
        entrada_em=agora - timedelta(minutes=75), saida_em=agora,
        tempo_permanencia_minutos=75,
    )
    db.add(hist)
    db.commit()
    pag = Pagamento(
        historico_id=hist.id, estacionamento_id=est.id,
        valor_bruto=12.5, valor_total=12.5,
        metodo_pagamento="pix", status_pagamento="aprovado",
        data_pagamento=agora,
    )
    db.add(pag)
    db.commit()
    return hist, pag


class TestPurgaEstacionamento:
    def test_sensores_eventos_e_caixa_somem_junto(self, client, db, fab):
        admin, h = _admin_h(db, fab)
        est = fab.est()
        sensor = _sensor(db, est, f"SNS-{est.id[:10]}")
        vaga = fab.vaga(fab.andar(est))
        db.add(
            SensorEvento(
                sensor_id=sensor.id, seq=1, status_enviado="ocupada",
                aplicado=True, vaga_id=vaga.id,
            )
        )
        db.add(
            FechamentoCaixa(
                estacionamento_id=est.id, usuario_abertura_id=admin.id,
                usuario_fechamento_id=admin.id,
                data_abertura=utc_agora() - timedelta(hours=3),
                data_fechamento=utc_agora(), valor_total=0.0,
            )
        )
        gestor = fab.usuario(role=TipoUsuario.GESTOR, est=est)
        db.commit()

        est_id, gestor_id, sensor_id = est.id, gestor.id, sensor.id
        r = client.delete(f"/api/admin/estacionamentos/{est_id}", headers=h)
        assert r.status_code == 200, r.text

        db.expunge_all()
        # filtros por est_id: a base de teste é um arquivo compartilhado —
        # contar global veria resíduos dos OUTROS testes da suíte
        assert db.query(Sensor).filter(Sensor.estacionamento_id == est_id).count() == 0
        assert db.query(SensorEvento).filter(SensorEvento.sensor_id == sensor_id).count() == 0
        assert db.query(FechamentoCaixa).filter(FechamentoCaixa.estacionamento_id == est_id).count() == 0
        # gestor da filial excluída não fica órfão: a conta existia PARA ela
        assert db.query(Usuario).filter(Usuario.id == gestor_id).count() == 0

    def test_pagamento_null_out_antes_do_delete(self, client, db, fab):
        # em Postgres era IntegrityError 500: historico apontava pagamento
        # apagado primeiro. Agora o purge NULL-out o pagamento_id antes.
        _admin, h = _admin_h(db, fab)
        est = fab.est()
        hist, pag = _estadia_com_pagamento(db, fab, est)
        hist.pagamento_id = pag.id  # o vínculo nasce na confirmação do serviço
        db.commit()
        hist_id, pag_id, est_id = hist.id, pag.id, est.id
        db.expunge_all()
        assert db.get(Historico, hist_id).pagamento_id == pag_id
        r = client.delete(f"/api/admin/estacionamentos/{est_id}", headers=h)
        assert r.status_code == 200, r.text
        db.expunge_all()
        assert db.query(Historico).filter(Historico.estacionamento_id == est_id).count() == 0
        assert db.query(Pagamento).filter(Pagamento.estacionamento_id == est_id).count() == 0

    def test_sessoes_simulador_revogadas_na_exclusao(self, client, db, fab):
        _admin, h = _admin_h(db, fab)
        est = fab.est()
        c = client.post(
            "/api/admin/simulador/sessoes",
            json={"estacionamento_id": est.id, "expira_em_horas": 1},
            headers=h,
        )
        assert c.status_code == 201, c.text
        token = c.json()["token"]
        assert client.get(f"/api/admin/simulador/sessoes/{token}/validar").status_code == 200

        assert client.delete(f"/api/admin/estacionamentos/{est.id}", headers=h).status_code == 200
        # QR da filial morta não vale mais (rota do validador exige admin)
        v = client.get(f"/api/admin/simulador/sessoes/{token}/validar", headers=h)
        assert v.status_code == 410

    def test_gestor_com_reserva_propria_nao_trava_delete(self, client, db, fab):
        # reserva de motorista NOUTRA filial feita pelo gestor: tem de sumir
        # junto do usuário (FK reservas.usuario_id), senão órfão/RESTRICT.
        _admin, h = _admin_h(db, fab)
        est_a = fab.est()
        est_b = fab.est()
        gestor = fab.usuario(role=TipoUsuario.GESTOR, est=est_a)
        vaga_b = fab.vaga(fab.andar(est_b))
        agora = utc_agora()
        db.add(
            Reserva(
                usuario_id=gestor.id, vaga_id=vaga_b.id,
                status="confirmada", horario_inicio=agora,
                horario_fim=agora + timedelta(minutes=20),
            )
        )
        db.commit()
        est_a_id, gestor_id = est_a.id, gestor.id
        r = client.delete(f"/api/admin/estacionamentos/{est_a_id}", headers=h)
        assert r.status_code == 200, r.text
        db.expunge_all()
        assert db.query(Reserva).filter(Reserva.usuario_id == gestor_id).count() == 0


class TestLockoutAdmin:
    def test_ultimo_admin_nao_pode_ser_rebaixado(self, client, db, fab):
        admin, h = _admin_h(db, fab, ultimo=True)
        r = client.put(
            f"/api/admin/usuarios/{admin.id}",
            json={"role": "usuario"},
            headers=h,
        )
        assert r.status_code == 422, r.text
        assert "último administrador" in r.text.lower()

    def test_ultimo_admin_nao_pode_ser_desativado(self, client, db, fab):
        admin, h = _admin_h(db, fab, ultimo=True)
        r = client.put(
            f"/api/admin/usuarios/{admin.id}",
            json={"is_ativo": False},
            headers=h,
        )
        assert r.status_code == 422, r.text

    def test_segundo_admin_destrava_rebaixamento(self, client, db, fab):
        admin, h = _admin_h(db, fab)
        fab.usuario(role=TipoUsuario.ADMIN)  # mais um humano no balcão
        r = client.put(
            f"/api/admin/usuarios/{admin.id}",
            json={"role": "usuario"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        db.expunge_all()
        assert db.query(Usuario).filter(Usuario.id == admin.id).one().role == "usuario"
