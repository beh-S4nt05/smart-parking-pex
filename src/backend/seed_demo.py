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

from core.security import criar_hash_senha, verificar_senha
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
    usuario_estacionamentos,
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

# Shoppings que já têm o gestor clássico (gestor@) — os demais ganham um
# gestor próprio (gestor<i>) na hora do seed.
SHOPPING_COM_GESTOR_CLASICO = {"Amazonas Shopping", "Millennium Shopping"}

USUARIOS_DEMO = [
    {
        "nome": "Administrador",
        "email": "admin@smartparking.com",
        "senha": "admin123",
        "role": TipoUsuario.ADMIN.value,
        "telefone": "92999110000",
        "estacionamento": None,
        "vinculos": [],
    },
    {
        "nome": "Gestor Amazonas e Millennium",
        "email": "gestor@smartparking.com",
        "senha": "gestor123",
        "role": TipoUsuario.GESTOR.value,
        "telefone": "92999220000",
        "estacionamento": "Amazonas Shopping",
        "vinculos": ["Millennium Shopping"],
    },
    {
        "nome": "Gestor Amazonas",
        "email": "financeiro@smartparking.com",
        "senha": "gestor123",
        "role": TipoUsuario.GESTOR.value,
        "telefone": "92999330000",
        "estacionamento": "Amazonas Shopping",
        "vinculos": [],
    },
    {
        "nome": "Motorista Demo",
        "email": "motorista@smartparking.com",
        "senha": "motor123",
        "role": TipoUsuario.USUARIO.value,
        "telefone": "92999440000",
        "estacionamento": None,
        "vinculos": [],
        "placa": "AMA1B23",
    },
]

# Um financeiro por shopping: o `$` do pedido vira número sequencial
# (financeiro1, financeiro2 ...) até a quantidade de shoppings cadastrados.
# Os shoppings sem gestor clássico ganham também um gestor próprio (gestor<i>).
for _i, _shopping in enumerate(SHOPPINGS, start=1):
    _nome = _shopping["nome"]
    USUARIOS_DEMO.append(
        {
            "nome": f"Financeiro {_nome}",
            "email": f"financeiro{_i}@smartparking.com",
            "senha": "financ123",
            "role": TipoUsuario.FINANCEIRO.value,
            "telefone": f"92999{60000 + _i}",
            "estacionamento": _nome,
            "vinculos": [],
        }
    )
    if _nome not in SHOPPING_COM_GESTOR_CLASICO:
        USUARIOS_DEMO.append(
            {
                "nome": f"Gestor {_nome}",
                "email": f"gestor{_i}@smartparking.com",
                "senha": "gestor123",
                "role": TipoUsuario.GESTOR.value,
                "telefone": f"92999{70000 + _i}",
                "estacionamento": _nome,
                "vinculos": [],
            }
        )



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


def _sincronizar_vinculos(db: Session, usuario: Usuario, estacionamento_ids: list[str]) -> None:
    """Garante exatamente os vínculos N:N esperados (idempotente)."""
    atual = {v.id for v in usuario.estacionamentos_vinculados}
    esperados = set(estacionamento_ids)
    for est_id in esperados - atual:
        db.execute(
            usuario_estacionamentos.insert().values(
                usuario_id=usuario.id, estacionamento_id=est_id
            )
        )
    stale = atual - esperados
    if stale:
        db.execute(
            usuario_estacionamentos.delete().where(
                usuario_estacionamentos.c.usuario_id == usuario.id,
                usuario_estacionamentos.c.estacionamento_id.in_(stale),
            )
        )


def _garantir_usuario_demo(
    db: Session, spec: dict, por_nome: dict, resumo: dict
) -> None:
    """Cria/atualiza um usuário de demo com papél, principal e vínculos N:N.

    Idempotente e autorreparante: `python seed_demo.py` sobre uma base antiga
    aplica a atribuição atual do spec (papél, vínculo principal e vínculos) —
    assim a estrutura pedida (gestor com vários shoppings, financeiro por
    shopping, admin global) é garantida em qualquer estado anterior.
    """
    nome_est = spec.get("estacionamento")
    principal_id = por_nome[nome_est].id if nome_est in por_nome else None
    vinculo_ids = [
        por_nome[n].id for n in spec.get("vinculos", []) if n in por_nome
    ]

    existente = db.query(Usuario).filter(Usuario.email == spec["email"]).first()
    if existente:
        existente.role = spec["role"]
        if not existente.telefone and spec.get("telefone"):
            existente.telefone = spec["telefone"]
        existente.estacionamento_id = principal_id
        # Senhas padrões: só reinicia a hash quando a atual não confere —
        # evita travar um usuário que alterou a senha intencionalmente.
        if not verificar_senha(spec["senha"], existente.senha_hash):
            existente.senha_hash = criar_hash_senha(spec["senha"])
        _sincronizar_vinculos(db, existente, vinculo_ids)
        db.commit()
        return

    usuario = Usuario(
        nome=spec["nome"],
        email=spec["email"],
        telefone=spec.get("telefone"),
        placa_veiculo=spec.get("placa"),
        senha_hash=criar_hash_senha(spec["senha"]),
        role=spec["role"],
        estacionamento_id=principal_id,
        is_ativo=True,
    )
    db.add(usuario)
    db.flush()
    _sincronizar_vinculos(db, usuario, vinculo_ids)
    resumo["usuarios"] += 1


def popular_database(db: Session) -> dict:
    """Cria estacionamentos, andares, vagas, usuários e histórico de demonstração."""
    resumo = {"estacionamentos": 0, "andares": 0, "vagas": 0, "usuarios": 0, "historicos": 0}

    # Idempotência: se já existe estrutura demo, apenas garante os usuários
    if db.query(Estacionamento).count() > 0:
        print("ℹ️  Estacionamentos já existem — pulando criação de estrutura (use --reset para recriar).")
        by_nome = {e.nome: e for e in db.query(Estacionamento).all()}
        for spec in USUARIOS_DEMO:
            _garantir_usuario_demo(db, spec, by_nome, resumo)
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
        _garantir_usuario_demo(db, spec, estacionamento_por_nome, resumo)

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
    ids = [
        uid
        for (uid,) in db.query(Usuario.id)
        .filter(Usuario.email.in_(emails))
        .all()
    ]
    if ids:
        # SQLite não ativa FK por default: limpa os vínculos N:N manualmente.
        db.execute(
            usuario_estacionamentos.delete().where(
                usuario_estacionamentos.c.usuario_id.in_(ids)
            )
        )
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
