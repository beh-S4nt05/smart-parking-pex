# Migrações com Alembic (M4-02 · ADR-04)

O app continua subindo com `Base.metadata.create_all` (não quebramos nada em
funcionamento) — o Alembic entra como **linha de base versionada** do esquema
e mecanismo das mudanças futuras. Baseline gerada em 22/10:
`migrations/versions/3c79cee6fe1f_baseline_esquema_completo_2026_10_22_.py`
(13 tabelas; validada com `alembic upgrade head` em banco vazio e
`alembic check` = zero divergência contra os modelos).

## Bancos NOVOS (deploy do zero)

```bash
cd src/backend
pip install -r requirements-dev.txt
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/smartparking alembic upgrade head
```

## Bancos EXISTENTES (o Postgres do compose da V-02) — STAMP, não upgrade

O esquema já existe criado pelo `create_all`. Diga ao Alembic que a linha de
base já está aplicada, senão o `upgrade` tentará criar tabelas repetidas:

```bash
docker compose -f src/docker-compose.yml exec backend \
  python -m alembic -c /app/alembic.ini stamp head
# (ou, rodando o venv direto no host, com DATABASE_URL apontando para o Postgres:)
DATABASE_URL=... alembic stamp head
```

> O compose atual não instala `alembic` na imagem (é dependência de dev, em
> `requirements-dev.txt`) — para stampar dentro do container:
> `docker compose exec backend pip install alembic && ... stamp head`.
> Alternativa sem tocar na imagem: rodar o stamp de fora, com o venv local.

## Fluxo de mudança futura

```bash
cd src/backend
# 1) altere models/db_models.py
# 2) gere o diff automaticamente contra o banco real (ou um SQLite vazio)
DATABASE_URL=... alembic revision --autogenerate -m "descricao"
# 3) revise o arquivo gerado, depois:
DATABASE_URL=... alembic upgrade head
```

`env.py` lê `DATABASE_URL` do ambiente (mesma hierarquia do app: env > .env >
SQLite de dev) e o alvo é o `Base.metadata` real — autogenerate comparado a
qualquer banco dos modelos.

## O que ficou de fora (decisão 22/10, honesto)

- Dados demo/seed continuam no `seed_demo.py` (idempotente) — não viraram data migration.
- O `create_all` do boot permanece; quando a equipe confiar 100% no Alembic, remova-o e o esquema passa a ser só migrations.
<<<<<<< HEAD
=======

---

## Nota (22/10-rod.4) — `ondelete` nos modelos

Os modelos ganharam `ondelete` defensivo em 13 FKs que não tinham (sensores,
pagamentos→usuários, histórico→pagamento, caixas→filial, cupons→filial).
Efeito prático:

- **bancos novos / SQLite de dev** (`create_all`): o constraint chega ao schema;
- **bancos existentes (Postgres)**: nada muda sozinhos — `alembic check`
  **não** compara `ondelete`, e é intencional: a linha de frente de exclusão é
  o serviço (`admin_service._purgar_operacional`, que já apaga na ordem
  certa). Quem quiser alinhar o banco ao modelo, gere uma revisão com
  `alembic revision --autogenerate -m "fk ondelete"` e EDITE à mão (troca de
  FK exige `batch_alter_table` em SQLite; em Postgres use drop+add com
  `ON CONSTRAINT`).
- Banco de produção da equipe: **stamp-only até 02/11** (política da
  disciplina) — este parágrafo é o registro do porquê.
>>>>>>> eb64687f68d74c589beca0aaf9d41bbce94aeffd
