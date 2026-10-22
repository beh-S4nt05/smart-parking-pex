"""
Seed de demonstração do SmartParking — shoppings reais de Manaus/AM.

Popula o banco com:
  • 8 estacionamentos de shoppings parceiros (endereços e coordenadas aproximadas)
  • andares e vagas por andar (tipos: comum, pcd, idoso, moto, eletrico)
  • usuários demo (admin, gestor, financeiro, motorista) — senhas do README
  • histórico de entradas/saídas de hoje (para os relatórios nascerem vivos)

Uso:
    python seed_demo.py            # aplica o seed (idempotente)
    python seed_demo.py --reset    # apaga estacionamentos/vagas/usuarios demo e recria

Em desenvolvimento o `main.py` chama `popular_database()` automaticamente
quando o banco está vazio (SEED_DEMO_ON_STARTUP=True e DEBUG=True).
"""

import argparse
import random
import sys
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.security import criar_hash_senha
from models.database import Base, SessionLocal, engine
from models.db_models import (
    Andar,
    Estacionamento,
    Historico,
    StatusPagamento,
    StatusVaga,
    TipoUsuario,
    TipoVaga,
    Usuario,
    Vaga,
)

random.seed(2026)  # demo reproduzível

# ---------------------------------------------------------------------------
# Shoppings parceiros de Manaus/AM — números casados com os templates do Figma
# ---------------------------------------------------------------------------
SHOPPINGS = [
    {
        "nome": "Amazonas Shopping",
        "endereco": "Av. Djalma Batista, 1646 - Chapada, Manaus - AM",
        "bairro": "Chapada",
        "latitude": -3.0728,
        "longitude": -60.0194,
        "hora_abertura": "06:00",
        "hora_fechamento": "00:00",
        "taxa_hora": 8.00,
        "telefone": "(92) 3655-6000",
        "andares": {1: 105, 2: 105, 3: 105, 4: 105},
        "ocupacao_alvo": 0.89,
    },
    {
        "nome": "Manauara Shopping",
        "endereco": "Av. Mário Ypiranga Monteiro, 1300 - Adrianópolis, Manaus - AM",
        "bairro": "Adrianópolis",
        "latitude": -3.0886,
        "longitude": -60.0049,
        "hora_abertura": "06:00",
        "hora_fechamento": "00:00",
        "taxa_hora": 9.00,
        "telefone": "(92) 2121-3000",
        "andares": {1: 120, 2: 120, 3: 120},
        "ocupacao_alvo": 0.64,
    },
    {
        "nome": "Sumaúma Park Shopping",
        "endereco": "Av. Noel Nutels, 1762 - Cidade Nova, Manaus - AM",
        "bairro": "Cidade Nova",
        "latitude": -3.0309,
        "longitude": -60.0041,
        "hora_abertura": "07:00",
        "hora_fechamento": "23:00",
        "taxa_hora": 6.00,
        "telefone": "(92) 3655-8000",
        "andares": {1: 100, 2: 100, 3: 100},
        "ocupacao_alvo": 0.96,
    },
    {
        "nome": "Ponta Negra Shopping",
        "endereco": "Av. Coronel Teixeira, 5200 - Ponta Negra, Manaus - AM",
        "bairro": "Ponta Negra",
        "latitude": -3.0181,
        "longitude": -60.0364,
        "hora_abertura": "07:00",
        "hora_fechamento": "23:00",
        "taxa_hora": 7.00,
        "telefone": "(92) 3655-7000",
        "andares": {1: 110, 2: 110},
        "ocupacao_alvo": 0.57,
    },
    {
        "nome": "Millennium Shopping",
        "endereco": "Av. Djalma Batista, 2010 - Chapada, Manaus - AM",
        "bairro": "Chapada",
        "latitude": -3.0755,
        "longitude": -60.0231,
        "hora_abertura": "08:00",
        "hora_fechamento": "22:00",
        "taxa_hora": 6.00,
        "telefone": "(92) 3236-5000",
        "andares": {1: 60, 2: 60},
        "ocupacao_alvo": 0.62,
    },
    {
        "nome": "Studio 5 Festival Mall",
        "endereco": "Av. Max Teixeira, 2000 - Cidade Nova, Manaus - AM",
        "bairro": "Cidade Nova",
        "latitude": -3.0405,
        "longitude": -60.0180,
        "hora_abertura": "07:00",
        "hora_fechamento": "23:00",
        "taxa_hora": 5.00,
        "telefone": "(92) 3655-9000",
        "andares": {1: 80, 2: 70},
        "ocupacao_alvo": 0.44,
    },
    {
        "nome": "Shopping Norte",
        "endereco": "Av. Camapuã, 1480 - Cidade Nova, Manaus - AM",
        "bairro": "Cidade Nova",
        "latitude": -3.0474,
        "longitude": -59.9876,
        "hora_abertura": "08:00",
        "hora_fechamento": "22:00",
        "taxa_hora": 5.00,
        "telefone": "(92) 3655-1000",
        "andares": {1: 90},
        "ocupacao_alvo": 0.38,
    },
    {
        "nome": "Shopping Phelippe Daou",
        "endereco": "Av. Camapuã, 4475 - Jorge Teixeira, Manaus - AM",
        "bairro": "Jorge Teixeira",
        "latitude": -3.0550,
        "longitude": -59.9558,
        "hora_abertura": "08:00",
        "hora_fechamento": "22:00",
        "taxa_hora": 5.00,
        "telefone": "(92) 3655-2000",
        "andares": {1: 55, 2: 45},
        "ocupacao_alvo": 0.50,
    },
]

