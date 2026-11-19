"""Provisionamento inicial interativo para um piloto isolado em producao.

Uso: docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
  exec backend python piloto_criar_admin.py
Nunca comita credenciais, nunca cria o admin123 padrao e nunca altera conta existente.
"""
from getpass import getpass
import re

from core.config import settings
from core.security import criar_hash_senha
from models.database import SessionLocal
from models.db_models import TipoUsuario, Usuario


def main() -> None:
    if settings.ENVIRONMENT != "production":
        raise SystemExit("Provisionamento exclusivo do perfil production.")
    email = input("E-mail do administrador do piloto: ").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise SystemExit("E-mail invalido.")
    nome = input("Nome do administrador: ").strip()
    if len(nome) < 2:
        raise SystemExit("Nome deve ter ao menos 2 caracteres.")

    senha = getpass("Senha exclusiva do piloto (12-72 bytes): ")
    confirmacao = getpass("Repita a senha: ")
    if senha != confirmacao:
        raise SystemExit("As senhas nao conferem.")
    if len(senha.encode("utf-8")) < 12 or len(senha.encode("utf-8")) > 72:
        raise SystemExit("Senha deve ter entre 12 e 72 bytes UTF-8.")
    if senha in {"admin123", "motor123", "gestor123", "financ123"}:
        raise SystemExit("Nao use senhas conhecidas de demonstracao.")

    db = SessionLocal()
    try:
        if db.query(Usuario).filter(Usuario.email == email).first():
            raise SystemExit("Essa conta ja existe. O script nao redefine senhas.")
        db.add(Usuario(
            nome=nome,
            email=email,
            senha_hash=criar_hash_senha(senha),
            role=TipoUsuario.ADMIN.value,
            is_ativo=True,
        ))
        db.commit()
        print("Administrador criado. Use a UI da V1 para cadastrar os demais usuarios.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
