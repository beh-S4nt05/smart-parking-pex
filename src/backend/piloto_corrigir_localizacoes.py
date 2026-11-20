"""Corrige EXCLUSIVAMENTE endereços/coords antigos do seed Manaus da V1.

Default: dry-run. Para alterar, rode explicitamente:
    python piloto_corrigir_localizacoes.py --apply

Não altera estacionamento personalizado, reservas, histórico ou vínculos.
Nunca executa o seed e não redefinirá senhas.
"""

import argparse

from models.database import SessionLocal
from models.db_models import Estacionamento

# Nome ANTIGO -> endereço ANTIGO exato, nome real, endereço confirmado.
# Os valores de referência originais são do seed 2026, não de geocodificação.
ATUALIZACOES = {
    "Amazonas Shopping": (
        "Av. Djalma Batista, 1646 - Chapada, Manaus - AM",
        "Amazonas Shopping",
        "Av. Djalma Batista, 482 - Parque 10 de Novembro, Manaus - AM",
    ),
    "Manauara Shopping": (
        "Av. Mário Ypiranga Monteiro, 1300 - Adrianópolis, Manaus - AM",
        "Manauara Shopping",
        "Av. Mário Ypiranga Monteiro, 1300 - Adrianópolis, Manaus - AM",
    ),
    "Sumaúma Park Shopping": (
        "Av. Noel Nutels, 1762 - Cidade Nova, Manaus - AM",
        "Sumaúma Park Shopping",
        "Av. Noel Nutels, 1762 - Cidade Nova, Manaus - AM",
    ),
    "Ponta Negra Shopping": (
        "Av. Coronel Teixeira, 5200 - Ponta Negra, Manaus - AM",
        "Ponta Negra Shopping",
        "Av. Coronel Teixeira, 5705 - Ponta Negra, Manaus - AM",
    ),
    "Millennium Shopping": (
        "Av. Djalma Batista, 2010 - Chapada, Manaus - AM",
        "Millennium Shopping",
        "Av. Djalma Batista, 1661 - Chapada, Manaus - AM",
    ),
    "Studio 5 Festival Mall": (
        "Av. Max Teixeira, 2000 - Cidade Nova, Manaus - AM",
        "Studio 5 Festival Mall",
        "Av. Rodrigo Otávio, 3555 - Distrito Industrial, Manaus - AM",
    ),
    "Shopping Norte": (
        "Av. Camapuã, 1480 - Cidade Nova, Manaus - AM",
        "Shopping Manaus ViaNorte",
        "Av. Arquiteto José Henrique Bento Rodrigues, 3541 - Santa Etelvina, Manaus - AM",
    ),
    "Shopping Phelippe Daou": (
        "Av. Camapuã, 4475 - Jorge Teixeira, Manaus - AM",
        "Shopping Phelippe Daou",
        "Av. Camapuã, 2939 - Cidade de Deus, Manaus - AM",
    ),
}

# Nome e endereço antigo precisam casar exatamente para proteger cadastros
# manuais e não converter shoppings homônimos. Para os dois endereços já
# corretos, apenas as coordenadas históricas aproximadas são limpas.
COORDENADAS_SEED = {
    "Amazonas Shopping": (-3.0728, -60.0194),
    "Manauara Shopping": (-3.0886, -60.0049),
    "Sumaúma Park Shopping": (-3.0309, -60.0041),
    "Ponta Negra Shopping": (-3.0181, -60.0364),
    "Millennium Shopping": (-3.0755, -60.0231),
    "Studio 5 Festival Mall": (-3.0405, -60.0180),
    "Shopping Norte": (-3.0474, -59.9876),
    "Shopping Phelippe Daou": (-3.0550, -59.9558),
}


def corrigir(db, *, aplicar: bool = False) -> tuple[int, int]:
    """Retorna (linhas elegíveis, linhas ignoradas); commit só com --apply."""
    elegiveis = 0
    ignoradas = 0
    for nome_antigo, (endereco_antigo, nome_real, endereco_real) in ATUALIZACOES.items():
        registros = db.query(Estacionamento).filter(
            Estacionamento.nome == nome_antigo,
        ).all()
        for est in registros:
            if est.endereco != endereco_antigo:
                ignoradas += 1
                continue
            coord_seed = COORDENADAS_SEED[nome_antigo]
            gps_antigo = (
                est.latitude is not None and est.longitude is not None
                and abs(est.latitude - coord_seed[0]) < 1e-5
                and abs(est.longitude - coord_seed[1]) < 1e-5
            )
            gps_vazio = est.latitude is None and est.longitude is None
            if not (gps_antigo or gps_vazio):
                # Coordenadas de administrador não devem ser sobrescritas.
                ignoradas += 1
                continue
            if est.nome == nome_real and est.endereco == endereco_real and gps_vazio:
                continue
            elegiveis += 1
            print(f"{'[APLICAR]' if aplicar else '[SIMULAR]'} {nome_antigo} -> {nome_real}: {endereco_real}")
            if aplicar:
                est.nome = nome_real
                est.endereco = endereco_real
                # Remover coordenadas antigas incorretas, não inventar GPS real.
                est.latitude = None
                est.longitude = None

    if aplicar and elegiveis:
        db.commit()
    return elegiveis, ignoradas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Grava correções após inspeção do dry-run")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        n, ignoradas = corrigir(db, aplicar=args.apply)
        print(f"Elegíveis: {n}; ignorados por divergência: {ignoradas}.")
        if not args.apply:
            print("Nenhum dado foi gravado. Use --apply após conferir os registros.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