USUARIOS_DEMO = [
    {
        "nome": "Administrador",
        "email": "admin@smartparking.com",
        "senha": "admin123",
        "role": TipoUsuario.ADMIN.value,
        "telefone": "92999110000",
        "estacionamento": None,
    },
    {
        "nome": "Gestor Amazonas",
        "email": "gestor@smartparking.com",
        "senha": "gestor123",
        "role": TipoUsuario.GESTOR.value,
        "telefone": "92999220000",
        "estacionamento": "Amazonas Shopping",
    },
    {
        "nome": "Financeiro Central",
        "email": "financeiro@smartparking.com",
        "senha": "financ123",
        "role": TipoUsuario.FINANCEIRO.value,
        "telefone": "92999330000",
        "estacionamento": "Manauara Shopping",
    },
    {
        "nome": "Motorista Demo",
        "email": "motorista@smartparking.com",
        "senha": "motor123",
        "role": TipoUsuario.USUARIO.value,
        "telefone": "92999440000",
        "estacionamento": None,
        "placa": "AMA1B23",
    },
]



def _tipo_para_indice(i: int, total: int) -> str:
    """Distribui tipos especiais: ~8% PCD, ~8% idoso, ~15% moto, ~4% elétrico."""
    pct = (i + 1) / total
    if pct <= 0.08:
        return TipoVaga.PCD.value
    if pct <= 0.16:
        return TipoVaga.IDOSO.value
    if pct <= 0.31:
        return TipoVaga.MOTO.value
    if pct <= 0.35:
        return TipoVaga.ELETRICO.value
    return TipoVaga.COMUM.value


