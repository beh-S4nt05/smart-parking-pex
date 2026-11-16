"""Negative authorization tests — forbidden actions never change resources."""
from models.db_models import TipoUsuario, StatusVaga
from core.escopo import garantir_vagas_no_escopo


def test_bulk_scope_checks_all_ids_before_mutation(client, db, fab):
    est_a, est_b = fab.est("Shopping A"), fab.est("Shopping B")
    vaga_a = fab.vaga(fab.andar(est_a), status=StatusVaga.LIVRE)
    vaga_b = fab.vaga(fab.andar(est_b), status=StatusVaga.LIVRE)
    gestor = fab.usuario(role=TipoUsuario.GESTOR, est=est_a)
    h = fab.token(gestor)

    for ids, expected in [
        ([vaga_a.id, vaga_b.id], 403),
        ([vaga_a.id, "vaga-inexistente"], 404),
    ]:
        r = client.patch("/api/vagas/lote/status", json={
            "vaga_ids": ids, "status": "ocupada", "origem": "manual",
        }, headers=h)
        assert r.status_code == expected, r.text
        db.refresh(vaga_a)
        db.refresh(vaga_b)
        assert vaga_a.status == StatusVaga.LIVRE
        assert vaga_b.status == StatusVaga.LIVRE

    # Lote próprio continua funcional, sem bloquear a operação legítima.
    ok = client.patch("/api/vagas/lote/status", json={
        "vaga_ids": [vaga_a.id], "status": "ocupada", "origem": "manual",
    }, headers=h)
    assert ok.status_code == 200, ok.text
    db.refresh(vaga_a)
    assert vaga_a.status == StatusVaga.OCUPADA


def test_driver_cannot_change_spots_or_admin_roles(client, db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    motorista = fab.usuario()
    h = fab.token(motorista)

    alterar = client.patch(f"/api/vagas/{vaga.id}/status", json={
        "status": "ocupada", "origem": "manual",
    }, headers=h)
    assert alterar.status_code == 403
    promover = client.patch(f"/api/admin/usuarios/{motorista.id}/promover-admin", headers=h)
    assert promover.status_code in {401, 403, 404}
    db.refresh(vaga)
    db.refresh(motorista)
    assert vaga.status == StatusVaga.LIVRE
    assert motorista.role == TipoUsuario.USUARIO.value


def test_admin_cannot_update_absent_spot_in_bulk(client, db, fab):
    from core.escopo import garantir_vagas_no_escopo
    admin = fab.usuario(role=TipoUsuario.ADMIN)
    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    from fastapi import HTTPException
    try:
        garantir_vagas_no_escopo(db, admin, [vaga.id, "nao-existe"])
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
