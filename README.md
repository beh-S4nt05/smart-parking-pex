# 🅿️ Smart Parking — Monitoramento Inteligente de Vagas

**Aplicação para monitorar vagas de estacionamento de shoppings em tempo real** —
com dashboard, mapa de vagas por andar e simulador de sensores por QR Code.

*Projeto PEX · Manaus/AM · MVP para apresentação em **12/10/2026***

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![React Native](https://img.shields.io/badge/React_Native-0.86-61DAFB?logo=react&logoColor=black)
![Expo](https://img.shields.io/badge/Expo_SDK-57-000020?logo=expo&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 Sumário

- [🅿️ Smart Parking — Monitoramento Inteligente de Vagas](#️-smart-parking--monitoramento-inteligente-de-vagas)
  - [📖 Sumário](#-sumário)
  - [🎯 Sobre o projeto](#-sobre-o-projeto)
  - [⚡ Funcionalidades](#-funcionalidades)
    - [Entrega atual (MVP)](#entrega-atual-mvp)
    - [Roadmap (fase 2)](#roadmap-fase-2)
  - [💡 Habilidades demonstradas](#-habilidades-demonstradas)
  - [🏗️ Arquitetura](#️-arquitetura)
  - [🚀 Como executar](#-como-executar)
    - [Pré-requisitos](#pré-requisitos)
    - [1️⃣ Backend + Banco (Docker)](#1️⃣-backend--banco-docker)
    - [2️⃣ Backend local (alternativa sem Docker)](#2️⃣-backend-local-alternativa-sem-docker)
    - [3️⃣ Frontend (Expo)](#3️⃣-frontend-expo)
  - [📱 Como usar a aplicação](#-como-usar-a-aplicação)
    - [🧑‍💻 Fluxo do motorista (app mobile/web)](#-fluxo-do-motorista-app-mobileweb)
    - [👨‍💼 Fluxo do administrador (simulador de sensores por QR Code)](#-fluxo-do-administrador-simulador-de-sensores-por-qr-code)
    - [🔑 Usuários de demonstração (criados pelo seed)](#-usuários-de-demonstração-criados-pelo-seed)
  - [🔌 API](#-api)
  - [🛡️ Segurança](#️-segurança)
  - [📁 Estrutura do repositório](#-estrutura-do-repositório)
  - [✅ Validação e testes](#-validação-e-testes)
  - [🗺️ Roadmap](#️-roadmap)
  - [👤 Autor e licença](#-autor-e-licença)

---

## 🎯 Sobre o projeto

**Problema:** perder tempo procurando vaga em shopping — e o estacionamento não ter visão de ocupação em tempo real.

**Solução:** o Smart Parking centraliza o **monitoramento inteligente de vagas** de uma rede de shoppings (Manaus/AM):

| Para o público | Para o estacionamento |

|---|---|
| Ver vagas disponíveis **em tempo real**, por shopping e andar | **Dashboard** com ocupação geral, por andar e por shopping |
| Consultar a **próxima vaga livre** (com prioridade por tipo: PCD, idoso, moto…) | **Simulador de sensores por QR Code** — entrada/saída de veículos em lote |
| Experiência **mobile + web** com o mesmo código | Base pronta para **sensores IoT reais** no futuro |

> **Status:** MVP em desenvolvimento — 🎯 apresentação em **12/10/2026**. Reservas e pagamentos entram na fase 2.

---

## ⚡ Funcionalidades

### Entrega atual (MVP)

- 📊 **Dashboard em tempo real** — vagas livres/ocupadas/reservadas, taxa de ocupação e tempo médio de permanência
- 🗺️ **Mapa de vagas por andar** — status individual de cada vaga (livre, ocupada, reservada, inativa)
- 📱 **QR Code do simulador** — a API gera uma URL por estacionamento/andar; o admin abre a página no celular e **adiciona/remove veículos** (inclusive **em lote**), simulando sensores
- 👨‍💼 **Área administrativa** — gestão de estacionamentos, andares, vagas (individual ou lote), usuários e papéis
- 🔐 **Segurança de produção** — JWT, assinatura HMAC anti-replicação, rate limiting duplo, middlewares de proteção
- 🌆 **Dados reais de Manaus** — 8 shoppings parceiros com endereços reais

### Roadmap (fase 2)

- 🔖 Reserva antecipada de vaga · 💳 Pagamento de estadia (PIX, cartão, dinheiro) · 🎟️ Cupons · 💰 Caixa por turno
- 📈 Relatórios financeiros · 📲 Login social (Google/Apple) · 🔌 Sensores IoT reais

---

## 💡 Habilidades demonstradas

| Área | Habilidades | Onde aplicado no código |

|---|---|---|
| **Arquitetura de software** | Arquitetura limpa e desacoplada (API → regras → dados), SOLID, separação de responsabilidades | `api/` só trata HTTP · `rules/` concentra a lógica · `models/` cuida da persistência |
| **API REST** | Design RESTful, documentação OpenAPI/Swagger automática, códigos HTTP corretos, validação de contratos | `api/api.py`, `api/admin.py` · `/docs` |
| **Backend** | FastAPI, Python 3.11, workers com Gunicorn+Uvicorn, pool de conexões | `main.py`, `gunicorn_config.py` |
| **Banco de dados** | PostgreSQL, ORM SQLAlchemy 2.0 (relacionamentos 1-∞, cascata, UUIDs), migrations manuais, fallback automático SQLite | `models/database.py`, `models/db_models.py` |
| **Validação** | Pydantic v2 (schemas de entrada/saída), e-mail, limites, padrões | `models/schemas.py` |
| **Autenticação** | JWT (access 15 min + refresh 7 dias), hash bcrypt com salt, papéis e permissões (admin/gestor/financeiro/motorista) | `core/security.py`, `core/deps.py` |
| **Segurança de APIs** | Assinatura **HMAC-SHA256** com anti-replay (timestamp + nonce), rate limiting em 2 camadas, anti-SQLi, headers de segurança, bloqueio de scanners | `core/request_validator.py`, `core/rate_limiter.py`, `core/security_middleware.py`, `nginx/` |
| **Frontend mobile + web** | React Native 0.86 + Expo SDK 57, **um código para Android/iOS/Web** (react-native-web), TypeScript estrito | `src/frontend/smart-parking/` |
| **UI cross-platform** | NativeWind (Tailwind no RN), componentização, design responsivo sem CSS grid, acessibilidade de toque (Pressable) | `src/components/` |
| **Estado e integração** | React Context + hooks customizados, interceptors Axios (token + refresh automático + assinatura), storage seguro multiplataforma | `src/context/`, `src/hooks/`, `src/services/` |
| **DevOps/Infra** | Docker Compose (nginx + backend + postgres + pgadmin), proxy reverso com load balancing (`least_conn`), health checks | `src/docker-compose.yml`, `src/nginx/` |
| **Qualidade** | Testes (pytest), smoke tests shell, validação estática (tsc, expo export, expo-doctor), matriz de conformidade | `scripts/validacao/` |
| **Documentação** | 12 documentos técnicos (integração, segurança, módulos, guias) + plano e validação | `src/docs/` |

---

## 🏗️ Arquitetura

``` text
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│  App — Expo (Android/iOS/Web)│  HTTPS │  Nginx · proxy reverso + LB      │
│  TypeScript · NativeWind     │───────▶│  rate limit · TLS · segurança    │
│  Axios + assinatura HMAC     │        └──────────────┬───────────────────┘
└─────────────────────────────┘                       │
        Admin: QR do simulador           ┌─────────────▼─────────────┐
        (página de operação) ───────────▶│  FastAPI · Gunicorn       │
                                         │  api/  rules/  models/    │
   Sensores IoT (futuro) ── PATCH ──────▶│  JWT · HMAC · rate limit  │
                                         └─────────────┬─────────────┘
                                         ┌─────────────▼─────────────┐
                                         │  PostgreSQL 15            │
                                         │  (SQLite automático em dev)│
                                         └───────────────────────────┘
```

**Modelo de dados:** `Estacionamento → Andar → Vaga`, com `Histórico` automático de entrada/saída, `Reserva`, `Pagamento`, `Cupom`, `FechamentoCaixa` e `Usuário` com papéis.

---

## 🚀 Como executar

### Pré-requisitos

- [Docker + Docker Compose](https://docs.docker.com/) (recomendado) **ou** Python 3.11 + PostgreSQL 15
- [Node.js 24](https://nodejs.org/) + npm
- Celular com **Expo Go** (opcional, para testar no Android/iOS)

### 1️⃣ Backend + Banco (Docker)

```bash
cd src
docker compose up -d --build      # sobe nginx (80) · backend (8000) · postgres (5432) · pgadmin (5050)
```

### 2️⃣ Backend local (alternativa sem Docker)

```bash
cd src/backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env-sample .env                                 # ajuste SECRET_KEY e APP_SIGNING_SECRET
python seed_demo.py                                 # popula os 8 shoppings de Manaus (demo)
python main.py                                      # API em http://localhost:8000
```

### 3️⃣ Frontend (Expo)

```bash
cd src/frontend/smart-parking
npm install
# aponte para o IP da sua máquina (celular na mesma rede Wi-Fi):
export EXPO_PUBLIC_API_URL=http://SEU_IP_LOCAL:8000
npx expo start          # pressione: w (web) · a (Android) · i (iOS) · ou escaneie o QR
```

> 📖 **Documentação da API:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger interativo)
> 🐘 **PgAdmin:** [http://localhost:5050](http://localhost:5050) · `admin@admin.com` / `admin`

---

## 📱 Como usar a aplicação

### 🧑‍💻 Fluxo do motorista (app mobile/web)

1. **Abra o app** — a tela inicial mostra os shoppings parceiros de Manaus e o painel de status
2. **Escolha um shopping** — o dashboard atualiza com vagas disponíveis, ocupação e tempo médio
3. **Explore o mapa de vagas** — veja o status por andar (🟢 livre · 🔴 ocupada · 🟡 reservada)
4. **Consulte a próxima vaga** — o motor de atribuição sugere a melhor vaga (priorizando PCD/idoso/moto)

### 👨‍💼 Fluxo do administrador (simulador de sensores por QR Code)

1. **Entre como administrador** (área restrita — somente o admin tem acesso)
2. **Gere o QR Code** de um estacionamento/andar
3. **Escaneie no celular** — abre a página de operação do andar
4. **Simule a movimentação:**
   - Toque em uma vaga para **ocupar/liberar**
   - Use as **ações em lote** (ex.: *"preencher 10 vagas"*, *"liberar todas"*)
5. **Veja o dashboard atualizar em tempo real** — cada operação gera o histórico de entrada/saída automaticamente

> 🔮 No futuro, **sensores reais** substituem o simulador usando a mesma API (`PATCH /api/vagas/{id}/status`).

### 🔑 Usuários de demonstração (criados pelo seed)

| Papel | E-mail | Senha | Pode |

|---|---|---|---|
| Administrador | `admin@smartparking.com` | `admin123` | tudo (inclui gerar QR do simulador) |
| Gestor | `gestor@smartparking.com` | `gestor123` | gerenciar o estacionamento vinculado |
| Financeiro | `financeiro@smartparking.com` | `financ123` | pagamentos e relatórios |
| Motorista | `motorista@smartparking.com` | `motor123` | usar o app |

---

## 🔌 API

**Autenticação:** `POST /auth/login` retorna `access_token` + `refresh_token` (JWT).
Rotas autenticadas usam `Authorization: Bearer <access_token>`.

| Método | Rota | Descrição | Auth |

|---|---|---|---|
| GET | `/api/estacionamentos` | Lista shoppings com vagas disponíveis | — |
| GET | `/api/estacionamentos/{id}/vagas` | Mapa de vagas por andar | — |
| GET | `/api/estacionamentos/{id}/proxima-vaga` | Próxima vaga livre (por tipo) | — |
| PATCH | `/api/vagas/{id}/status` | Atualiza status da vaga (sensor/simulador) | HMAC |
| PATCH | `/api/vagas/lote/status` | Atualização **em lote** | HMAC |
| POST | `/api/admin/simulador/qr` | Gera URL/QR do simulador (andar) | JWT admin |
| POST/GET/DELETE | `/api/reservas/*` | Reservas do motorista (fase 2) | JWT |
| GET | `/api/relatorios/fluxo` · `/ocupacao` | Fluxo de veículos e ocupação | — |
| * | `/api/admin/financeiro/*` | Tarifas, pagamentos, caixa, cupons | JWT+role |

**Exemplo rápido:**

```bash

curl http://localhost:8000/api/estacionamentos | python -m json.tool
```

---

## 🛡️ Segurança

O projeto aplica defesa em **múltiplas camadas**:

| Camada | Proteção |

|---|---|
| 🔏 **Assinatura HMAC-SHA256** | Toda escrita (POST/PUT/PATCH/DELETE) é assinada pelo app — requisições replicadas (Postman, scripts, DevTools) são bloqueadas |
| 🕐 **Anti-replay** | Timestamp (±5 min) + nonce único por requisição — requisições capturadas não podem ser repetidas |
| 🔑 **JWT + bcrypt** | Access token curto (15 min) + refresh (7 dias); senhas com hash bcrypt |
| ⚖️ **Rate limiting duplo** | Nginx (30 r/s geral · 5/min no login) + SlowAPI por usuário/IP |
| 🧱 **Middlewares** | Anti-SQLi/XSS, bloqueio de scanners, headers de segurança, ocultação de tecnologia |
| 👥 **Permissões por papel** | admin · gestor · financeiro · motorista — cada rota exige o papel correto |
| 🔒 **HTTPS/TLS** | Configuração TLS 1.3 + HSTS pronta (`nginx/`), SSL pinning previsto para o app |

---

## 📁 Estrutura do repositório

``` text
smart-parking-pex/
├── README.md                    ← você está aqui
├── src/
│   ├── docker-compose.yml       # nginx + backend + postgres + pgadmin
│   ├── backend/                 # FastAPI (arquitetura limpa)
│   │   ├── api/                 #   rotas (HTTP)
│   │   ├── rules/               #   regras de negócio
│   │   ├── models/              #   ORM + schemas
│   │   ├── core/                #   segurança, config, middlewares
│   │   └── seed_demo.py         #   dados dos 8 shoppings de Manaus
│   ├── frontend/smart-parking/  # Expo (Android · iOS · Web)
│   │   └── src/                 #   app · components · hooks · services · context
│   ├── nginx/                   # proxy reverso + load balancer
│   ├── docs/                    # 12 documentos técnicos
│   └── scripts/validacao/       # scripts de verificação (L1–L3)
└── LICENSE                      # MIT
```

---

## ✅ Validação e testes

```bash
# Frontend: TypeScript + HTML residual + bundles Android/Web + expo-doctor
./scripts/validacao/validar_frontend.sh

# Backend: smoke test da API viva (15 etapas)
./scripts/validacao/validar_backend_smoke.sh http://localhost:8000

# Segurança: paridade HMAC + anti-replay
python3 scripts/validacao/validar_assinatura.py
```

A conformidade do projeto é controlada pela **matriz de conformidade** em [`src/docs/VALIDACAO_E_CONFORMIDADE.md`](src/docs/VALIDACAO_E_CONFORMIDADE.md).

---

## 🗺️ Roadmap

| Data | Marco |

|---|---|
| 28/09–09/10/2026 | Execução das frentes: Frontend · Backend · Integração · Segurança · Simulador QR |
| 10–11/10/2026 | Folga para ajustes e ensaio |
| **12/10/2026** | 🎯 **Apresentação do MVP** (app + relatório + demo) |
| Fase 2 | Reservas · pagamentos (PIX/cartão) · cupons · caixa · sensores IoT reais |

---

## 👤 Autor e licença

**Breno Santos** — Manaus, AM · <behsolutionsandautomations@gmail.com>

Distribuído sob licença **MIT** — veja [LICENSE](LICENSE).

Feito com 💙 para facilitar a ida ao shopping · **Smart Parking Shoppings**