def popular_database(db: Session) -> dict:
    """Cria estacionamentos, andares, vagas, usuários e histórico de demonstração."""
    resumo = {"estacionamentos": 0, "andares": 0, "vagas": 0, "usuarios": 0, "historicos": 0}

    # Idempotência: se já existe estrutura demo, apenas garante os usuários
    if db.query(Estacionamento).count() > 0:
        print("ℹ️  Estacionamentos já existem — pulando criação de estrutura (use --reset para recriar).")
        existentes = {e.nome for e in db.query(Estacionamento).all()}
        by_nome = {e.nome: e for e in db.query(Estacionamento).all()}
        for spec in USUARIOS_DEMO:
            usuario = db.query(Usuario).filter(Usuario.email == spec["email"]).first()
            vinculo = (
                by_nome[spec["estacionamento"]].id
                if spec.get("estacionamento") in existentes
                else None
            )
            if usuario:
                if not usuario.telefone and spec.get("telefone"):
                    usuario.telefone = spec["telefone"]
                if spec["role"] == TipoUsuario.ADMIN.value:
                    usuario.role = TipoUsuario.ADMIN.value
                if vinculo and not usuario.estacionamento_id:
                    usuario.estacionamento_id = vinculo
            elif spec["email"] != "admin@smartparking.com":
                db.add(
                    Usuario(
                        nome=spec["nome"],
                        email=spec["email"],
                        telefone=spec.get("telefone"),
                        placa_veiculo=spec.get("placa"),
                        senha_hash=criar_hash_senha(spec["senha"]),
                        role=spec["role"],
                        estacionamento_id=vinculo,
                        is_ativo=True,
                    )
                )
                resumo["usuarios"] += 1
        db.commit()
        return resumo

    # -------- Estacionamentos + andares + vagas --------
    estacionamento_por_nome = {}
    for spec in SHOPPINGS:
        andares_spec = spec["andares"]
        est = Estacionamento(
            nome=spec["nome"],
            endereco=spec["endereco"],
            latitude=spec["latitude"],
            longitude=spec["longitude"],
            hora_abertura=spec["hora_abertura"],
            hora_fechamento=spec["hora_fechamento"],
            taxa_hora=spec["taxa_hora"],
            telefone=spec["telefone"],
            total_andares=len(andares_spec),
            total_vagas=sum(andares_spec.values()),
        )
        db.add(est)
        db.flush()
        estacionamento_por_nome[est.nome] = est
        resumo["estacionamentos"] += 1

        for numero_andar, capacidade in andares_spec.items():
            andar = Andar(
                estacionamento_id=est.id,
                numero_andar=numero_andar,
                capacidade=capacidade,
            )
            db.add(andar)
            db.flush()
            resumo["andares"] += 1

            # códigos no formato do painel: A-01, A-02 ... B-01...
            # (prefixo = letra do andar; o mapa do app agrupa por linha)
            prefixo = chr(ord("A") + (numero_andar - 1) % 26)
            for i in range(capacidade):
                vaga = Vaga(
                    andar_id=andar.id,
                    codigo=f"{prefixo}-{i + 1:02d}",
                    tipo=_tipo_para_indice(i, capacidade),
                    posicao_x=i % 8,
                    posicao_y=i // 8,
                    status=StatusVaga.LIVRE,
                )
                db.add(vaga)
            resumo["vagas"] += capacidade

    db.flush()

    # -------- Ocupação inicial realista por estacionamento --------
    todas_vagas = db.query(Vaga).all()
    alvo_por_nome = {s["nome"]: s.get("ocupacao_alvo", 0.5) for s in SHOPPINGS}
    vagas_por_est: dict[str, list[Vaga]] = {}
    for vaga in todas_vagas:
        nome = vaga.andar.estacionamento.nome
        vagas_por_est.setdefault(nome, []).append(vaga)

    hoje = datetime.now().replace(microsecond=0)
    historicos = []
    for nome, vagas in vagas_por_est.items():
        alvo = alvo_por_nome.get(nome, 0.5)
        random.shuffle(vagas)
        n_ocupadas = int(len(vagas) * alvo)
        for idx, vaga in enumerate(vagas):
            if idx == n_ocupadas:
                # a primeira após o corte de ocupadas nasce reservada
                vaga.status = StatusVaga.RESERVADA
            elif idx < n_ocupadas:
                vaga.status = StatusVaga.OCUPADA
                # entrada há X minutos (veículo "estacionado agora")
                minutos = random.randint(5, 240)
                entrada = hoje - timedelta(minutes=minutos)
                historicos.append(
                    Historico(
                        estacionamento_id=vaga.andar.estacionamento_id,
                        vaga_id=vaga.id,
                        entrada_em=entrada,
                        status_pagamento=StatusPagamento.PENDENTE,
                    )
                )
            else:
                # ~3% das livres nascem inativas (manutenção)
                if random.random() < 0.03:
                    vaga.status = StatusVaga.INATIVA

        # histórico de veículos que já saíram hoje (alimenta /relatorios/fluxo)
        livres = [v for v in vagas if v.status == StatusVaga.LIVRE]
        for vaga in random.sample(livres, k=min(6, len(livres))):
            entrada = hoje - timedelta(hours=random.randint(2, 10), minutes=random.randint(0, 59))
            saida = entrada + timedelta(minutes=random.randint(45, 180))
            if saida >= hoje:
                saida = hoje - timedelta(minutes=5)
            minutos = int((saida - entrada).total_seconds() // 60)
            valor = round(max(1.0, minutos / 60 * (vaga.andar.estacionamento.taxa_hora or 6)), 2)
            historicos.append(
                Historico(
                    estacionamento_id=vaga.andar.estacionamento_id,
                    vaga_id=vaga.id,
                    entrada_em=entrada,
                    saida_em=saida,
                    tempo_permanencia_minutos=minutos,
                    valor_bruto=valor,
                    valor_desconto=0.0,
                    valor_total=valor,
                    status_pagamento=StatusPagamento.PAGO,
                    forma_pagamento="pix",
                )
            )

    db.add_all(historicos)
    resumo["historicos"] = len(historicos)

    # -------- Usuários de demonstração --------
    for spec in USUARIOS_DEMO:
        vinculo = (
            estacionamento_por_nome[spec["estacionamento"]].id
            if spec.get("estacionamento")
            else None
        )
        existente = db.query(Usuario).filter(Usuario.email == spec["email"]).first()
        if existente:
            # completa campos de demo que possam faltar (ex.: admin criado
            # no boot antes do seed não tem telefone) sem sobrescrever nada
            if not existente.telefone and spec.get("telefone"):
                existente.telefone = spec["telefone"]
            if spec["role"] == TipoUsuario.ADMIN.value:
                existente.role = TipoUsuario.ADMIN.value
            if vinculo and not existente.estacionamento_id:
                existente.estacionamento_id = vinculo
            db.commit()
            continue
        usuario = Usuario(
            nome=spec["nome"],
            email=spec["email"],
            telefone=spec.get("telefone"),
            placa_veiculo=spec.get("placa"),
            senha_hash=criar_hash_senha(spec["senha"]),
            role=spec["role"],
            estacionamento_id=vinculo,
            is_ativo=True,
        )
        db.add(usuario)
        resumo["usuarios"] += 1

    # -------- Tarifas base por estacionamento (ConfiguracaoPreco) --------
    from models.db_models import ConfiguracaoPreco

    for est in estacionamento_por_nome.values():
        for tipo, mult in (
            (TipoVaga.COMUM.value, 1.0),
            (TipoVaga.MOTO.value, 0.5),
            (TipoVaga.ELETRICO.value, 1.2),
            # ACH-07: sem PCD/idoso o modal "cartão especial" ficava sem preço
            # e o calcular-tarifa respondia "Preço não configurado".
            (TipoVaga.PCD.value, 1.0),
            (TipoVaga.IDOSO.value, 1.0),
        ):
            existe = (
                db.query(ConfiguracaoPreco)
                .filter(
                    ConfiguracaoPreco.estacionamento_id == est.id,
                    ConfiguracaoPreco.tipo_vaga == tipo,
                )
                .first()
            )
            if existe:
                continue
            db.add(
                ConfiguracaoPreco(
                    estacionamento_id=est.id,
                    tipo_vaga=tipo,
                    valor_hora=round(est.taxa_hora * mult, 2),
                    valor_fração_15min=round(est.taxa_hora * mult / 4, 2),
                    valor_diaria=round(est.taxa_hora * mult * 10, 2),
                )
            )

    db.commit()
    return resumo


def resetar_dados_demo(db: Session) -> None:
    """Remove estacionamentos (cascata limpa andares/vagas) e usuários demo."""
    db.query(Historico).delete()
    db.query(Estacionamento).delete()
    emails = [u["email"] for u in USUARIOS_DEMO]
    db.query(Usuario).filter(Usuario.email.in_(emails)).delete(synchronize_session=False)
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed de demonstração SmartParking")
    parser.add_argument("--reset", action="store_true", help="apaga os dados demo e recria")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.reset:
            print("🧹 Removendo dados de demonstração...")
            resetar_dados_demo(db)
        resumo = popular_database(db)
        print(
            "✅ Seed aplicado: "
            f"{resumo['estacionamentos']} estacionamentos, "
            f"{resumo['andares']} andares, "
            f"{resumo['vagas']} vagas, "
            f"{resumo['usuarios']} usuários demo, "
            f"{resumo['historicos']} registros de histórico."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
