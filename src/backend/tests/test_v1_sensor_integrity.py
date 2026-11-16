"""PR63: high sequence prevents an unrecorded older event from reverting a spot."""
from models.db_models import Sensor, StatusVaga


def test_sensor_replay_out_of_order_and_same_batch(client, db, fab):
    admin = fab.usuario(role="admin")
    est = fab.est("Parking Seq")
    spot = fab.vaga(fab.andar(est), codigo="SEQ01")
    head = fab.token(admin)
    r = client.post("/api/admin/sensores", json={
        "estacionamento_id": est.id, "codigo": "sens-seq",
    }, headers=head)
    assert r.status_code == 201, r.text
    sensor = r.json()
    dev = {"X-Device-Key": sensor["chave"]}

    def send(sequence: int, status: str):
        return client.post("/api/sensores/eventos", headers=dev, json={
            "eventos": [{"seq": sequence, "codigo_vaga": "SEQ01", "status": status}],
        })

    assert send(10, "ocupada").json()["aceitos"] == 1
    db.refresh(spot)
    assert spot.status == StatusVaga.OCUPADA
    old = send(9, "livre")
    assert old.status_code == 200
    assert old.json()["aceitos"] == 0
    assert old.json()["duplicados"] == 1
    db.refresh(spot)
    assert spot.status == StatusVaga.OCUPADA

    assert send(11, "livre").json()["aceitos"] == 1
    db.refresh(spot)
    assert spot.status == StatusVaga.LIVRE
    again = send(10, "ocupada")
    assert again.json()["aceitos"] == 0
    db.refresh(spot)
    assert spot.status == StatusVaga.LIVRE

    sensor_db = db.get(Sensor, sensor["id"])
    assert sensor_db.ultimo_seq == 11
    assert send(12, "ocupada").json()["aceitos"] == 1
    db.refresh(spot)
    assert spot.status == StatusVaga.OCUPADA
