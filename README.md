# 🅿️ Smart Parking — Monitoramento Inteligente de Vagas

**Aplicação para monitorar vagas de estacionamento de shoppings em tempo real** —
com dashboard, mapa de vagas por andar e simulador de sensores por QR Code.

*Projeto PEX · Manaus/AM · MVP para apresentação em **12/10/2026***

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![React Native](https://img.shields.io/badge/React_Native-0.88-61DAFB?logo=react&logoColor=black)
![Expo](https://img.shields.io/badge/Expo_SDK-58-000020?logo=expo&logoColor=white)
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
  - [👥 Equipe e licença](#-equipe-e-licença)

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
| **Frontend mobile + web** | React Native 0.88 + Expo SDK 58 (versões **fixas/exatas** em `package.json`), **um código para Android/iOS/Web** (react-native-web), TypeScript estrito | `src/frontend/smart-parking/` |
| **UI cross-platform** | NativeWind (Tailwind no RN), componentização, design responsivo sem CSS grid, acessibilidade de toque (Pressable) | `src/components/` |
| **Estado e integração** | React Context + hooks customizados, interceptors Axios (token + refresh automático + assinatura), storage seguro multiplataforma | `src/context/`, `src/hooks/`, `src/services/` |
| **DevOps/Infra** | Docker Compose (nginx + backend + postgres + pgadmin), proxy reverso com load balancing (`least_conn`), health checks | `src/docker-compose.yml`, `src/nginx/` |
| **Qualidade** | Testes (pytest), smoke tests shell, validação estática (tsc, expo export, expo-doctor), QA de UI/UX medido no pré-render web, rubrica por marca | `src/backend/tests/` · `scripts/` · `src/docs/MARCAS_ENTREGA.md` · `src/docs/QA_UI_UX.md` |
| **Documentação** | SDD v0.3 (contrato executável com evidências) + 13 documentos técnicos — destaque para o [`MAPA_APLICACAO.md`](src/docs/MAPA_APLICACAO.md) (índice do sistema inteiro e do fluxo de acesso) | `src/docs/` |

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

> **📅 Marcas de entrega (PEX):** os 5 critérios oficiais — peso, deadline e status
> item a item — estão em [src/docs/MARCAS_ENTREGA.md](src/docs/MARCAS_ENTREGA.md):
> Banco modelado (10/09 ✅) · **MVP operacional (22/10 🎯)** · Relatórios (02/11) ·
> Testes & Docs (09/11) · Entrega Integrada Funcional (12/11, peso 5).

---

## 🚀 Como executar

### Pré-requisitos

- [Docker + Docker Compose](https://docs.docker.com/) (recomendado) **ou** Python 3.11 + PostgreSQL 15
- [Node.js 24](https://nodejs.org/) + npm
- Celular com **Expo Go** (opcional, para testar no Android/iOS)

### 1️⃣ Backend + Banco (Docker)

```bash
./scripts/docker.sh up            # (re)gera as imagens, sobe nginx (80) · backend (8000) ·
                                  # postgres (5432) · pgadmin (5050) e roda o smoke da cadeia
./scripts/docker.sh acesso        # auditoria de controle de acesso (27 checagens: anon/papéis/escopo)
./scripts/docker.sh reset         # apaga volume + rebuilda + smoke — "dia de apresentação" limpo
./scripts/docker.sh logs          # segue backend+nginx quando der 502/400 na banca
```

> **Notas do stack Docker** (corrigido em 20/10 — antes dessas correções a cadeia
> Nginx→API **não podia** funcionar, dava 502/400 ou "Welcome to nginx" puro):
> - `src/nginx/Dockerfile` agora instala o `default.conf` em **conf.d/** (o `COPY . /etc/nginx/`
>   antigo deixava o arquivo onde o nginx nunca lê) e o `default.conf` declara as **zonas**
>   `req_limit_per_ip`/`login_limit`/`conn_limit_per_ip` que antes eram usadas sem existir
>   (`nginx -t` falhava → crash-loop). Editou conf? Rebuilde (`--build`) — a config vai **assa-
>   da na imagem**, sem bind mount.
> - `gunicorn_config.py`: bind `0.0.0.0:8000` (com `localhost` o nginx, de outro container,
>   levava connection refused) e `GUNICORN_WORKERS=1` enquanto sessões do simulador/QR e o
>   cache anti-replay forem memória de processo.
> - Backend no container roda `ENVIRONMENT=staging` (assinatura HMAC/trusted-host liberados
>   p/ demo por IP na LAN) e `DB_AUTO_SQLITE=false` (sem dados fantasmas em SQLite).
>   Produção real = `production` + `TRUSTED_HOSTS` + segredos fortes — ver `.env.example`.

### 2️⃣ Backend local (alternativa sem Docker)

```bash
cd src/backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env-sample .env                                 # ajuste SECRET_KEY e APP_SIGNING_SECRET
python seed_demo.py                                 # popula os 8 shoppings de Manaus (demo)
python main.py                                      # API em http://localhost:8000
```

### 2.5️⃣ "Está sem conexão?" — um comando responde

```bash
./scripts/check_conexao.sh          # diagnóstico: .env, porta, firewall/LAN, CORS, Metro, Docker
./scripts/check_conexao.sh --fix    # conserta o item 1 sozinho (QA-101: linha ativa no .env)
```

Exit code `0` = conexão validada ponta a ponta (health → login → /me → proxima-vaga →
CORS), `1` = o primeiro ✘ impresso é exatamente o que bloqueia. É o gate de véspera de
banca: roda de qualquer pasta, sem dependência além de `curl`.

### 3️⃣ Frontend (Expo)

```bash
cd src/frontend/smart-parking
npm ci --no-audit --no-fund
cp .env.example .env    # opcional: o app resolve a URL sozinho por plataforma
                        # (web → host atual; Expo Go → IP do "npx expo start");
                        # o .env só p/ porta != 8000, túnel ou produção
npx expo start          # pressione: w (web) · a (Android) · i (iOS) · ou escaneie o QR
```

Para celular físico, prefira `./scripts/dev-front.sh`: ele atualiza o IP da LAN
e limpa o cache do Expo. O guia [`CONECTIVIDADE_MOBILE.md`](src/docs/CONECTIVIDADE_MOBILE.md)
separa Expo Go, emulador, development build e produção, inclui a permissão de
Rede Local do iPhone e mostra como liberar somente o IP privado da API — sem
CORS `*`, ATS arbitrário ou cleartext Android global.

> O SDK 58 está **fixado** no `package.json` e no `package-lock.json`. Para
> instalar ou recuperar o frontend, use `npm ci` — não `npm install`, que pode
> recalcular a árvore. `npm install` só é apropriado quando você pretende
> alterar dependências de propósito.

#### 🔄 Verificação e atualização nativa do SDK

```bash
cd src/frontend/smart-parking
npm run check-sdk      # canal latest + pins exatos + lockfile/node_modules
npm run update-sdk     # expo install expo@latest + --fix, restaurando pins exatos
npm run doctor         # diagnóstico oficial completo (requer acesso à API do Expo)
npm run check-native   # export Hermes Android/iOS/Web + prebuild em pasta temporária
```

A CI executa essas verificações em pushes e PRs. O workflow
[`expo-sdk-update.yml`](.github/workflows/expo-sdk-update.yml) também consulta o
canal estável diariamente e abre um PR quando encontra atualização. Não há push
nem merge automático na `main`: `expo-doctor`, TypeScript, export e prebuild
precisam passar antes da criação do PR. Teste em aparelho físico continua sendo
obrigatório antes de publicar uma build.

> **Achas de configuração (importante pro time todo):**
> - Os overrides do app são `EXPO_PUBLIC_API_URL_WEB`, `EXPO_PUBLIC_API_URL_MOBILE`
>   e o global `EXPO_PUBLIC_API_URL`. Env chamada `DEFAULT_API_URL`
>   **não existe** — se alguém colocar no `.env`, é ignorada. Sem env, o app resolve
>   sozinho (ACH-21): **web** usa o próprio host (`:80`/`:443` = same-origin; dev
>   `:8081` → mesma máquina na `:8000`); **Expo Go** usa o IP LAN que o próprio
>   `npx expo start` publica (`hostUri`); **emulador Android** → `10.0.2.2`. Uma
>   API só — **não** existe "API da web" e "API do mobile": o que muda é a
>   resolução do host no cliente.
> - Backend: o `.env` vive em `src/backend/` (`cp .env.example .env`). Porta 8000
>   ocupada? `PORT=8010` lá **e** no env do front, com `npx expo start -c`.
> - Se o Postgres cair e `DB_AUTO_SQLITE=true`, o app **silencia** e usa um SQLite
>   oculto — os dados entram num banco e você olha noutro. Em dupla/trio, prefira
>   `DB_AUTO_SQLITE=false` para o erro aparecer na hora.

O **web e o mobile usam as mesmas rotas** (layout responsivo): `/` home ·
`/login` (e-mail **ou** telefone) · `/cadastro` · `/explorar` ·
`/shopping/{id}` mapa de vagas · `/reservas` · `/dashboard` painel ·
`/simulador-qr` + `/simulador` (fluxo do QR). Contrato completo em
[`src/docs/INTEGRACAO_FRONTEND.md`](src/docs/INTEGRACAO_FRONTEND.md).

> 📖 **Documentação da API:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger interativo)
> 🐘 **PgAdmin:** [http://localhost:5050](http://localhost:5050) · `admin@admin.com` / `admin`

#### 🧯 `expo install --check` ou `npm audit fix --force` misturou as versões?

**Não aceite o “Fix dependencies?” nem rode `npm audit fix --force` para
consertar o SDK.** O `expo install` usa o pacote `expo` que está em
`node_modules`; se essa pasta ainda for do SDK 57, ele propõe dependências do
57 mesmo com o `package.json` atualizado. Já o `audit fix --force` pode trocar
majeures sem relação com o problema (no incidente de 23/10, chegou a sugerir
Expo 44, RN 0.72 e NativeWind 2). O resultado é uma árvore mista — não uma
correção de vulnerabilidades.

Recupere **somente os arquivos de dependências** e reinstale do lockfile. Na
raiz do repositório, primeiro desfaça as alterações automáticas e depois
atualize a cópia, se necessário:

```bash
# opcional, mas recomendado: guarda o diff antes de descartar as alterações
# automáticas; não toca em código, telas, .env ou backend
git diff -- src/frontend/smart-parking/package.json \
            src/frontend/smart-parking/package-lock.json > /tmp/smart-parking-deps.diff

git restore --source=HEAD -- \
  src/frontend/smart-parking/package.json \
  src/frontend/smart-parking/package-lock.json

# só se a cópia ainda não tiver o commit 3a28ae9 (ou posterior):
git pull --ff-only
git log -1 --oneline

cd src/frontend/smart-parking
rm -rf node_modules .expo
npm ci --no-audit --no-fund

# tem que imprimir 58.0.20; se imprimir outra major, pare e confira a cópia/branch
node -p "require('./node_modules/expo/package.json').version"
npx expo start -c
```

Se houver alterações manuais nesses dois arquivos, preserve-as no diff e
reaplique depois — o `restore` acima descarta apenas as mudanças não
commitadas deles. O `git log` precisa mostrar `3a28ae9` ou um commit posterior
do SDK 58; não tente fazer o upgrade restaurando arquivos de outra cópia.

Depois do `npm ci`, o `npx expo install --check` confirma a compatibilidade com
o SDK instalado e também roda na CI. Se ele anunciar uma major inesperada,
pressione `Ctrl+C`, repita a checagem do `node_modules` e use somente
`npm run update-sdk` para uma atualização intencional. `npm audit` pode ser lido
à parte, mas seus avisos transitivos não devem derrubar os pins do SDK.

#### 📱 Expo Go no celular: "Failed to download remote update"

Esse erro **não é do código do app** — o projeto não usa OTA/EAS Update (não há
`expo-updates` nem `eas.json`); é o Expo Go tentando baixar o bundle do servidor
da Expo em vez de conectar ao Metro do PC. Cheque nesta ordem:

1. **Expo Go compatível com o SDK 58 do projeto** — o Expo Go das lojas segue o
   SDK mais recente e a build para o SDK 58 saiu ~2–3 semanas após o release
   (15/10/2026). Se a sua Play Store ainda mostrar só o Expo Go do SDK 57, ele
   NÃO abre projeto 58 ("Failed to download remote update" é o sintoma): aguarde
   a atualização do app OU rode por navegador (`npx expo start --web`) / Android
   Studio emulator, ou migre para dev build (`npx expo run:android`).
2. **Abra pelo QR do terminal**, não pela aba "Projects/Recentes" do Expo Go (esse
   caminho vai no expo.dev, que exige projeto publicado → update remoto → falha).
   Rode `npx expo start` no terminal e escaneie o QR dali (ou digite
   `exp://IP-DO-PC:8081` no Expo Go → "Enter URL").
3. **Wi-Fi que isola dispositivos** (comum em rede de campus/hotel — "AP
   isolation"): o Metro na 8081 nunca responde e o Expo Go desiste para o remoto.
   Teste no navegador do celular: `http://IP-DO-PC:8081/status` deve responder
   qualquer coisa (ex.: `Bundler activity: none`). Se não abre, sua rede isola →
   use túnel, que não exige nada novo no projeto: `npx expo start --tunnel`
   (o `npx` baixa o `@expo/ngrok` sob demanda).

Desde a correção de 22/10 **não precisa configurar nada** para o celular achar a
API: o Expo Go resolve o IP do PC sozinho (QR do `npx expo start`). Se um dia o
`.env` fixar `EXPO_PUBLIC_API_URL`, ele passa a mandar em tudo — trocas no `.env`
exigem `npx expo start -c`.

#### ⚠️ "expo config"/"expo start" falhando com stack de OUTRA pasta? É o CLI global legado

Se o erro apontar caminhos como `~/.nvm/.../node_modules/expo-cli` (e o banner
*"The legacy expo-cli does not support Node +17"*), **não é o projeto** quem está
rodando — é o `expo-cli` global deprecado sequestrando o `npx expo` porque o
binário local está ausente/quebrado. Conserto na ordem:

1. `npm rm -g expo-cli` (só este pacote; se existir `expo-doctor` global antigo, remova também);
2. dentro de `src/frontend/smart-parking`: `rm -rf node_modules .expo && npm ci`;
3. confira `ls node_modules/.bin/expo`. Se o `npm ci` termina bem mas o `.bin`
   some, o filesystem não cria symlinks — clone em HD/partição **NTFS/exFAT**
   (comum em dual boot, pasta montada em `/media/...`) → mova o repositório para
   a partição Linux (ext4) e reinstale lá.

Os scripts do projeto já chamam `npx expo ...`, que prioriza o binário local.

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
│   ├── docs/                    # 14 documentos técnicos (mapa + QA de UI/UX)
└── LICENSE                      # MIT
```

---

## ✅ Validação e testes

```bash
# Backend — suíte pytest (31 testes: fuso/tarifa/cupom/relatórios/expiração de
# reserva/matriz BOLA/guards de produção). SQLite isolado, SEM Docker, SEM servidor:
cd src/backend && pip install -r requirements-dev.txt && pytest tests -q

# Backend — aceite E2E contra a API viva (com o servidor de pé):
./scripts/smoke_mvp.sh    http://localhost:8000   # 10 checks de fluxo de dados
./scripts/smoke_acesso.sh http://localhost:8000   # 27 checks de papel × recurso (BOLA)

# Sensores IoT (RF-45): emite uma chave pelo admin e fala com a API sem JWT
curl -s -X POST http://localhost:8000/api/admin/sensores \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"estacionamento_id":"E0","codigo":"SNS-A01"}'
curl -s -X POST http://localhost:8000/api/sensores/eventos \
  -H "X-Device-Key: SPK-..." -H "Content-Type: application/json" \
  -d '{"eventos":[{"seq":1,"codigo_vaga":"A01","status":"ocupada"}]}'

# Stack completo com Postgres + smoke da cadeia:
./scripts/docker.sh up      # sobe db+api+nginx e roda os dois smokes
./scripts/docker.sh smoke

# Frontend — typecheck e build web:
cd src/frontend/smart-parking && npx tsc --noEmit && npx expo export --platform web
```

> **Honestidade (SDD M4-04):** as versões antigas deste README apontavam para
> `scripts/validacao/` e `src/docs/VALIDACAO_E_CONFORMIDADE.md`, que não existem
> neste repositório — a régua real é [`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md)
> e o [`src/docs/SDD.md`](src/docs/SDD.md) (status por requisito + §12 de evidências).
> Tudo acima foi executado de fato em 22/10 (pytest 25/25 · smokes 10/10 e 27/27 · tsc limpo).



---

## 🗺️ Roadmap

Régua oficial = as 5 marcas da rubrica (detalhe e evidência por marca em
[`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md)):

| Data | Marco | Status |
|---|---|---|
| 10/09/2026 | 1️⃣ Banco de dados modelado | ✅ |
| 22/10/2026 | 2️⃣ MVP operacional (API+app+Docker+acessos) | ✅ |
| 02/11/2026 | 3️⃣ Relatórios (fluxo/ocupação/rotação/financeiro + CSV + aba no painel) | ✅ 22/10, antecipado |
| 09/11/2026 | 4️⃣ Testes & Documentação (pytest em CI + SDD) | 🟡 suíte+CI prontas; SDD em `src/docs/SDD.md` |
| 12/11/2026 | 5️⃣ Entrega Integrada Funcional | ⬜ plano na doc de marcas |

---

## 👥 Equipe e licença

| Papel no projeto PEX | Integrante(s) |
|---|---|
| ✍️ Autor / Liderança | **Breno Santos** |
| 🛠️ Desenvolvimento | **Gabriel Almeida** · **Breno Santos** |
| 🎨 Desenvolvimento de UI | **Jonas Almeida** |

Projeto acadêmico PEX — Manaus/AM · contato: <behsolutionsandautomations@gmail.com>

Distribuído sob licença **MIT** — veja [LICENSE](LICENSE).

Feito com 💙 para facilitar a ida ao shopping · **Smart Parking Shoppings**
