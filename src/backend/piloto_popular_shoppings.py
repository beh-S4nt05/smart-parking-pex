"""Cria APENAS estacionamentos/vagas fictícios do piloto V1 (Manaus).

NUNCA cria admin, gestor, financeiro, motorista, senha padrão ou sessão.
NUNCA altera tabelas existentes. Dry-run por padrão.

Com o banco vazio e a API em producao:
  python piloto_popular_shoppings.py
  python piloto_popular_shoppings.py --apply

É um conjunto de dados acadêmicos SIMULADOS; não representa sensores
instalados nos shoppings nem parceria comercial com os empreendimentos.
"""
import argparse
import random

from core.config import settings
from models.database import SessionLocal
from models.db_models import Andar, Estacionamento, StatusVaga, Vaga
from seed_demo import SHOPPINGS, _tipo_para_indice


def popular_shoppings_piloto(db, *, aplicar=False):
    """(shoppings, andares, vagas); sem commit sem --apply, sem contas demo."""
    if db.query(Estacionamento).count():
        print("O banco ja possui estacionamentos. Nada sera inserido ou alterado.")
        return (0, 0, 0)
    total_andares = sum(len(s["andares"]) for s in SHOPPINGS)
    total_vagas = sum(sum(s["andares"].values()) for s in SHOPPINGS)
    print(f"Piloto: {len(SHOPPINGS)} shoppings, {total_andares} andares e "
          f"{total_vagas} vagas SIMULADAS em Manaus.")
    print("Nenhum usuario, senha, permissao, reserva ou historico sera criado.")
    if not aplicar:
        print("Simulacao: banco nao alterado. Revise e execute --apply quando aprovado.")
        return (len(SHOPPINGS), total_andares, total_vagas)

    for indice, spec in enumerate(SHOPPINGS):
        est = Estacionamento(
            nome=spec["nome"],
            endereco=spec["endereco"],
            latitude=spec["latitude"],
            longitude=spec["longitude"],
            hora_abertura=spec["hora_abertura"],
            hora_fechamento=spec["hora_fechamento"],
            taxa_hora=spec["taxa_hora"],
            telefone=spec["telefone"],
            total_andares=len(spec["andares"]),
            total_vagas=sum(spec["andares"].values()),
        )
        db.add(est)
        db.flush()
        # Foto inicial reprodutivel para demonstrar disponibilidade, jamais
        # contagem real de ocupacao dos estacionamentos citados.
        aleatorio = random.Random(2026 + indice)  # noqa: S311 - apenas dados simulados, sem finalidade criptografica
        alvo = spec.get("ocupacao_alvo", 0.5)
        for andar_numero, capacidade in spec["andares"].items():
            andar = Andar(
                estacionamento_id=est.id,
                numero_andar=andar_numero,
                capacidade=capacidade,
            )
            db.add(andar)
            db.flush()
            prefixo = chr(ord("A") + (andar_numero - 1) % 26)
            for i in range(capacidade):
                db.add(Vaga(
                    andar_id=andar.id,
                    codigo=f"{prefixo}-{i + 1:02d}",
                    tipo=_tipo_para_indice(i, capacidade),
                    posicao_x=i % 8,
                    posicao_y=i // 8,
                    status=(
                        StatusVaga.OCUPADA if aleatorio.random() < alvo
                        else StatusVaga.LIVRE
                    ),
                ))
    db.commit()
    print("Dados academicos de estacionamentos e vagas criados com sucesso.")
    return (len(SHOPPINGS), total_andares, total_vagas)


def main():
    if settings.ENVIRONMENT.lower() != "production":
        raise SystemExit("Operacao permitida somente no ambiente do piloto production.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Gravar somente se nao houver estacionamentos")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        popular_shoppings_piloto(db, aplicar=args.apply)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
