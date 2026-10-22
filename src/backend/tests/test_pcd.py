"""RF-47 — vaga PCD só para quem se declarou PCD no cadastro.

Regra auditada (relato do usuário, rodada 22/10): quem NÃO é PCD ou NÃO
declarou no cadastro é motorista comum — o sistema atribui/reserva vaga
COMUM, nunca PCD. Cobrimos os três pontos do fluxo:

1. cadastro (`POST /auth/registrar`): a declaração entra e volta na resposta;
2. perfil (`PUT /auth/me`): dá pra declarar/revogar depois;
3. consumo:
   · reserva explícita de vaga PCD por não-declarado → 403 (a amarração que
     faltava — antes bastava tocar na célula do mapa);
   · motor de atribuição (`GET .../proxima-vaga`): ignora PCD para
     anônimo/não-declarado, PRIORIZA para declarado; o pedido explícito
     ?tipo_vaga=pcd de não-declarado rebaixa para comum com `aviso`.
"""
from datetime import datetime, timedelta

from models.db_models import TipoUsuario, TipoVaga, Usuario


def _reserve(client, h, vaga_id, minutos=60):
    agora = datetime.utcnow()
    return client.post(
        "/api/reservas",
        json={
            "vaga_id": vaga_id,
            "horario_inicio": agora.isoformat(),
            "horario_fim": (agora + timedelta(minutes=minutos)).isoformat(),
        },
        headers=h,
    )


class TestDeclaracaoNoCadastro:
    def test_registrar_persiste_e_devolve_declaracao(self, client):
        base = {"nome": "QA PCD Um", "senha": "senha123"}
        r1 = client.post(
            "/auth/registrar",
            json={**base, "email": f"qa-pcd-{datetime.utcnow().timestamp()}@t.dev",
                  "is_pcd": True},
        )
        assert r1.status_code == 201, r1.text
        assert r1.json()["is_pcd"] is True
        r2 = client.post(
            "/auth/registrar",
            json={**base, "email": f"qa-pcd2-{datetime.utcnow().timestamp()}@t.dev"},
        )
        assert r2.status_code == 201
        assert r2.json()["is_pcd"] is False  # omissão = comum (RF-47)

    def test_perfil_declarar_e_revogar(self, client, db, fab):
        u = fab.usuario()
        assert u.is_pcd is False
        r = client.put("/auth/me", json={"is_pcd": True}, headers=fab.token(u))
        assert r.status_code == 200, r.text
        assert r.json()["is_pcd"] is True
        r = client.put("/auth/me", json={"is_pcd": False}, headers=fab.token(u))
        assert r.json()["is_pcd"] is False


class TestReservaExplícita:
    def test_nao_declarado_nao_reserva_pcd(self, client, db, fab):
        est = fab.est()
        pcd = fab.vaga(fab.andar(est), codigo="PCD-A1", tipo=TipoVaga.PCD)
        u = fab.usuario()
        r = _reserve(client, fab.token(u), pcd.id)
        assert r.status_code == 403, r.text
        assert "exclusiva" in r.json()["detail"]

    def test_declarado_reserva_pcd_e_tambem_comum(self, client, db, fab):
        est = fab.est()
        andar = fab.andar(est)
        pcd = fab.vaga(andar, codigo="PCD-B1", tipo=TipoVaga.PCD)
        comum = fab.vaga(andar, codigo="COM-B2")
        u = fab.usuario()
        u.is_pcd = True
        db.commit()
        assert _reserve(client, fab.token(u), pcd.id).status_code == 201
        assert _reserve(client, fab.token(u), comum.id).status_code == 201


class TestMotorDeAtribuicao:
    def _mix(self, fab):
        est = fab.est()
        andar = fab.andar(est)
        pcd = fab.vaga(andar, codigo="A1", tipo=TipoVaga.PCD)  # a mais próxima
        comum = fab.vaga(andar, codigo="A2")
        return est, pcd, comum

    def test_anonimo_nunca_recebe_pcd(self, client, db, fab):
        est, _pcd, comum = self._mix(fab)
        r = client.get(f"/api/estacionamentos/{est.id}/proxima-vaga")
        assert r.status_code == 200
        assert r.json()["vaga"]["id"] == comum.id
        assert r.json().get("aviso") is None

    def test_declarado_prioriza_pcd(self, client, db, fab):
        est, pcd, _comum = self._mix(fab)
        u = fab.usuario()
        u.is_pcd = True
        db.commit()
        r = client.get(
            f"/api/estacionamentos/{est.id}/proxima-vaga", headers=fab.token(u)
        )
        assert r.json()["vaga"]["id"] == pcd.id

    def test_pedido_explícito_pcd_de_nao_declarado_rebaixa_com_aviso(
        self, client, db, fab
    ):
        est, _pcd, comum = self._mix(fab)
        u = fab.usuario()
        r = client.get(
            f"/api/estacionamentos/{est.id}/proxima-vaga",
            params={"tipo_vaga": "pcd"},
            headers=fab.token(u),
        )
        assert r.status_code == 200
        assert r.json()["vaga"]["id"] == comum.id
        assert "reservadas" in r.json()["aviso"]

    def test_sozinha_pcd_disponivel_nao_e_sugerida_para_comum(self, client, db, fab):
        est = fab.est()
        fab.vaga(fab.andar(est), codigo="X1", tipo=TipoVaga.PCD)
        r = client.get(f"/api/estacionamentos/{est.id}/proxima-vaga")
        assert r.json()["vaga"] is None
        assert "comuns" in r.json()["mensagem"]
        # mas para o PCD declarado ela É a sugestão
        u = fab.usuario()
        u.is_pcd = True
        db.commit()
        r2 = client.get(
            f"/api/estacionamentos/{est.id}/proxima-vaga", headers=fab.token(u)
        )
        assert r2.json()["vaga"]["codigo"] == "X1"

    def test_token_invalido_e_tratado_anonimo_nao_401(self, client, db, fab):
        # o opcional NÃO pode transformar a rota pública em 401
        est, _pcd, comum = self._mix(fab)
        r = client.get(
            f"/api/estacionamentos/{est.id}/proxima-vaga",
            headers={"Authorization": "Bearer nao-sou-jwt"},
        )
        assert r.status_code == 200
        assert r.json()["vaga"]["id"] == comum.id


class TestLegadoSemDeclaracao:
    def test_usuarios_antigos_sao_comuns(self, client, db, fab):
        # linha criada antes da coluna (migração usa server_default False)
        u = Usuario(
            nome="Legado QA", email=f"legado-{datetime.utcnow().timestamp()}@t.dev",
            senha_hash="x", role=TipoUsuario.USUARIO.value, is_ativo=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.is_pcd is False
