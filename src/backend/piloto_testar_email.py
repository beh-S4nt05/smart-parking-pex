"""Teste manual do provedor de e-mail configurado, sem alterar o banco.

No container backend, após configurar as variáveis corporativas:
    python piloto_testar_email.py --destino pessoa-que-autorizou@exemplo.com

Apenas o operador executa. Não chamar por HTTP/API ou com endereço de terceiros.
"""
import argparse

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException

from rules.identity_service import _enviar_email, _transporte_disponivel


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste de e-mail corporativo Smart Parking")
    parser.add_argument("--destino", required=True, help="E-mail próprio/autorizado para teste")
    args = parser.parse_args()
    try:
        destino = validate_email(args.destino, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        parser.error(f"Destinatário inválido: {exc}")
    if not _transporte_disponivel():
        parser.error("Transporte incompleto: verifique EMAIL_PROVIDER e credenciais no backend")
    try:
        _enviar_email(
            destino,
            "Smart Parking - teste de e-mail corporativo",
            "Esta é uma mensagem de teste do Smart Parking.\n"
            "Nenhuma alteração foi feita no banco de dados.\n"
            "Se não solicitou o teste, ignore esta mensagem.",
        )
    except HTTPException as exc:
        parser.exit(1, f"Falha no transporte: {exc.detail}\n")
    print("O provedor aceitou a mensagem. Confira a caixa de entrada e spam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
