# Migrações com Alembic (M4-02 · ADR-04)

O app continua subindo com `Base.metadata.create_all` (não quebramos nada em
funcionamento) — o Alembic entra como **linha de base versionada** do esquema
e mecanismo das mudanças futuras. Baseline gerada em 22/10:
`migrations/versions/3c79cee6fe1f_baseline_esquema_completo_2026_10_22_.py`
(13 tabelas; validada com `alembic upgrade head` em banco vazio e
`alembic check` = zero divergência contra os modelos).

**2ª revisão — 22/10 (RF-47):**
`migrations/versions/a7e41c9d0b52_rf47_usuario_is_pcd.py` — adiciona
`usuarios.is_pcd BOOLEAN NOT NULL DEFAULT false`. Escolha deliberada:
`server_default` faz toda linha pré-existente virar **comum** (quem nunca
declarou não tem direito à vaga PCD — exatamente a regra da RF-47), sem
backfill e sem lock em Postgres. `downgrade` drop-safe. Validada com
`upgrade head` + `alembic check` em banco vazio.

**Nota Docker (visto na máquina do usuário em 22/10):** a imagem do backend
não carrega alembic nos requirements de runtime — volumes criados antes de
uma revisão nova ficariam com a tabela antiga e o boot quebrava
(`UndefinedColumn` no seed de admin → healthcheck falha →
`dependency backend failed to start`). O `main.py` ganhou
`reparar_esquema_antigo()`, chamado antes do seed: detecta a coluna ausente e
aplica o DDL equivalente à revisão (idempotente, PG e SQLite, testes em
`tests/test_compat_volume.py`). Para parity completa com os modelos, rode
`alembic upgrade head` a partir do host — o auto-reparo cobre só colunas
simples com default seguro.

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


---

## V1 — Veículos, credenciais e compatibilidade de vagas (d8f3a91c6e40)

A revisão `d8f3a91c6e40` acrescenta `veiculos`,
`credenciais_estacionamento`, `auditoria_credenciais`,
`usuarios.data_nascimento`, detalhes opcionais de compatibilidade em
`vagas` e duas referências opcionais em `reservas`. **Não remove**
`usuarios.placa_veiculo`, `usuarios.is_pcd` nem reservas antigas.
O backfill copia placas legadas para um veículo do tipo `carro` com
motorização `nao_informada` (não deduz elétrico pela placa).

### Executar de forma segura no banco existente

1. **Backup obrigatório:** confirme o `DATABASE_URL` que o backend usa e faça
   `pg_dump` do banco PostgreSQL correspondente. Não use `docker compose down -v`
   ou o comando `reset`.
2. Execute a migração **antes de iniciar a nova imagem do backend**, para que
   `create_all` não antecipe parte do esquema; utilize Python do host com
   dependências de `requirements-dev.txt` e conexão válida ao PostgreSQL.
3. Em `src/backend`, com `DATABASE_URL` apontando para o mesmo banco:

```bash
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
python -m alembic current
```

Se `current` estiver vazio, mas o banco já contiver toda a versão anterior
(`usuarios.is_pcd`, `usuario_estacionamentos` etc.), **confira antes de fazer stamp**.
Só nesse caso execute `python -m alembic stamp c4e8b1d2f9a0` e, em seguida,
`python -m alembic upgrade head`. Não dê `stamp head` às cegas: isso
registraria a revisão nova sem aplicar sua migração. Bancos vazios devem
receber `upgrade head` diretamente, sem `stamp`.

O boot atual possui reparo limitado de colunas ausentes (compatibilidade com
volumes antigos). Ele não substitui a migração Alembic: as chaves estrangeiras,
índices e backfill devem ser validados no banco real. A aplicação da migração
não ativa por si só o fluxo de credenciais e o motor de elegibilidade; esses
continuam como etapas de implementação da V1.

### Validações após migração

```sql
SELECT version_num FROM alembic_version;
SELECT COUNT(*) FROM usuarios;
SELECT COUNT(*) FROM reservas;
SELECT COUNT(*) FROM veiculos;
SELECT id, usuario_id, placa, categoria, motorizacao
FROM veiculos ORDER BY criado_em DESC LIMIT 10;
```

A quantidade de reservas/usuários não deve diminuir; reservas legadas
continuam com `veiculo_id = NULL`. Nunca executar `downgrade` em dados reais
sem backup, pois remove as novas tabelas e seus registros.
