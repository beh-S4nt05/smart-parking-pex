"""Regressão V1: duas contas podem compartilhar telefone sem trocar identidades."""

def _login(client, credencial: str, senha: str):
    return client.post("/auth/login", json={"email": credencial, "senha": senha})


def test_telefone_compartilhado_autentica_pela_senha_da_conta_correta(client, db, fab):
    conta_a = fab.usuario(senha="Senha-A123")
    conta_b = fab.usuario(senha="Senha-B456")
    conta_a.telefone = "(92) 99999-1234"
    conta_b.telefone = "92999991234"
    db.commit()

    a = _login(client, "92999991234", "Senha-A123")
    assert a.status_code == 200, a.text
    assert a.json()["user"]["id"] == conta_a.id

    b = _login(client, "(92) 99999-1234", "Senha-B456")
    assert b.status_code == 200, b.text
    assert b.json()["user"]["id"] == conta_b.id

    errada = _login(client, "92999991234", "Senha-desconhecida")
    assert errada.status_code == 401


def test_telefone_e_senha_compartilhados_solicitam_email_para_evitar_conta_errada(client, db, fab):
    conta_a = fab.usuario(senha="Senha-igual123")
    conta_b = fab.usuario(senha="Senha-igual123")
    conta_a.telefone = "92999992345"
    conta_b.telefone = "(92) 99999-2345"
    db.commit()

    ambiguo = _login(client, "92999992345", "Senha-igual123")
    assert ambiguo.status_code == 409, ambiguo.text
    assert "e-mail" in ambiguo.json()["detail"]

    por_email = _login(client, conta_b.email, "Senha-igual123")
    assert por_email.status_code == 200, por_email.text
    assert por_email.json()["user"]["id"] == conta_b.id


def test_telefone_de_conta_desativada_nao_autentica(client, db, fab):
    usuario = fab.usuario(senha="Senha-inativa123")
    usuario.telefone = "92999993456"
    usuario.is_ativo = False
    db.commit()

    bloqueado = _login(client, "92999993456", "Senha-inativa123")
    assert bloqueado.status_code == 403
    assert "desativado" in bloqueado.json()["detail"].lower()
