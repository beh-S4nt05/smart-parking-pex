# Marcas de Entrega — SmartParking (PEX)

![Rubrica de entregas](marcas-de-entrega.png)

A tabela da rubrica oficial (total 10 pontos) é a régua do projeto: cada marca
abaixo diz **o que já está provado no repositório** e **o que falta** para a
banca fechar o ponto. Atualizar o "Status" a cada revisão.

| # | Critério         | Deadline | Peso | Status                          |
| - | ---------------- | -------- | ---- | ------------------------------- |
| 1 | Banco modelado   | 10/09    | 1    | ✅ Entregue                     |
| 2 | MVP operacional  | 22/10    | 2    | 🎯 **Desta entrega** (20/10)    |
| 3 | Relatórios       | 02/11    | 1    | ⚠️ Fluxo+Ocupação prontos no back |
| 4 | Testes & Docs    | 09/11    | 1    | ⚠️ Docs ✅, testes a escrever    |
| 5 | Entrega Integrada| 12/11    | 5    | ⬜ Plano de fechamento abaixo   |

---

## 1️⃣ Banco de dados modelado — 10/09 · peso 1 ✅

Modelagem completa em `src/backend/models/db_models.py` — **10 tabelas, 47
relacionamentos/FKs, 31 campos indexados** (SQLAlchemy + Postgres 15):

| Tabela                 | Papel no domínio                                                        |
| ---------------------- | ----------------------------------------------------------------------- |
| `usuarios`             | Motorista / Gestor / Financeiro / Admin — roles, credenciais, bloqueio  |
| `estacionamentos`      | Filiais: endereço, horários, taxa base, capacidade                       |
| `andares`              | Planta por filial (aceita subsolo negativo)                               |
| `vagas`                | Vaga física com estado (livre/ocupada/manutenção/reservada)              |
| `reservas`             | Ciclo entrada→saída: placa, valores, QR de vínculo                        |
| `configuracoes_precos` | Tarifação por andar/tipo de vaga                                          |
| `historicos`           | Auditoria automática de entrada/saída/alteração                           |
| `cupons_desconto`      | Campanhas com validade e limite de uso                                    |
| `pagamentos`           | Fluxo financeiro (método, valor, estorno)                                 |
| `fechamentos_caixa`    | Fechamento diário por filial                                              |

Extras que contam a favor: criação de schema automática no boot
(`Base.metadata.create_all`), **seed demo** idempotético (`seed_demo.py`,
8 shoppings de Manaus) e fallback SQLite só em dev (desligável com
`DB_AUTO_SQLITE=false` — o compose de produção já liga o modo estrito).

## 2️⃣ MVP operacional — 22/10 · peso 2 🎯 (esta entrega)

MVP "operacional" = cadeia inteira **reproduzível em qualquer máquina**. Desta
entrega:

- **Conserto da cadeia Docker→Nginx→API** (estava quebrada em 4 pontos — 502
  por bind `localhost` do gunicorn, conf do nginx instalado em lugar morto,
  zonas de rate limit inexistentes, `400 Invalid host header` em produção):
  `src/nginx/Dockerfile`, `src/nginx/default.conf`, `src/backend/gunicorn_config.py`,
  `src/docker-compose.yml`.
- **Rota `GET /health`** + healthcheck real no compose (nginx só sobe com a API viva).
- **`TRUSTED_HOSTS` configurável** (era hardcoded localhost-only; a banca por IP
  da LAN não funcionaria em produção).
- **`scripts/smoke_mvp.sh`**: prova a cadeia em 1 comando (health → lista → login
  admin → CRUD com cascata → bloqueio sem token), na 8000 direta ou via `BASE_URL=http://localhost` (nginx).

**Como validar em 2 minutos:**

```bash
cd src && docker compose up -d --build && cd ../..
./scripts/smoke_mvp.sh                          # API direta
BASE_URL=http://localhost ./scripts/smoke_mvp.sh # via nginx — cadeia completa
```

