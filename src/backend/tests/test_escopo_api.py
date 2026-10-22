"""RNF-02/ADR-07 — a matriz de acesso com o escopo novo do SDD (BOLA fechada)."""

from datetime import timedelta

from core.timeutils import utc_agora
from models.db_models import TipoUsuario, Usuario


def _tokens(db, fab):
    admin = db.query(Usuario).filter(Usuario.email == "admin@smartparking.com").first()
    assert admin is not None  # criado pelo bootstrap do main.py (test ≠ production)
    return {"Authorization": f"Bearer {fab.token(admin)['Authorization'].split(' ')[1]}"}


def test_bola_financeiro_gestor_so_no_proprio_estacionamento(client, db, fab):
    est_a = fab.est(nome="QA Bola A")
    est_b = fab.est(nome="QA Bola B")
    gestor_a = fab.usuario(role=TipoUsuario.GESTOR, est=est_a)
    hg = fab.token(gestor_a)
    ha = _tokens(db, fab)

    # preços do vizinho: 403 (antes: 200 com dados alheios)
    assert client.get(f"/api/admin/financeiro/precos/{est_b.id}", headers=hg).status_code == 403
    assert client.get(f"/api/admin/financeiro/precos/{est_a.id}", headers=hg).status_code == 200
    # criar preço no vizinho: 403 — e no próprio: 201
    corpo = {"estacionamento_id": est_b.id, "tipo_vaga": "comum", "valor_hora": 5.0}
    assert client.post("/api/admin/financeiro/precos", json=corpo, headers=hg).status_code == 403
    corpo["estacionamento_id"] = est_a.id
    assert client.post("/api/admin/financeiro/precos", json=corpo, headers=hg).status_code == 201
    # cupons do vizinho: 403
    assert client.get(f"/api/admin/financeiro/cupons/{est_b.id}", headers=hg).status_code == 403
    # eventos com estacionamento alheio explícito: 403
    assert client.get("/api/admin/eventos", params={"estacionamento_id": est_b.id}, headers=hg).status_code == 403
    # admin global passeia nos dois
    assert client.get(f"/api/admin/financeiro/precos/{est_b.id}", headers=ha).status_code == 200


def test_csv_exigira_autenticacao_e_escopo(client, db, fab):
    est = fab.est()
    assert client.get("/api/relatorios/fluxo/csv").status_code == 401

    ha = _tokens(db, fab)
    r = client.get("/api/relatorios/fluxo/csv", params={"periodo": "mensal"}, headers=ha)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0].lstrip("\ufeff").startswith("id;entrada_em")

    motorista = fab.usuario()
    r = client.get(
        "/api/relatorios/fluxo/csv",
        params={"periodo": "mensal", "estacionamento_id": est.id},
        headers=fab.token(motorista),
    )
    assert r.status_code == 403  # motorista não é papel de painel


def test_reserva_futura_de_terceiro_nao_pode_ser_cancelada(client, db, fab):
    est = fab.est(); andar = fab.andar(est); vaga = fab.vaga(andar)
    dono = fab.usuario()
    outro = fab.usuario()
    agora = utc_agora()
    r = client.post(
        "/api/reservas",
        json={
            "vaga_id": vaga.id,
            "horario_inicio": agora.isoformat(),
            "horario_fim": (agora + timedelta(hours=2)).isoformat(),
        },
        headers=fab.token(dono),
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert client.delete(f"/api/reservas/{rid}", headers=fab.token(outro)).status_code == 403
    assert client.delete(f"/api/reservas/{rid}", headers=fab.token(dono)).status_code == 200


def test_relatorios_novos_respondem_para_admin(client, db, fab):
    est = fab.est(); andar = fab.andar(est); fab.vaga(andar)
    db.commit()
    ha = _tokens(db, fab)
    for ep in ("/api/relatorios/ocupacao-historica", "/api/relatorios/rotacao"):
        r = client.get(ep, params={"estacionamento_id": est.id}, headers=ha)
        assert r.status_code == 200, (ep, r.text[:200])
        d = r.json()
        assert d.get("fuso") == "America/Manaus"
