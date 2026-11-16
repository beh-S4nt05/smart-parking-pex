"""V1: garagem, credenciais de estacionamento e compatibilidade de vagas.

Revision ID: d8f3a91c6e40
Revises: c4e8b1d2f9a0

Expansão aditiva e compatível com reservas antigas. Migra placas legadas sem
remover usuarios.placa_veiculo. Suporta bancos que tiveram create_all/reparo
de compatibilidade antes da migração, inclusive com tabelas já criadas.
"""
import sqlalchemy as sa
from alembic import op

revision = "d8f3a91c6e40"
down_revision = "c4e8b1d2f9a0"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table):
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table):
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


def _column_if_missing(table, name, column):
    if name not in _columns(table):
        op.add_column(table, column)


def _index_if_missing(table, name, columns):
    if name not in _indexes(table):
        op.create_index(name, table, columns)


def upgrade() -> None:
    tables = _tables()

    # 1. Acrescentar atributos nullable. Não apagar placa_veiculo nem is_pcd
    # (legados) e não alterar reservas existentes.
    _column_if_missing("usuarios", "data_nascimento", sa.Column("data_nascimento", sa.Date(), nullable=True))
    _column_if_missing("vagas", "categoria_veiculo", sa.Column("categoria_veiculo", sa.String(12), nullable=True))
    _column_if_missing(
        "vagas", "recarga_disponivel",
        sa.Column("recarga_disponivel", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _column_if_missing("vagas", "conector_tipo", sa.Column("conector_tipo", sa.String(40), nullable=True))

    # 2. Novas tabelas. Checagem evita choque com Base.metadata.create_all
    # em um volume iniciado antes da execução do Alembic.
    if "veiculos" not in tables:
        op.create_table(
            "veiculos",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), nullable=False),
            sa.Column("placa", sa.String(12), nullable=False),
            sa.Column("categoria", sa.String(12), nullable=False),
            sa.Column("motorizacao", sa.String(20), nullable=False),
            sa.Column("marca", sa.String(80), nullable=True),
            sa.Column("modelo", sa.String(100), nullable=True),
            sa.Column("conector_tipo", sa.String(40), nullable=True),
            sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("usuario_id", "placa", name="uq_veiculo_usuario_placa"),
        )
    _index_if_missing("veiculos", "ix_veiculos_usuario_id", ["usuario_id"])
    _index_if_missing("veiculos", "ix_veiculos_placa", ["placa"])

    if "credenciais_estacionamento" not in tables:
        op.create_table(
            "credenciais_estacionamento",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("usuario_id", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(12), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("referencia_hash", sa.String(64), nullable=True),
            sa.Column("validade", sa.Date(), nullable=True),
            sa.Column("verificado_por_id", sa.String(), nullable=True),
            sa.Column("verificado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["verificado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        )
    _index_if_missing("credenciais_estacionamento", "ix_credenciais_estacionamento_usuario_id", ["usuario_id"])
    _index_if_missing("credenciais_estacionamento", "ix_credenciais_estacionamento_status", ["status"])

    if "auditoria_credenciais" not in tables:
        op.create_table(
            "auditoria_credenciais",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("credencial_id", sa.String(), nullable=False),
            sa.Column("avaliador_id", sa.String(), nullable=True),
            sa.Column("acao", sa.String(30), nullable=False),
            sa.Column("justificativa", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["credencial_id"], ["credenciais_estacionamento.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["avaliador_id"], ["usuarios.id"], ondelete="SET NULL"),
        )
    _index_if_missing("auditoria_credenciais", "ix_auditoria_credenciais_credencial_id", ["credencial_id"])

    _column_if_missing("reservas", "veiculo_id", sa.Column("veiculo_id", sa.String(), nullable=True))
    _column_if_missing("reservas", "credencial_id", sa.Column("credencial_id", sa.String(), nullable=True))
    _index_if_missing("reservas", "ix_reservas_veiculo_id", ["veiculo_id"])

    # Se o boot legou colunas sem FK, restaura a integridade em PostgreSQL.
    # Em SQLite, a adição de FK à tabela existente exigiria table rebuild;
    # a instalação SQLite suportada deve aplicar o Alembic antes do boot.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        fks = sa.inspect(bind).get_foreign_keys("reservas")
        for col, target, name in [
            ("veiculo_id", "veiculos", "fk_reservas_veiculo_id"),
            ("credencial_id", "credenciais_estacionamento", "fk_reservas_credencial_id"),
        ]:
            if not any(col in fk.get("constrained_columns", []) for fk in fks):
                op.create_foreign_key(name, "reservas", target, [col], ["id"], ondelete="SET NULL")
    else:
        # SQLite com schema criado pelo Alembic: adição via batch_copy inclui FK.
        # Usamos batch_alter_table somente quando não existe a FK.
        fks = sa.inspect(bind).get_foreign_keys("reservas")
        faltantes = [
            (col, target, name)
            for col, target, name in [
                ("veiculo_id", "veiculos", "fk_reservas_veiculo_id"),
                ("credencial_id", "credenciais_estacionamento", "fk_reservas_credencial_id"),
            ]
            if not any(col in fk.get("constrained_columns", []) for fk in fks)
        ]
        if faltantes:
            with op.batch_alter_table("reservas", recreate="always") as batch:
                for col, target, name in faltantes:
                    batch.create_foreign_key(name, target, [col], ["id"], ondelete="SET NULL")

    # 3. Backfill idempotente. Não inventar modelo/motorização a partir de placa.
    # A coluna legada permanece. Registro só quando não existe mesma placa.
    op.execute(sa.text("""
        INSERT INTO veiculos
            (id, usuario_id, placa, categoria, motorizacao, principal, ativo)
        SELECT 'legacy-' || u.id, u.id, UPPER(TRIM(u.placa_veiculo)),
               'carro', 'nao_informada', true, true
        FROM usuarios u
        WHERE u.placa_veiculo IS NOT NULL AND TRIM(u.placa_veiculo) <> ''
          AND LENGTH(TRIM(u.placa_veiculo)) <= 12
          AND NOT EXISTS (
              SELECT 1 FROM veiculos v
              WHERE v.usuario_id = u.id
                AND v.placa = UPPER(TRIM(u.placa_veiculo))
          )
    """))


def downgrade() -> None:
    # Destrutivo para novos dados: usar somente em dev e com backup.
    op.drop_index("ix_reservas_veiculo_id", table_name="reservas")
    # SQLite requer batch para remover colunas que possuem FK.
    with op.batch_alter_table("reservas") as batch:
        batch.drop_column("credencial_id")
        batch.drop_column("veiculo_id")
    op.drop_index("ix_auditoria_credenciais_credencial_id", table_name="auditoria_credenciais")
    op.drop_table("auditoria_credenciais")
    op.drop_index("ix_credenciais_estacionamento_status", table_name="credenciais_estacionamento")
    op.drop_index("ix_credenciais_estacionamento_usuario_id", table_name="credenciais_estacionamento")
    op.drop_table("credenciais_estacionamento")
    op.drop_index("ix_veiculos_placa", table_name="veiculos")
    op.drop_index("ix_veiculos_usuario_id", table_name="veiculos")
    op.drop_table("veiculos")
    op.drop_column("vagas", "conector_tipo")
    op.drop_column("vagas", "recarga_disponivel")
    op.drop_column("vagas", "categoria_veiculo")
    op.drop_column("usuarios", "data_nascimento")
