"""Cadastro V1 em produção: validação, normalização e resposta sem dados sensíveis."""
import uuid

from models.db_models import Usuario


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.test"


def test_cadastro_normaliza_nome_email_telefone_sem_expor_senha(client, db):
    email = _email("cadastro")
    resposta = client.post("/auth/registrar", json={
        "nome": "   Maria   de  Oliveira  ",
        "email": email.upper(),
        "telefone": "(92) 99999-8888",
        "senha": "FraseSegura-2026!",
    })
    assert resposta.status_code == 201, resposta.text
    data = resposta.json()
    assert data["nome"] == "Maria de Oliveira"
    assert data["email"] == email
    assert data["telefone"] == "92999998888"
    assert data["role"] == "usuario"
    assert "senha" not in data and "senha_hash" not in data
    conta = db.query(Usuario).filter(Usuario.email == email).one()
    assert conta.senha_hash != "FraseSegura-2026!"
    login = client.post("/auth/login", json={"email": email, "senha": "FraseSegura-2026!"})
    assert login.status_code == 200, login.text


def test_cadastro_duplicado_retorna_409_sem_alterar_primeira_conta(client, db):
    email = _email("duplicado")
    primeira = client.post("/auth/registrar", json={
        "nome": "Primeira Pessoa",
        "email": email,
        "senha": "PrimeiraSenha2026!",
    })
    assert primeira.status_code == 201, primeira.text
    segunda = client.post("/auth/registrar", json={
        "nome": "Outra Pessoa",
        "email": email.upper(),
        "senha": "OutraSenha2026!",
    })
    assert segunda.status_code == 409
    assert "já possui" in segunda.json()["detail"]
    assert db.query(Usuario).filter(Usuario.email == email).count() == 1
    assert db.query(Usuario).filter(Usuario.email == email).one().nome == "Primeira Pessoa"


def test_cadastro_bloqueia_nome_vazio_telefone_incompleto_e_senha_curta(client, db):
    email = _email("invalidos")
    invalida = client.post("/auth/registrar", json={
        "nome": "    ",
        "email": email,
        "telefone": "99999",
        "senha": "1234567",
    })
    assert invalida.status_code == 422
    campos = {str(i["loc"][-1]) for i in invalida.json()["detail"]}
    assert {"nome", "telefone", "senha"}.issubset(campos)
    assert db.query(Usuario).filter(Usuario.email == email).count() == 0


def test_cadastro_sem_veiculo_e_sem_telefone_eh_valido(client, db):
    email = _email("minimo")
    resposta = client.post("/auth/registrar", json={
        "nome": "Conta Simples",
        "email": email,
        "senha": "SenhaUnica2026!",
    })
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["telefone"] is None