**Checklist do dia 22 (rodar na véspera na máquina da apresentação):**
banco limpo (`docker compose down -v && up -d --build`) → login `admin@smartparking.com/admin123`
→ painel: novo estacionamento + andares + vagas em lote → criar usuário gestor →
celular no mesmo Wi-Fi: `npx expo start` (`.env` com `EXPO_PUBLIC_API_URL=http://<IP-da-máquina>:8000`)
→ cadastro motorista → explorar → reservar → entrar com QR → saída.
Se travar em algo "sem dados", seguir as Achas de configuração do README.

## 3️⃣ Relatórios prontos — 02/11 · peso 1 ⚠️ (backend 50% já existe)

**Já implementado** em `src/backend/api/api.py` + `core/relatorio_service.py`:

- `GET /api/relatorios/fluxo?periodo=diario|semanal|mensal[&estacionamento_id=]` — entradas/saídas;
- `GET /api/relatorios/ocupacao?periodo=...` — taxa de ocupação + dados de mapa de calor por andar.

Falta para fechar a marca:

- `GET /api/relatorios/financeiro` (receita por dia/método em `pagamentos`, estornos,
  cupons usados, ligação com `fechamentos_caixa`) e `.../rotacao` (tempo médio por vaga);
- **Export CSV** via `StreamingResponse` (sem dependência nova);
- **Gating de acesso**: hoje as duas rotas acima estão no router público `/api` —
  mover para exigir role (`admin`/`financeiro`/`gestor` do próprio estacionamento);
- **Aba "Relatórios" no painel** (roles com permissão), reaproveitando a UI de
  filtros já existente em `src/app/dashboard.tsx`.

## 4️⃣ Testes & Documentação — 09/11 · peso 1 ⚠️

- **Docs:** já em `src/docs/` — `INTEGRACAO_FRONTEND.md` (contrato de rotas),
  `PROTECAO_REQUISICOES.md`/`SEGURANCA_*` (HMAC/TLS), `NGINX_EXPLICADO.md`
  (teoria do conf atual), `docker-commands.md`, README com Achas de config.
  Falta: adicionar seção de Relatórios quando a marca 3 sair.
- **Testes (a escrever):** `pytest` + `TestClient` do FastAPI em
  `src/backend/tests/`, rodando em SQLite (não exige Docker), com deps só de
  dev no requirements-dev. Cobertura-alvo (fluxos de peso): auth (login e-mail/
  telefone, refresh, bloqueado→401), cotação→reserva→saída (vaga livre→ocupada→
  livre), permissões do admin (gestor pode o próprio parking, 403 fora dele),
  cupom (válido/expirado/limite). O `scripts/smoke_mvp.sh` já serve de aceite
  manual integrado.

## 5️⃣ Entrega do Projeto Integrado (Funcional) — 12/11 · peso 5 ⬜

Fecha o sistema inteiro funcionando de ponta a ponta (mobile + web + painel +
relatórios + testes). Hardening programado — parte já preparada nesta entrega:

- `ENVIRONMENT=production` de verdade: TLS no nginx (guia em
  `SEGURANCA_TLS_WIRESHARK.md`), `TRUSTED_HOSTS` com o domínio, `SECRET_KEY` e
  `APP_SIGNING_SECRET` fortes (a chave de assinatura precisa ser **a mesma** no
  app — paridade documentada em `requestSigner.ts`);
- **Migrar sessões do simulador/QR e o cache anti-replay para o banco/Redis** →
  libera `GUNICORN_WORKERS>1` (hoje travado em 1 por estado em memória — ver
  comentário em `gunicorn_config.py`);
- Backup do volume Postgres (`pg_dump` agendado) + rotina de restore documentada;
- Leitura do **QR pela câmera** do celular no check-in/check-out (entrada/saída reais);
- Manual do usuário com prints + roteiro de apresentação.

---

*Legenda de status: ✅ entregue/comprovado · 🎯 foco do prazo atual · ⬜ planejado · ⚠️ parcial.*
*Preencher a coluna "Avaliado" da tabela da rubrica com a data da revisão do professor.*
