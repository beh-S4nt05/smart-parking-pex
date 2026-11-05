"""Provas comportamentais de que entradas hostis não viram SQL executável."""

import uuid

import pytest
import sqlalchemy as sa

from models.database import engine
from models.db_models import Estacionamento, Usuario, Vaga


PAYLOADS_LOGIN = [
    "admin@smartparking.com' --",
    "admin@smartparking.com' OR '1'='1",
    "x@teste.dev' OR 1=1 --",
    "x@teste.dev' UNION SELECT id, senha_hash FROM usuarios --",
    "x@teste.dev'; DROP TABLE usuarios; --",
    "x@teste.dev' OR SLEEP(2)--",
]


def _assert_resposta_segura(response):
    assert response.status_code < 500, response.text
    texto = response.text.lower()
    assert "traceback" not in texto
    assert "sqlalchemy" not in texto
    assert "syntax error" not in texto


def _assert_tabelas_intactas():
    tabelas = set(sa.inspect(engine).get_table_names())
    assert {"usuarios", "estacionamentos", "vagas", "reservas"}.issubset(tabelas)


@pytest.mark.parametrize("payload", PAYLOADS_LOGIN)
def test_sql_injection_no_login_não_autentica_nem_executa_comando(client, db, payload):
    usuarios_antes = db.query(Usuario).count()

    response = client.post("/auth/login", json={"email": payload, "senha": "qualquer"})

    assert response.status_code == 401, response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
    _assert_resposta_segura(response)
    _assert_tabelas_intactas()
    assert db.query(Usuario).count() == usuarios_antes


@pytest.mark.parametrize(
    ("payload", "senha"),
    [
        ("' OR '1'='1' --", "qualquer"),
        ("qualquer", "' OR '1'='1' --"),
        ("admin@smartparking.com", "admin123' OR '1'='1"),
    ],
)
def test_sql_injection_não_contorna_verificacao_de_senha(client, payload, senha):
    response = client.post("/auth/login", json={"email": payload, "senha": senha})
    assert response.status_code == 401
    assert "access_token" not in response.text
    _assert_resposta_segura(response)


@pytest.mark.parametrize("campo", ["estacionamento_id", "andar_id", "status", "tipo"])
@pytest.mark.parametrize("payload", ["' OR '1'='1' --", "%' UNION SELECT * FROM vagas --"])
def test_sql_injection_em_filtros_não_retorna_dados_de_outro_escopo(client, fab, campo, payload):
    est = fab.est()
    fab.vaga(fab.andar(est))

    response = client.get("/api/vagas", params={campo: payload})

    assert response.status_code == 200, response.text
    assert response.json() == []
    _assert_resposta_segura(response)
    _assert_tabelas_intactas()


@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1' --",
        "id'; DROP TABLE estacionamentos; --",
        "' UNION SELECT * FROM usuarios --",
    ],
)
def test_sql_injection_em_path_não_encontra_objeto_nem_derruba_tabela(client, fab, payload):
    est = fab.est(nome="Estacionamento sentinela")

    mapa = client.get(f"/api/estacionamentos/{payload}/vagas")
    sugestao = client.get(f"/api/estacionamentos/{payload}/proxima-vaga")

    assert mapa.status_code == 404
    assert sugestao.status_code == 404
    _assert_resposta_segura(mapa)
    _assert_resposta_segura(sugestao)
    _assert_tabelas_intactas()
    assert client.get("/api/estacionamentos").status_code == 200
    assert any(item["id"] == est.id for item in client.get("/api/estacionamentos").json())


def test_payload_salvo_como_texto_literal_não_como_sql(client, db, fab):
    admin = fab.usuario(role="admin")
    nome = "QA SQLi '); DROP TABLE usuarios; --"
    usuarios_antes = db.query(Usuario).count()

    criado = client.post(
        "/api/admin/estacionamentos",
        json={"nome": nome, "endereco": "Rua D'Ávila; SELECT 1", "total_andares": 1},
        headers=fab.token(admin),
    )

    assert criado.status_code == 201, criado.text
    assert criado.json()["nome"] == nome
    assert criado.json()["endereco"] == "Rua D'Ávila; SELECT 1"
    _assert_tabelas_intactas()
    assert db.query(Usuario).count() == usuarios_antes
    assert db.get(Estacionamento, criado.json()["id"]).nome == nome

    listado = client.get("/api/estacionamentos")
    registro = next(item for item in listado.json() if item["id"] == criado.json()["id"])
    assert registro["nome"] == nome


def test_payload_em_atualizacao_de_perfil_permanece_dado_do_próprio_usuario(client, db, fab):
    usuario = fab.usuario()
    nome = "D'Ávila; UPDATE usuarios SET role='admin'"
    role_antes = usuario.role

    response = client.put("/auth/me", json={"nome": nome}, headers=fab.token(usuario))

    assert response.status_code == 200, response.text
    assert response.json()["nome"] == nome
    assert response.json()["role"] == role_antes
    db.expire_all()
    persistido = db.get(Usuario, usuario.id)
    assert persistido.nome == nome
    assert persistido.role == role_antes
    _assert_tabelas_intactas()


def test_payload_em_relatorio_público_não_agrega_todos_os_estacionamentos(client, db, fab):
    from datetime import timedelta

    from core.timeutils import utc_agora
    from models.db_models import Historico

    est = fab.est()
    vaga = fab.vaga(fab.andar(est))
    db.add(
        Historico(
            estacionamento_id=est.id,
            vaga_id=vaga.id,
            entrada_em=utc_agora() - timedelta(minutes=5),
        )
    )
    db.commit()

    response = client.get(
        "/api/relatorios/fluxo/publico",
        params={"periodo": "diario", "estacionamento_id": "' OR '1'='1' --"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["total_entradas"] == 0
    assert response.json()["total_saidas"] == 0
    assert "registros" not in response.json()
    _assert_resposta_segura(response)


def test_forca_bruta_no_login_atinge_rate_limit_sem_emitir_token(client):
    email = f"inexistente-{uuid.uuid4().hex[:8]}@teste.dev"
    respostas = [
        client.post("/auth/login", json={"email": email, "senha": "senha-errada"})
        for _ in range(11)
    ]

    assert [r.status_code for r in respostas[:10]] == [401] * 10
    assert respostas[-1].status_code == 429
    assert all("access_token" not in r.text for r in respostas)
    assert "Retry-After" in respostas[-1].headers


def test_apos_payloads_consultas_normais_continuam_funcionando(client, db, fab):
    est = fab.est()
    vaga = fab.vaga(fab.andar(est), status="livre")

    response = client.get("/api/vagas", params={"estacionamento_id": est.id, "status": "livre"})

    assert response.status_code == 200
    assert any(item["id"] == vaga.id for item in response.json())
    assert db.query(Vaga).filter(Vaga.id == vaga.id).count() == 1
