# 🅿️ Smart Parking — Monitoramento Inteligente de Vagas

**Aplicação para monitorar vagas de estacionamento de shoppings em tempo quase real** — com dashboard, mapa de vagas por andar, simulador de sensores por QR Code e uma base pronta para IoT.

> **Projeto acadêmico PEX · FMM · Manaus/AM**
> Código, documentação e evidências organizados para a banca, para o time e para quem precisar manter o sistema.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)
![Expo](https://img.shields.io/badge/Expo-SDK%2058-000020?logo=expo&logoColor=white)
![React Native](https://img.shields.io/badge/React_Native-Web%20%2F%20Mobile-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-estrito-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Backend](https://img.shields.io/badge/backend-176%20pytest-2E7D32)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-green)

> ⚠️ **Estado atual (06/11/2026):** o trabalho foi mesclado em `main` pelo PR [#32](https://github.com/beh-S4nt05/smart-parking-pex/pull/32). Os arquivos `src/frontend/smart-parking/package.json` e `package-lock.json` foram **removidos do versionamento** a pedido do projeto. Um clone limpo, portanto, não contém os manifests exigidos por `npm ci`/Expo, e os jobs `frontend`/`ui` da CI falham no `actions/setup-node`. Os jobs de backend em Python 3.10 e 3.12 permanecem verdes. Veja [9.5 Limitações conhecidas](#limitacoes-conhecidas) e a [run 42311181364](https://github.com/beh-S4nt05/smart-parking-pex/actions/runs/42311181364).

---

## Sumário

- [1. Visão geral](#visao-geral)
- [2. Autores e Porquê](#autores-e-porque)
- [3. Conceitos](#conceitos)
- [4. Métodos e Estrutura](#metodos-e-estrutura)
- [5. Funcionalidades](#funcionalidades)
- [6. Como executar](#como-executar)
- [7. Como usar](#como-usar)
- [8. API](#api)
- [9. Segurança aplicada ao Projeto](#seguranca-aplicada)
  - [9.5 Limitações conhecidas](#limitacoes-conhecidas)
- [10. Qualidade, validação e testes](#qualidade-validacao-e-testes)
- [11. Roadmap](#roadmap)
- [12. Referência da faculdade](#referencia-da-faculdade)
- [13. Documentação](#documentacao)
- [14. Solução de problemas](#solucao-de-problemas)
- [15. Equipe, contato e licença](#equipe-contato-e-licenca)

---

<a id="visao-geral"></a>
## 1. Visão geral

### 1.1 O problema e a solução

| Para o público | Para o estacionamento |
|---|---|
| Perder tempo procurando vaga em shopping | Não ter visão confiável de ocupação em tempo real |
| Ver vagas disponíveis por shopping e por andar | Dashboard com ocupação geral, por andar, rotação e tempo médio |
| Consultar a **próxima vaga livre**, com prioridade por tipo: PCD, idoso, moto | Simulador de sensores por QR Code, com entrada/saída individual ou em lote |
| Usar a mesma experiência no celular e no navegador | Base pronta para sensores IoT reais, sem reescrever a API |

A solução centraliza o monitoramento de uma rede de **8 shoppings de Manaus/AM** em um backend FastAPI, um app Expo/React Native e uma stack Docker com Nginx e PostgreSQL.

### 1.2 Escopo

| Dentro desta entrega | Fora / fase 2 / documentado |
|---|---|
| Consulta pública de vagas por shopping e andar | Pagamento real de estadia por PIX/cartão |
| Dashboard e painel administrativo por papel | Integração com gateway de pagamento |
| Simulador de sensores por QR Code, somente admin | Sensores IoT físicos em produção |
| Relatórios de fluxo, ocupação, rotação e financeiro com CSV | Login social operacional (Google/Apple/Facebook) |
| Reservas básicas já existentes no app | Notificações push |
| Seed demo, Docker, smoke tests e suíte E2E de UI | Publicação em Play Store / App Store |
| Chave de dispositivo para ingestão idempotente de sensores | Check-in/check-out por câmera |

> **Regra de leitura:** se este README, o [`SDD.md`](src/docs/SDD.md) e o código divergirem, **o código é a fonte da verdade**. Divergência de documentação deve ser corrigida, não escondida.

### 1.3 Status resumido

| Área | Estado |
|---|---|
| Backend, regras de negócio, relatórios e segurança | ✅ Implementado e coberto por 176 testes |
| App mobile/web, UI/UX, cache offline e resiliência | ✅ Implementado; 22 jornadas Playwright registradas antes da remoção dos manifests |
| Docker, Nginx, PostgreSQL e smoke tests | ✅ Cadeia reproduzível |
| CI de backend (Python 3.10 / 3.12) | ✅ Verde |
| CI de frontend e UI | ❌ Bloqueada pela ausência dos manifests no repositório |
| Aparelho físico e instalação externa | ⬜ Não validado neste ambiente |

---

<a id="autores-e-porque"></a>
## 2. Autores e Porquê

### 2.1 Autores

| Integrante | Papel no projeto PEX |
|---|---|
| **Breno Santos** | Autor, liderança e desenvolvimento |
| **Gabriel Almeida** | Desenvolvimento |
| **Jonas Almeida** | Desenvolvimento de UI |

Fonte dos nomes e papéis: [`src/docs/README.md`](src/docs/README.md) e [`src/docs/SDD.md`](src/docs/SDD.md). O contato do projeto está na [seção 15](#equipe-contato-e-licenca).

### 2.2 Por que o projeto existe

1. **Problema urbano real:** em shoppings de Manaus, motoristas circulam sem informação de onde há vaga; o operador não consegue medir ocupação, rotação ou permanência.
2. **Objetivo acadêmico:** entregar um projeto de extensão PEX verificável, com banco modelado, MVP operacional, relatórios, testes e documentação rastreável para a banca da FMM.
3. **Objetivo de engenharia:** demonstrar arquitetura desacoplada, API REST, segurança em camadas, QA medido, DevOps e um único código para Android, iOS e Web.
4. **Objetivo de produto:** criar uma base evolutiva — primeiro com simulador por QR Code, depois com sensores IoT reais usando o mesmo contrato `PATCH /api/vagas/{id}/status`.

### 2.3 Para quem é

| Público | O que encontra aqui |
|---|---|
| Motorista | Home, exploração de shoppings, mapa de vagas, próxima vaga, login/cadastro, reservas e perfil |
| Administrador | Painel completo, usuários, CRUD de estacionamentos/andares/vagas, QR do simulador e chaves de sensor |
| Gestor | Painel com escopo restrito à própria filial |
| Financeiro | Relatórios, preços, pagamentos e CSV com escopo restrito à própria filial |
| Banca / orientação FMM | Rubrica, SDD, mapa da aplicação, evidências de execução e este README |
| Time de manutenção | Comandos, variáveis de ambiente, estrutura de pastas e solução de problemas |

### 2.4 O que este projeto **não** é

- Não é um gateway de pagamento nem processa PIX/cartão reais nesta entrega.
- Não é uma instalação de produção com TLS, domínio, backup e múltiplos workers já ativos.
- Não é uma frota de sensores IoT físicos; a ingestão por `X-Device-Key` existe, o hardware é fase 2.
- Não é um app publicado nas lojas nem validado em aparelho físico neste ambiente.
- Não é um exemplo de "segurança só no cliente": autorização, escopo e validação são decididos no servidor.

---

<a id="conceitos"></a>
## 3. Conceitos

### 3.1 Glossário do domínio

| Termo | Significado no projeto |
|---|---|
| **Estacionamento** | Unidade operacional: um shopping parceiro, com endereço, horários, capacidade e taxa base. |
| **Andar** | Piso do estacionamento; aceita numeração negativa para subsolo. |
| **Vaga** | Posição física com `status` (`livre`, `ocupada`, `reservada`, `inativa`) e `tipo` (comum, PCD, idoso, moto). |
| **Histórico** | Registro automático de entrada, saída e alteração de uma vaga; base dos relatórios de fluxo e ocupação histórica. |
| **Reserva** | Ciclo planejado de uso de uma vaga; expira automaticamente e libera a vaga presa. |
| **Próxima vaga** | Motor de atribuição que sugere a melhor vaga livre, considerando elegibilidade e prioridade por tipo. |
| **Simulador / Sessão QR** | Sessão tokenizada, expirável e revogável que abre a tela de operação de um andar no celular do admin. |
| **Sensor** | Dispositivo com chave `X-Device-Key` (hash no banco), emissão/revogação apenas por admin e ingestão idempotente por `(sensor, seq)`. |
| **Papel** | `admin`, `gestor`, `financeiro` ou `motorista`; define o que cada usuário pode chamar. |
| **Escopo** | Regra que amarra gestor/financeiro à filial vinculada; impede BOLA/IDOR entre estacionamentos. |
| **HMAC de requisição** | Assinatura HMAC-SHA256 de escritas em produção, com timestamp e nonce; camada de atrito, não fronteira de segurança. |
| **Cache stale** | Última leitura persistida em `AsyncStorage` (`sp:cache:*`) e exibida com aviso quando a API cai. |
| **Tempo quase real** | Atualização por polling configurável (8–25 s), sem WebSocket/SSE, com coalescência de requisições. |

### 3.2 Conceitos de engenharia

| Conceito | Como aparece no código |
|---|---|
| **Arquitetura limpa / separação de camadas** | `api/` trata HTTP, `rules/` concentra regra de negócio, `models/` cuida de persistência e schemas, `core/` cuida de segurança e configuração. |
| **Spec-Driven Development** | [`src/docs/SDD.md`](src/docs/SDD.md) funciona como contrato executável, com ADRs, status por requisito e apêndice de evidências. |
| **REST + OpenAPI** | FastAPI gera `/docs`, `/redoc` e `/openapi.json` em desenvolvimento; em produção essas rotas são desativadas. |
| **ORM e migrações** | SQLAlchemy 2.0, PostgreSQL 15, Alembic baseline e reparo idempotente de esquema antigo no boot. |
| **Validação de contrato** | Pydantic v2 valida entrada/saída antes da regra de negócio; erros viram `{ "detail": ... }`. |
| **Fuso horário** | UTC no banco, `America/Manaus` na borda dos relatórios e da UI (ADR-05). |
| **Cross-platform** | Expo Router + React Native Web + NativeWind: um código para Android, iOS e Web, com adaptações medidas no pré-render. |
| **Estado e integração** | Contexto de autenticação, hooks customizados, Axios com refresh *single-flight*, storage multiplataforma e assinador de requisições. |
| **Defesa em profundidade** | Nginx, middlewares, JWT, escopo, HMAC, rate limiting, limite de corpo, headers e testes de segurança. |
| **QA medido** | [`QA_UI_UX.md`](src/docs/QA_UI_UX.md) mede cor, foco, hover, pressed, contraste, overflow, movimento reduzido e orçamento de desempenho no artefato renderizado. |
| **Gate binário** | Scripts e CI devem terminar com exit `0` ou `1`; não se usa retry, espera fixa ou filtro de erro para esconder falha. |

### 3.3 Tempo quase real sem WebSocket

O projeto mantém **polling** por decisão registrada no ADR-01: atende ao objetivo de atualização sem exigir estado compartilhado entre workers.

- [`useEstacionamentos.ts`](src/frontend/smart-parking/src/hooks/useEstacionamentos.ts) e [`useMapaVagas.ts`](src/frontend/smart-parking/src/hooks/useMapaVagas.ts) evitam chamadas sobrepostas com `emCurso`, guardam `idAtual`/`mounted` e ignoram respostas antigas.
- O cache em `AsyncStorage` não sobrescreve uma resposta real já recebida; se a rede falha, os dados viram **stale** com aviso explícito.
- A recuperação ocorre sem reload: a próxima leitura válida limpa o erro e substitui o cache.
- [`quality.spec.ts`](src/frontend/smart-parking/tests/ui/quality.spec.ts) mede mudança externa do mapa em até 8 s e [`resilience.spec.ts`](src/frontend/smart-parking/tests/ui/resilience.spec.ts) prova preservação do cache e recuperação.
- Animações respeitam `prefers-reduced-motion`; botões mantêm cor, foco e transição mesmo sem animação.

### 3.4 Modelo de dados resumido

```text
Estacionamento ──< Andar ──< Vaga ──< Historico
       │                      │
       │                      ├──< Reserva ──< Pagamento
       │                      └──< ConfiguracaoPreco
       ├──< CupomDesconto
       ├──< FechamentoCaixa
       └──< Usuario (papel + vínculo de filial)

Sensores ──< Eventos de sensor (idempotentes por sensor + seq)
Sessões QR ──< Operações do simulador (admin, expiração/revogação)
```

---

<a id="metodos-e-estrutura"></a>
## 4. Métodos e Estrutura

### 4.1 Método de trabalho

| Método | Aplicação prática |
|---|---|
| **Contrato antes de código** | SDD, mapa da aplicação e rubrica definem o que existe, o que falta e como provar. |
| **Entrega por marcos** | Cinco marcas PEX com prazo, peso e evidência; ver [Roadmap](#roadmap). |
| **Rotas finas, regras puras** | Se uma rota tem `if` de negócio, ele deve estar em `rules/`. |
| **ADRs registrados** | Decisões de polling, fuso, HMAC, escopo, migrações e deploy estão justificadas no SDD. |
| **Validação real** | pytest com SQLite isolado, smoke contra API viva, Playwright com backend e banco reais, `ruff`, `tsc`, export e prebuild. |
| **QA de artefato** | Medidas sobre HTML/CSS renderizado, não opinião visual; dois renderers (nativo e web) são considerados. |
| **Segurança por camadas** | Nenhuma proteção cliente-side é tratada como autoridade; o backend sempre revalida. |
| **Honestidade técnica** | Documentos antigos trazem notas explícitas sobre pinning não implementado, HMAC como atrito e compose em HTTP. |
| **Reprodutibilidade** | Docker Compose, scripts de smoke, `.env.example`, CI e pinagem de dependências — com a ressalva atual dos manifests em [9.5](#limitacoes-conhecidas). |

### 4.2 Decisões arquiteturais (resumo das ADRs)

| ADR | Decisão | Por quê |
|---|---|---|
| ADR-01 | Manter polling 8–25 s; avaliar SSE só se sobrar tempo | WebSocket/SSE exigiria estado compartilhado entre workers. |
| ADR-02 | Sessões QR em Postgres; nonces/rate limit em memória com 1 worker; Redis só ao escalar | Simplicidade para o volume da entrega. |
| ADR-03 | Sensor com `X-Device-Key` por dispositivo e eventos idempotentes | Sensor não faz login humano; chave é revogável. |
| ADR-04 | Alembic com baseline do esquema atual | Evoluir schema sem derrubar volume. |
| ADR-05 | UTC no banco, `America/Manaus` na borda | Independe do fuso da máquina/container. |
| ADR-06 | HMAC como camada extra; remover regex anti-SQLi; manter bloqueio de scanners e limite de corpo | SQLAlchemy já parametriza queries; regex causava falso positivo em dados legítimos. |
| ADR-07 | Uma dependência única de escopo aplicada a toda rota com `estacionamento_id` | Evita novo BOLA. |
| ADR-08 | Financeiro consolidado em `pagamento_service` | Elimina duplicidade de tarifa/cupom/resumo. |
| ADR-09 | Ocupação histórica derivada do `Historico` | Sem tabela de snapshots e sem novo estado. |
| ADR-10 | pytest + `TestClient` em SQLite e CI | Testes rápidos, sem Docker, com gate binário. |
| ADR-11 | Deploy de apresentação por Docker na LAN + Expo Go/Web; TLS na marca 5 | Reduz risco de rede e custo na banca. |

### 4.3 Arquitetura

```text
┌──────────────────────────────────────┐
│ App Expo — Android · iOS · Web       │
│ TypeScript · NativeWind · Expo Router │
│ Hooks + cache offline + HMAC client  │
└───────────────────┬──────────────────┘
                    │ HTTPS/HTTP JSON · Bearer · URL resolvida por plataforma
       ┌────────────▼─────────────┐        ┌──────────────────────────────┐
       │ Admin: QR do simulador   │        │ Sensores: X-Device-Key       │
       │ /simulador?sessao=...    │        │ POST /api/sensores/eventos   │
       └────────────┬─────────────┘        └──────────────┬───────────────┘
                    │                                      │
              ┌─────▼──────────────────────────────────────▼─────┐
              │ Nginx :80 — proxy reverso · rate limit · headers │
              └─────────────────────────┬────────────────────────┘
                                        │
              ┌─────────────────────────▼────────────────────────┐
              │ FastAPI :8000 — Gunicorn + Uvicorn                │
              │ middlewares → api/ → rules/ → models/             │
              │ JWT · escopo · HMAC · limite de corpo · rate limit│
              └─────────────────────────┬────────────────────────┘
                                        │
              ┌─────────────────────────▼────────────────────────┐
              │ PostgreSQL 15 · volume postgres_data              │
              │ SQLite automático apenas em dev, desligável       │
              └──────────────────────────────────────────────────┘
```

### 4.4 Caminho de uma requisição

1. O app resolve a URL da API **por plataforma**: Web same-origin/dev, Expo Go pelo `hostUri` do Metro, emulador Android por `10.0.2.2`, ou override `EXPO_PUBLIC_API_URL*`.
2. Login gera `access_token` (15 min) e `refresh_token` (7 dias), salvos em `AsyncStorage`.
3. [`api.ts`](src/frontend/smart-parking/src/services/api.ts) envia `Authorization: Bearer ...`; em produção, escritas também recebem headers HMAC.
4. Um `401` dispara **um único refresh** para N requisições pendentes; refresh morto encerra a sessão globalmente.
5. No servidor: validação de requisição → headers/scanners/anti-duplicação → limite de corpo → Trusted Host em produção → CORS → dependência de sessão → JWT → usuário ativo → regra de escopo → `rules/`.
6. A saída passa por schemas Pydantic; erros voltam como `{ "detail": ... }` e são traduzidos na UI.
7. Sensores e simulador QR são os dois caminhos que **não usam login humano**: um por chave de dispositivo, outro por sessão tokenizada criada por admin.

### 4.5 Estrutura do repositório

```text
smart-parking-pex/
├── README.md                         ← este documento
├── LICENSE                           ← MIT
├── .github/workflows/
│   ├── ci.yml                        ← backend 3.10/3.12, frontend, UI Playwright
│   ├── android-emulator.yml          ← gate nativo Android
│   └── expo-sdk-update.yml           ← consulta diária do canal estável do Expo
├── scripts/                          ← Docker, smoke, conexão, QA e servidores E2E
│   ├── docker.sh · smoke_mvp.sh · smoke_acesso.sh · e2e_validacao.sh
│   ├── check_conexao.sh · dev-front.sh · check_expo_sdk.cjs
│   ├── prepare_ui_backend.py · ui_backend_server.py · ui_web_server.cjs
│   └── validate_expo_native.sh · update_expo_sdk.sh
├── src/
│   ├── docker-compose.yml            ← nginx + backend + postgres + pgadmin
│   ├── nginx/                        ← proxy, zonas de rate limit, Dockerfile
│   ├── backend/                      ← FastAPI
│   │   ├── api/                      #   rotas HTTP: api, auth, admin, sensores
│   │   ├── rules/                    #   regras de negócio puras e testáveis
│   │   ├── models/                   #   ORM, schemas Pydantic, conexão
│   │   ├── core/                     #   config, segurança, middlewares, CORS, fuso
│   │   ├── migrations/               #   Alembic baseline
│   │   ├── tests/                    #   176 testes pytest
│   │   ├── seed_demo.py              #   8 shoppings de Manaus
│   │   └── main.py                   #   composição da app e lifespan
│   ├── frontend/smart-parking/       ← Expo SDK 58 · Android/iOS/Web
│   │   ├── app/ + src/app/           #   rotas e telas
│   │   ├── src/components/           #   Header, Hero, VagaMapa, AdminShell, ui.tsx
│   │   ├── src/hooks/                #   polling, cache, largura responsiva
│   │   ├── src/services/             #   api.ts, URL por plataforma, HMAC, storage
│   │   ├── src/context/              #   AuthContext
│   │   ├── src/types/                #   contratos TypeScript
│   │   ├── plugins/                  #   withLocalNetwork (LAN sem cleartext global)
│   │   ├── tests/ui/                 #   22 jornadas Playwright, retries: 0
│   │   └── playwright.config.ts      #   API real + SQLite seed + proxy same-origin
│   └── docs/                         ← 16 documentos técnicos + rubrica em imagem
└── .gitignore
```

> 📌 `src/frontend/smart-parking/package.json` e `package-lock.json` **não estão no tree do GitHub**. Eles continuam apenas como cópias locais/ignoradas quando disponíveis na máquina do time; não foram reintroduzidos aqui.

### 4.6 Camadas e responsabilidades

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Apresentação | `src/frontend/smart-parking/src/app/`, `src/components/` | Telas, navegação, estados de botão, acessibilidade e layout responsivo. |
| Estado do cliente | `src/hooks/`, `src/context/` | Polling sem sobreposição, cache offline, sessão, largura responsiva. |
| Integração HTTP | `src/services/` | Um ponto de saída, refresh, assinatura, resolução de URL e storage. |
| Borda HTTP | `src/backend/api/` | Validar contrato, chamar serviço, devolver código HTTP correto. |
| Regra de negócio | `src/backend/rules/` | Ocupação, reserva, tarifa, relatório, sensores, simulador, escopo. |
| Persistência | `src/backend/models/`, `migrations/` | Entidades, relacionamentos, schemas e evolução de esquema. |
| Segurança transversal | `src/backend/core/`, `src/nginx/` | JWT, HMAC, headers, rate limit, Trusted Host, CORS, limite de corpo. |
| Infraestrutura | `src/docker-compose.yml`, `scripts/` | Subir, semear, diagnosticar, testar e derrubar a stack. |
| Evidência | `tests/`, `src/docs/` | Provar o que foi implementado e o que ainda falta. |

---

<a id="funcionalidades"></a>
## 5. Funcionalidades

### 5.1 Entregue no MVP

| Funcionalidade | Descrição |
|---|---|
| 📊 Dashboard | Vagas livres/ocupadas/reservadas, taxa de ocupação, rotação, tempo médio e heatmap por hora/andar. |
| 🗺️ Mapa de vagas | Status individual por andar: 🟢 livre · 🔴 ocupada · 🟡 reservada · ⚪ inativa. |
| 📱 QR Code do simulador | API gera URL por estacionamento/andar; admin abre no celular e opera vagas individualmente ou em lote. |
| 👨‍💼 Área administrativa | Gestão de estacionamentos, andares, vagas, usuários, papéis, preços e chaves de sensor. |
| 🔐 Segurança | JWT, bcrypt, HMAC anti-replay, rate limiting, escopo por filial, headers, limite de corpo e guards de produção. |
| 🌆 Dados reais | Seed idempotético com 8 shoppings parceiros de Manaus/AM. |
| 📈 Relatórios | Fluxo, ocupação, ocupação histórica, rotação, resumo financeiro e CSV com BOM/`;` para Excel pt-BR. |
| 🔌 Sensores | Emissão/revogação de `X-Device-Key` e ingestão idempotente por `(sensor, seq)`. |
| ♿ UI/UX | Contraste, foco visível, hover/pressed, alvos de toque ≥ 44 px, `prefers-reduced-motion` e layout sem overflow. |
| 📴 Resiliência | Cache offline, aviso de dados stale, recuperação sem reload e polling coalescido. |

### 5.2 Parcial / sinalizado

| Item | Estado real |
|---|---|
| Reservas | Backend e UI básicos existem; expiração e liberação de vaga são testadas. Fluxo completo de check-in por câmera ainda é roadmap. |
| Financeiro | Leitura, resumo e CSV implementados; caixa por turno, estorno operacional e pagamento real seguem como fase 2. |
| Login social | Rotas existem, mas `LOGIN_SOCIAL_ENABLED=False` por padrão; respondedor 404 até configurar credenciais. |
| Cupons | Modelagem e regra de desconto existem; operação completa de campanha não é escopo desta entrega. |
| CI frontend/UI | Implementada, mas bloqueada pela ausência dos manifests no repositório. |

### 5.3 Roadmap de produto (fase 2)

- 🔖 Reserva antecipada completa com check-in/check-out por câmera.
- 💳 Pagamento de estadia: PIX, cartão, dinheiro, estorno e caixa por turno.
- 🎟️ Cupons e campanhas com validade/limite operados no painel.
- 📈 Relatórios financeiros avançados e exportações adicionais.
- 📲 Login social Google/Apple após configuração de credenciais.
- 🔌 Sensores IoT físicos e, se necessário, MQTT.
- 🔔 Notificações push e publicação nas lojas.

---

<a id="como-executar"></a>
## 6. Como executar

### 6.1 Pré-requisitos

| Ferramenta | Versão / observação |
|---|---|
| Docker + Docker Compose | Recomendado para a stack completa. |
| Python | **3.10 ou superior**; CI valida 3.10 e 3.12. Use os comandos `python` e `pip`, sem sufixos e sem criar `venv` no ambiente do projeto. |
| Node.js + npm | Node 24 e npm 11 na CI. |
| Expo Go | Opcional, compatível com SDK 58, para testar no celular. |
| Curl | Usado por `scripts/check_conexao.sh`. |

> ⚠️ **Antes do frontend:** os manifests `package.json` e `package-lock.json` foram removidos do GitHub. Para rodar `npm ci`, `npx expo`, `npm run check-sdk` ou Playwright, **é necessário ter a cópia local aprovada pela equipe** em `src/frontend/smart-parking/`. Um clone limpo sozinho não instala o app. Não reintroduza esses arquivos no versionamento sem nova autorização.

### 6.2 Backend + banco com Docker

```bash
./scripts/docker.sh up       # rebuild + nginx :80 · backend :8000 · postgres :5432 · pgadmin :5050 + smoke
./scripts/docker.sh acesso   # auditoria de controle de acesso (matriz papel × recurso)
./scripts/docker.sh smoke    # smoke da cadeia completa
./scripts/docker.sh logs     # diagnóstico de 502/400
./scripts/docker.sh reset    # volume limpo + rebuild + smoke ("dia de apresentação")
```

### 6.3 Backend local, sem Docker e sem venv

```bash
cd src/backend
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # opcional em dev; obrigatório ajustar segredos em produção
python seed_demo.py           # popula os 8 shoppings de Manaus
python main.py                # API em http://localhost:8000
```

Documentação interativa: `http://localhost:8000/docs` · PgAdmin: `http://localhost:5050` (`admin@admin.com` / `admin`, **apenas demo**).

### 6.4 Frontend Expo

Com os **manifests locais** presentes:

```bash
cd src/frontend/smart-parking
npm ci --no-audit --no-fund
cp .env.example .env          # opcional: o app resolve a URL sozinho por plataforma
npx expo start                # w = web · a = Android · i = iOS · ou escaneie o QR
```

Para celular físico na mesma LAN, prefira:

```bash
./scripts/dev-front.sh        # detecta o IP, escreve EXPO_PUBLIC_API_URL_MOBILE e limpa o cache
./scripts/check_conexao.sh    # health → login → /me → leituras → CORS
./scripts/check_conexao.sh --fix   # corrige a primeira linha ativa indevida no .env
```

O guia [`CONECTIVIDADE_MOBILE.md`](src/docs/CONECTIVIDADE_MOBILE.md) separa Expo Go, emulador, development build e produção. O acesso mobile é liberado **somente para IP privado**, sem CORS `*`, sem ATS arbitrário e sem cleartext Android global.

### 6.5 Verificação e atualização do SDK

Os comandos abaixo leem `package.json`/`package-lock.json` e, portanto, **só funcionam com a cópia local aprovada**:

```bash
cd src/frontend/smart-parking
npm run check-sdk      # canal latest + pins exatos + lockfile/node_modules
npm run update-sdk     # expo install expo@latest + --fix, restaurando pins exatos
npm run doctor         # diagnóstico oficial completo
npm run check-native   # export Hermes Android/iOS/Web + prebuild em pasta temporária
npm run typecheck      # TypeScript estrito
npx playwright test    # 22 jornadas com API real; requer Chromium e variáveis do playwright.config.ts
```

O workflow [`expo-sdk-update.yml`](.github/workflows/expo-sdk-update.yml) consulta o canal estável diariamente e abre PR quando há atualização. Não há push/merge automático na `main`: `expo-doctor`, TypeScript, export e prebuild precisam passar. Teste em aparelho físico continua obrigatório antes de publicar build.

### 6.6 Portas

| Serviço | Porta | Observação |
|---|---|---|
| Nginx | 80 | Proxy reverso; configuração é copiada na imagem, não por bind mount. |
| FastAPI | 8000 | `python main.py` ou container `backend`. |
| Expo/Metro | 8081 | Serve o bundle do app; **não** é a porta da API. |
| PostgreSQL | 5432 | `postgres:15-alpine`, volume `postgres_data`. |
| PgAdmin | 5050 | Interface web; credenciais padrão apenas para demo. |
| API E2E | 8010 | Backend isolado usado por `playwright.config.ts`. |
| Proxy Web E2E | 8000 | `scripts/ui_web_server.cjs` em same-origin para os testes. |

### 6.7 Variáveis de ambiente principais

| Variável | Onde | Papel |
|---|---|---|
| `ENVIRONMENT` | backend | `development`/`staging`/`test`/`production`; produção ativa HMAC, Trusted Host, HSTS e guards de segredo. |
| `DATABASE_URL` | backend | Postgres com driver explícito `postgresql+psycopg2://...`. |
| `DB_AUTO_SQLITE` | backend | `false` em equipe/produção para não esconder falha do Postgres em SQLite "fantasma". |
| `SECRET_KEY` | backend | Chave JWT; produção exige valor próprio com ≥ 32 bytes. |
| `APP_SIGNING_SECRET` | backend + app | Segredo HMAC; precisa ser **o mesmo** nos dois lados em produção. |
| `TRUSTED_HOSTS` | backend | Hosts aceitos em produção; suporta padrões de IP privado sem abrir `*`. |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | backend | Origens explícitas; curinga é recusado no boot de produção. |
| `MAX_REQUEST_BODY_BYTES` | backend | Teto de corpo para escritas (1 MiB por padrão). |
| `BLOQUEIO_DUPLICIDADE` | backend | Liga anti-duplicação de escritas idênticas em < 1 s. |
| `LOGIN_SOCIAL_ENABLED` | backend | Desligado por padrão; rotas sociais respondem 404. |
| `SIMULADOR_BASE_URL` | backend | URL pública embutida no QR; na LAN use o IP do PC, não `localhost` do celular. |
| `EXPO_PUBLIC_API_URL_WEB` | frontend | Override apenas para a Web. |
| `EXPO_PUBLIC_API_URL_MOBILE` | frontend | Override para celular/development build; aceita HTTP somente em LAN. |
| `EXPO_PUBLIC_API_URL` | frontend | Override global quando as específicas não existem. |
| `EXPO_PUBLIC_APP_SIGNING_SECRET` | frontend | Espelho de `APP_SIGNING_SECRET` para assinar escritas. |

> `DEFAULT_API_URL` **não existe**. Expo só injeta variáveis com prefixo `EXPO_PUBLIC_`. Mudou `.env`? Reinicie com `npx expo start -c`.

---

<a id="como-usar"></a>
## 7. Como usar

### 7.1 Fluxo do motorista

1. Abra o app: a home lista os shoppings parceiros de Manaus e o painel de status.
2. Escolha um shopping: o dashboard atualiza vagas, ocupação e tempo médio.
3. Explore o mapa por andar: 🟢 livre · 🔴 ocupada · 🟡 reservada.
4. Consulte a **próxima vaga**: o motor prioriza PCD/idoso/moto conforme elegibilidade.
5. Entre na conta para reservar, acompanhar reservas e editar o perfil.

### 7.2 Fluxo do administrador no simulador

1. Entre como administrador — área restrita.
2. Gere o QR Code de um estacionamento/andar.
3. Escaneie no celular: abre a página de operação do andar.
4. Toque em uma vaga para ocupar/liberar, ou use ações em lote.
5. Veja o dashboard atualizar e o `Historico` registrar entrada/saída automaticamente.

> 🔮 Sensores reais substituirão o simulador usando a mesma API de escrita, com `X-Device-Key` no lugar da sessão QR.

### 7.3 Usuários de demonstração

**Administrador (acesso total, gerencia todos os shoppings):**

| Papel | E-mail | Senha | Pode |
|---|---|---|---|
| Administrador | `admin@smartparking.com` | `admin123` | Tudo, inclusive gerar QR e emitir chave de sensor. |
| Motorista | `motorista@smartparking.com` | `motor123` | Usar o app e as próprias reservas. |

**Gestores (um ou mais shoppings por conta):**

| E-mail | Senha | Shoppings |
|---|---|---|
| `gestor@smartparking.com` | `gestor123` | Amazonas Shopping + Millennium Shopping |
| `financeiro@smartparking.com` | `gestor123` | Amazonas Shopping |
| `gestor2@…` até `gestor8@smartparking.com` | `gestor123` | Cada um, um shopping (os demais) |

**Financeiros (exatamente um shopping por conta):**

| E-mail | Senha | Shopping |
|---|---|---|
| `financeiro1@smartparking.com` … `financeiro8@smartparking.com` | `financ123` | Um por shopping (números sequenciais até a quantidade de shoppings cadastrados) |

> 🔒 Estas credenciais são **fixtures de desenvolvimento**. Com `ENVIRONMENT=production`, o admin padrão e o seed demo não são criados automaticamente; troque todas as chaves e credenciais antes de qualquer exposição real.

---

<a id="api"></a>
## 8. API

**Autenticação:** `POST /auth/login` retorna `access_token` + `refresh_token` (JWT). Rotas autenticadas usam `Authorization: Bearer <access_token>`.

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/health` | Healthcheck de infraestrutura | — |
| GET | `/api/estacionamentos` | Lista shoppings com vagas disponíveis | — |
| GET | `/api/estacionamentos/{id}/vagas` | Mapa de vagas por andar | — |
| GET | `/api/estacionamentos/{id}/proxima-vaga` | Próxima vaga livre por tipo; token opcional define elegibilidade PCD | — |
| PATCH | `/api/vagas/{id}/status` | Atualiza status da vaga | JWT + escopo |
| PATCH | `/api/vagas/lote/status` | Atualização em lote | JWT + escopo |
| POST | `/api/admin/simulador/qr` | Gera URL/QR do simulador | JWT admin |
| POST | `/api/sensores/eventos` | Ingestão idempotente de eventos | `X-Device-Key` |
| POST | `/auth/registrar` · `/auth/login` · `/auth/refresh` · `/auth/logout` | Ciclo de sessão | Público / JWT |
| GET/PUT | `/auth/me` · `/auth/senha` | Perfil e troca de senha | JWT |
| POST/GET/DELETE | `/api/reservas/*` | Reservas do motorista | JWT |
| GET | `/api/relatorios/fluxo` · `/ocupacao` · `/ocupacao-historica` · `/rotacao` | Relatórios agregados | JWT + papel + escopo |
| GET | `/api/relatorios/fluxo/publico` | Agregados públicos para a home | — |
| GET | `/api/relatorios/*/csv` | CSV pt-BR com BOM e `;` | JWT + papel + escopo |
| * | `/api/admin/*` | CRUD, preços, usuários, caixa, cupons, sensores | JWT + papel + escopo |

```bash
curl http://localhost:8000/api/estacionamentos | python -m json.tool
```

- 📖 Swagger: `http://localhost:8000/docs` — desativado em produção.
- 🗺️ Inventário de rotas e matriz papel × recurso: [`MAPA_APLICACAO.md`](src/docs/MAPA_APLICACAO.md).
- 🤝 Contrato frontend ↔ backend: [`INTEGRACAO_FRONTEND.md`](src/docs/INTEGRACAO_FRONTEND.md).

---

<a id="seguranca-aplicada"></a>
## 9. Segurança aplicada ao Projeto

> **Princípio:** defesa em profundidade, com o servidor como autoridade. A assinatura HMAC é **camada de atrito contra abuso casual**, não substitui autenticação, autorização, validação de escopo, rate limiting nem TLS. Essa honestidade está registrada em [`PROTECAO_REQUISICOES.md`](src/docs/PROTECAO_REQUISICOES.md) e [`SEGURANCA_TLS_WIRESHARK.md`](src/docs/SEGURANCA_TLS_WIRESHARK.md).

### 9.1 Mapa de camadas

| Camada | Ameaça endereçada | Mecanismo | Onde no código | Evidência |
|---|---|---|---|---|
| **Borda / transporte** | Host falso, origem não autorizada, exposição de versão | `TrustedHostLANMiddleware`, CORS sem curinga, remoção de `Server`/`X-Powered-By`, HSTS em produção, zonas Nginx | [`core/trusted_host.py`](src/backend/core/trusted_host.py), [`core/cors.py`](src/backend/core/cors.py), [`nginx/default.conf`](src/nginx/default.conf) | [`test_seguranca_http.py`](src/backend/tests/test_seguranca_http.py), [`check_conexao.sh`](scripts/check_conexao.sh) |
| **Autenticação** | Credencial fraca, token longo, sessão não revogada | JWT 15 min + refresh 7 dias, bcrypt com salt, logout com revogação, refresh *single-flight* | [`core/security.py`](src/backend/core/security.py), [`api/auth.py`](src/backend/api/auth.py), [`services/authFlow.ts`](src/frontend/smart-parking/src/services/authFlow.ts) | [`test_auth_sensores.py`](src/backend/tests/test_auth_sensores.py), [`auth.spec.ts`](src/frontend/smart-parking/tests/ui/auth.spec.ts) |
| **Autorização / escopo** | BOLA, IDOR, gestor acessando outra filial, motorista no painel | Papéis, `garantir_escopo_estacionamento`, `garantir_escopo_relatorio`, guards do último admin | [`core/deps.py`](src/backend/core/deps.py), [`rules/`](src/backend/rules/) | [`test_controle_acesso.py`](src/backend/tests/test_controle_acesso.py), [`smoke_acesso.sh`](scripts/smoke_acesso.sh) |
| **Integridade / anti-replay** | Cópia de requisição, alteração de corpo, replay | HMAC-SHA256 sobre método + path + query + timestamp + nonce + corpo, janela ±5 min, nonce único | [`core/request_validator.py`](src/backend/core/request_validator.py), [`services/requestSigner.ts`](src/frontend/smart-parking/src/services/requestSigner.ts) | [`PROTECAO_REQUISICOES.md`](src/docs/PROTECAO_REQUISICOES.md) |
| **Injeção e contrato** | SQL injection, payload inesperado, JSON malformado | SQLAlchemy parametrizado, Pydantic v2, **regex anti-SQLi removido** por ADR-06 para evitar falso positivo | [`models/schemas.py`](src/backend/models/schemas.py), [`models/db_models.py`](src/backend/models/db_models.py) | [`test_seguranca_sql_injection.py`](src/backend/tests/test_seguranca_sql_injection.py) |
| **XSS e UI** | Script injetado em perfil, open redirect, texto executável | Renderização de texto pelo React Native, CSP, validação de `next`, sanitização de erro | [`components/ui.tsx`](src/frontend/smart-parking/src/components/ui.tsx), [`services/api.ts`](src/frontend/smart-parking/src/services/api.ts) | [`security.spec.ts`](src/frontend/smart-parking/tests/ui/security.spec.ts) |
| **Abuso / disponibilidade** | Força bruta, scanner, corpo gigante, rajada | Nginx 30 r/s + login 5/min + 20 conexões/IP, SlowAPI, limite de 1 MiB, anti-duplicação, bloqueio de UA de scanner | [`core/rate_limiter.py`](src/backend/core/rate_limiter.py), [`core/body_limit.py`](src/backend/core/body_limit.py), [`core/security_middleware.py`](src/backend/core/security_middleware.py) | [`test_seguranca_resiliencia.py`](src/backend/tests/test_seguranca_resiliencia.py), [`resilience.spec.ts`](src/frontend/smart-parking/tests/ui/resilience.spec.ts) |
| **Configuração / segredos** | Chave padrão em produção, CORS `*`, `/docs` exposto | `Settings` recusa `SECRET_KEY`/`APP_SIGNING_SECRET` de exemplo e CORS curinga no boot de produção; docs desativadas | [`core/config.py`](src/backend/core/config.py), [`main.py`](src/backend/main.py) | [`test_core_guards.py`](src/backend/tests/test_core_guards.py) |
| **Mobile / LAN** | Cleartext global, ATS arbitrário, túnel indevido | Exceção somente para IP privado, `NSAllowsArbitraryLoads=false`, `usesCleartextTraffic=false`, firewall por sub-rede | [`plugins/withLocalNetwork.js`](src/frontend/smart-parking/plugins/withLocalNetwork.js), [`app.json`](src/frontend/smart-parking/app.json) | [`CONECTIVIDADE_MOBILE.md`](src/docs/CONECTIVIDADE_MOBILE.md) |
| **Resiliência de dados** | API lenta, queda de rede, cache corrompido, resposta antiga | Cache stale com aviso, coalescência de polling, guard de `mounted`/`idAtual`, recuperação sem reload | [`useEstacionamentos.ts`](src/frontend/smart-parking/src/hooks/useEstacionamentos.ts), [`useMapaVagas.ts`](src/frontend/smart-parking/src/hooks/useMapaVagas.ts) | [`quality.spec.ts`](src/frontend/smart-parking/tests/ui/quality.spec.ts), [`resilience.spec.ts`](src/frontend/smart-parking/tests/ui/resilience.spec.ts) |
| **Qualidade contínua** | Regressão silenciosa | `ruff`, pytest, TypeScript, export, prebuild, Playwright sem retries | [`.github/workflows/ci.yml`](.github/workflows/ci.yml), [`playwright.config.ts`](src/frontend/smart-parking/playwright.config.ts) | [Seção 10](#qualidade-validacao-e-testes) |

### 9.2 Cenários de ataque e resposta esperada

| Cenário | Resposta |
|---|---|
| Repetir uma escrita capturada | `403`/`429` por nonce já usado, timestamp expirado ou anti-duplicação. |
| Enviar SQL injection em campo de busca | Consulta parametrizada; entrada inválida é rejeitada por validação, não por regex que quebra nomes legítimos. |
| Injetar `<script>` no perfil | Texto renderizado como texto; CSP e teste E2E impedem execução. |
| Gestor consultar relatório de outra filial | `403` com escopo nomeado. |
| Motorista abrir painel admin | `403`; ações exclusivas não aparecem na UI. |
| `next` externo após login | Redirecionamento não autorizado é bloqueado. |
| 11º login no mesmo minuto | `429` com `retry_after`. |
| User-Agent de `sqlmap`/`nikto`/`curl` em produção | `403` de scanner, sem desligar as proteções. |
| `Content-Length` acima do teto | `413` antes de parser/HMAC, com conexão fechada. |
| `Host` falso em produção | `400` do Trusted Host; padrões de IP privado só valem para IP literal privado. |
| Origem CORS pública não autorizada | Sem cabeçalho `Access-Control-Allow-Origin`; verificada por `check_conexao.sh`. |
| Payload gigante ou rajada de polling | Limite de corpo e `emCurso` evitam acúmulo de requisições idênticas. |

### 9.3 Headers aplicados

`X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `X-XSS-Protection: 0` · `Referrer-Policy: strict-origin-when-cross-origin` · `Content-Security-Policy` · `Permissions-Policy` · `Cache-Control: no-store` · `Strict-Transport-Security` apenas em produção. `Server` e `X-Powered-By` são removidos inclusive nas respostas de bloqueio antecipado.

### 9.4 Checklist antes de produção

- [ ] `ENVIRONMENT=production`, `DEBUG=False`.
- [ ] `SECRET_KEY` e `APP_SIGNING_SECRET` fortes (≥ 32 bytes), com o **mesmo** segredo HMAC no app.
- [ ] `TRUSTED_HOSTS` e `CORS_ORIGINS` com domínios reais, sem curinga.
- [ ] TLS 1.2/1.3 + HSTS no Nginx; hoje o compose serve HTTP puro na porta 80.
- [ ] Remover/trocar credenciais do PgAdmin e todas as fixtures de demonstração.
- [ ] Migrar sessões QR, nonces e rate limit para Postgres/Redis antes de `GUNICORN_WORKERS>1`.
- [ ] `pg_dump` agendado + rotina de restore documentada.
- [ ] Revisar CI de frontend/UI sem reintroduzir os manifests no repositório.
- [ ] Validar em aparelho físico, em rede real e com build de produção.
- [ ] Avaliar SSL pinning e E2EE de payloads sensíveis; **pinning ainda não está implementado**.

<a id="limitacoes-conhecidas"></a>
### 9.5 Limitações conhecidas

1. **Manifests fora do GitHub.** `package.json` e `package-lock.json` foram excluídos do versionamento a pedido do projeto. O workflow ainda referencia `package-lock.json` em `cache-dependency-path` e roda `npm ci`; por isso `frontend` e `ui` falham no `actions/setup-node` na [run 42311181364](https://github.com/beh-S4nt05/smart-parking-pex/actions/runs/42311181364). Backends 3.10/3.12 seguem verdes. A correção deve revisar o workflow **sem** esconder testes, enfraquecer auditoria ou reintroduzir os arquivos sem autorização.
2. **HMAC não é fronteira criptográfica.** A chave viaja no bundle Web; a proteção eleva o custo de abuso casual, mas um atacante com engenharia reversa pode extraí-la. Autorização continua no servidor.
3. **SSL pinning não implementado.** [`SEGURANCA_TLS_WIRESHARK.md`](src/docs/SEGURANCA_TLS_WIRESHARK.md) é um guia, não uma funcionalidade ativa. O compose é HTTP na LAN.
4. **Estado em memória.** Sessões do simulador, nonces e rastreador de requisições são por processo; por isso o compose fixa `GUNICORN_WORKERS=1`. Escalar exige Redis/Postgres.
5. **Credenciais de demo.** Admin, gestor, financeiro, motorista e PgAdmin usam valores conhecidos; o guard de produção desliga o admin/seed padrão, mas o deploy precisa de rotação completa.
6. **Sem evidência de aparelho físico.** Export, prebuild, emulador e Playwright não provam Android/iPhone real nem a instalação em `/media/Arquivos/...`.
7. **Documentos históricos.** Alguns docs citam arquivos que não existem (`VALIDACAO_E_CONFORMIDADE.md`, `scripts/validacao/*`). A régua real é [`MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md) + [`SDD.md`](src/docs/SDD.md), e notas de honestidade foram preservadas.

---

<a id="qualidade-validacao-e-testes"></a>
## 10. Qualidade, validação e testes

### 10.1 Comandos

```bash
# Backend — sem Docker, sem servidor, sem venv no ambiente do projeto
cd src/backend
pip install -r requirements.txt -r requirements-dev.txt
pytest tests -q
ruff check .

# Aceite E2E contra API viva
./scripts/smoke_mvp.sh    http://localhost:8000   # fluxo de dados
./scripts/smoke_acesso.sh http://localhost:8000   # matriz papel × recurso

# Stack completa
./scripts/docker.sh up
./scripts/docker.sh smoke

# Frontend — requer os manifests locais aprovados
cd src/frontend/smart-parking
npm ci --no-audit --no-fund
npm run typecheck
npx expo export --platform web
npx playwright test
```

### 10.2 Resultados verificáveis

| Verificação | Resultado | Observação |
|---|---|---|
| `pytest tests -q` | **176 passed** em Python 3.11 local | Executado nesta rodada de documentação; 2 avisos de deprecação de bibliotecas. |
| `ruff check .` | **All checks passed!** | Portão de correção do backend. |
| CI backend 3.10 / 3.12 | ✅ Verde | `ruff` + `pytest` em cada versão. |
| `npm audit --audit-level=moderate` | Histórico: 7 achados após restauração dos manifests a `main` | Não enfraquecer o audit nem usar `npm audit fix --force` para esconder. |
| Playwright | **22 jornadas** registradas, `retries: 0` | 20 declarações `test(` + 3 cenários parametrizados de botões; última execução verde antes da remoção dos manifests. |
| CI frontend / UI no HEAD atual | ❌ Falha no `actions/setup-node@v4` | Causa: lockfile ausente no checkout. |
| TypeScript, SDK, bundles e prebuilds | ✅ Aprovados antes da remoção dos manifests | Não reexecutados nesta rodada de README. |
| Aparelho físico | ⬜ Não executado | Continua obrigatório antes de publicar build. |

> **Honestidade:** versões antigas deste README apontavam para `scripts/validacao/` e `src/docs/VALIDACAO_E_CONFORMIDADE.md`, que não existem. A régua real é [`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md) e o [`src/docs/SDD.md`](src/docs/SDD.md), com o apêndice §12 de evidências.

### 10.3 Como a suíte de UI é real

[`playwright.config.ts`](src/frontend/smart-parking/playwright.config.ts) sobe, sem mocks de API:

1. [`prepare_ui_backend.py`](scripts/prepare_ui_backend.py) — cria um SQLite isolado e semeia dados de teste.
2. [`ui_backend_server.py`](scripts/ui_backend_server.py) — FastAPI real na porta `8010`, com limiter e proteções ativas.
3. [`ui_web_server.cjs`](scripts/ui_web_server.cjs) — serve o bundle Expo e faz proxy same-origin para a API na porta `8000`.
4. Playwright executa jornadas de autenticação, reserva, segurança, resiliência, desempenho, contraste, foco, hover, pressed, movimento reduzido e tempo quase real.

Não há `pageerror` filtrado, retry, espera fixa para mascarar falha nem desativação de rate limiter/proteções.

---

<a id="roadmap"></a>
## 11. Roadmap

### 11.1 Régua acadêmica PEX

Fonte oficial: [`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md). A tabela abaixo é um resumo; a rubrica com pesos, evidências e imagem está no documento.

| # | Critério | Prazo | Peso | Status |
|---|---|---|---|---|
| 1 | Banco de dados modelado | 10/09/2026 | 1 | ✅ Entregue |
| 2 | MVP operacional (API + app + Docker + acessos) | 22/10/2026 | 2 | ✅ Entregue 20/10, com auditoria de acesso |
| 3 | Relatórios (fluxo/ocupação/rotação/financeiro + CSV + aba no painel) | 02/11/2026 | 1 | ✅ Antecipado em 22/10 |
| 4 | Testes & Documentação (pytest, CI, SDD, Alembic) | 09/11/2026 | 1 | ✅ Entregue 22/10 |
| 5 | Entrega Integrada Funcional | 12/11/2026 | 5 | 🟡 Chave de sensor, sessão com revogação, perfil e cache prontos; faltam TLS, câmera, backup e multi-worker |

### 11.2 Backlog técnico priorizado

| Prioridade | Item | Estado | Por que importa |
|---|---|---|---|
| **P0** | Revisar `.github/workflows/ci.yml` para `frontend`/`ui` sem depender de `package-lock.json` no checkout | ⬜ | Destrava a CI sem reintroduzir os manifests excluídos e sem enfraquecer gates. |
| **P0** | Hardening de produção real | 🟡 | TLS, secrets, Trusted Hosts, CORS, rotação de credenciais e remoção do PgAdmin padrão. |
| **P1** | Sessões QR/nonces/rate limit em Postgres/Redis | 🟡 | Libera `GUNICORN_WORKERS>1` sem perder anti-replay. |
| **P1** | Backup/restore do volume Postgres | ⬜ | Continuidade e recuperação em apresentação/produção. |
| **P1** | Check-in/check-out por câmera | ⬜ | Fecha o fluxo real de entrada/saída com QR. |
| **P1** | Manual do usuário com prints + roteiro de banca | ⬜ | Entrega integrada e avaliação da marca 5. |
| **P2** | Reservas completas, pagamento real, cupons e caixa | 🟡 | Backend existe; operação ponta a ponta ainda é fase 2. |
| **P2** | Sensores IoT físicos / MQTT | ⬜ | Substituir o simulador mantendo o contrato atual. |
| **P2** | Login social e notificações push | ⬜ | Depende de credenciais de provedores e build nativa. |
| **P2** | SSL pinning e criptografia de payloads sensíveis | ⬜ | Guia documentado, implementação pendente. |
| **P3** | Avaliar SSE/WebSocket e observabilidade | ⬜ | ADR-01 mantém polling até haver estado compartilhado. |

### 11.3 Concluído e protegido contra regressão

- 176 testes de backend, incluindo SQL injection, controle de acesso, guards de produção e resiliência HTTP.
- 22 jornadas E2E com API real, sem retries.
- Cache offline, stale data, recuperação sem reload e polling sem sobreposição.
- Cores, transições, foco, hover, pressed, contraste, alvos de toque e `prefers-reduced-motion` corrigidos e medidos.
- SDK 58 com pinagem exata no fluxo oficial do Expo, sem `audit fix --force`.
- Acesso mobile sem CORS `*`, sem ATS arbitrário e sem cleartext global.

---

<a id="referencia-da-faculdade"></a>
## 12. Referência da faculdade

### 12.1 Vinculação institucional

| Campo | Registro |
|---|---|
| Instituição | **Faculdade Matias Machline — FMM**, Manaus/AM. |
| Sigla nos documentos internos | `FMM`; o [`SDD.md`](src/docs/SDD.md) registra "`smart-parking-pex` (InteliParking) — extensão PEX, FMM, Manaus/AM". |
| Projeto | **PEX**, identificado nos documentos do repositório como extensão acadêmica. A sigla não é expandida literalmente nos arquivos internos, por isso é mantida como `PEX`. |
| Público avaliador | Equipe de desenvolvimento, **banca/orientação FMM** e agentes de código, conforme SDD §1.3. |
| Local | Manaus, Amazonas, Brasil. |
| Régua | Cinco marcas de entrega, total 10 pontos, registradas em [`MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md) e na imagem [`marcas-de-entrega.png`](src/docs/marcas-de-entrega.png). |

### 12.2 Documentos acadêmicos do repositório

| Documento | Papel na avaliação |
|---|---|
| [`src/docs/SDD.md`](src/docs/SDD.md) | Contrato executável: propósito, escopo, glossário, requisitos, ADRs e evidências §12. |
| [`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md) | Rubrica oficial, prazos, pesos e o que falta para cada marca. |
| [`src/docs/MAPA_APLICACAO.md`](src/docs/MAPA_APLICACAO.md) | Índice navegável de camadas, rotas, matriz papel × recurso e fluxo de acesso. |
| [`src/docs/QA_UI_UX.md`](src/docs/QA_UI_UX.md) | Medidas de UI/UX e gate de regressão do pré-render Web. |
| [`src/docs/INTEGRACAO_FRONTEND.md`](src/docs/INTEGRACAO_FRONTEND.md) | Contrato de rotas e códigos de erro entre app e API. |
| [`src/docs/MIGRACOES.md`](src/docs/MIGRACOES.md) | Baseline Alembic e fluxo de *stamp* para bancos existentes. |

### 12.3 Referências institucionais externas

- [Faculdade Matias Machline — site oficial](https://faculdadematiasmachline.org.br/)
- [Conheça a Faculdade Matias Machline](https://faculdadematiasmachline.org.br/conheca-a-faculdade-matias-machline/)

> O repositório usa apenas a sigla `FMM`; a expansão acima vem da referência institucional externa. Não há, nos arquivos internos, registro de disciplina específica, matrícula, nome de professor/orientador ou número de edital — portanto este README não inventa esses campos.

---

<a id="documentacao"></a>
## 13. Documentação

| Documento | Para que serve |
|---|---|
| [`src/docs/SDD.md`](src/docs/SDD.md) | Fonte da verdade de escopo, requisitos, ADRs e evidências. |
| [`src/docs/MARCAS_ENTREGA.md`](src/docs/MARCAS_ENTREGA.md) | Rubrica PEX e status das cinco marcas. |
| [`src/docs/MAPA_APLICACAO.md`](src/docs/MAPA_APLICACAO.md) | Mapa completo: camadas, rotas, fluxo de acesso, erros e animações. |
| [`src/docs/INTEGRACAO_FRONTEND.md`](src/docs/INTEGRACAO_FRONTEND.md) | Contrato de API, rotas e tratamento de erro no app. |
| [`src/docs/DOCUMENTACAO_BACKEND.md`](src/docs/DOCUMENTACAO_BACKEND.md) | Detalhamento do backend e notas de correção históricas. |
| [`src/docs/PROTECAO_REQUISICOES.md`](src/docs/PROTECAO_REQUISICOES.md) | HMAC, anti-replay e a nota de honestidade sobre seus limites. |
| [`src/docs/SEGURANCA_E_PERFORMANCE.md`](src/docs/SEGURANCA_E_PERFORMANCE.md) | Headers, rate limiting, pool de conexões e workers. |
| [`src/docs/SEGURANCA_TLS_WIRESHARK.md`](src/docs/SEGURANCA_TLS_WIRESHARK.md) | Guia de TLS/MITM; registra que pinning **não** está implementado. |
| [`src/docs/CONECTIVIDADE_MOBILE.md`](src/docs/CONECTIVIDADE_MOBILE.md) | Expo Go, emulador, development build e LAN sem abertura global. |
| [`src/docs/QA_UI_UX.md`](src/docs/QA_UI_UX.md) | Medidas de botões, contraste, overflow, animação e desempenho. |
| [`src/docs/MIGRACOES.md`](src/docs/MIGRACOES.md) | Alembic, baseline e bancos já existentes. |
| [`src/docs/MODULO_PAGAMENTOS_FATURAMENTO.md`](src/docs/MODULO_PAGAMENTOS_FATURAMENTO.md) | Tarifação, pagamentos, cupons e fechamento de caixa. |
| [`src/docs/NGINX_EXPLICADO.md`](src/docs/NGINX_EXPLICADO.md) | Proxy reverso, zonas de limite e encaminhamento. |
| [`src/docs/GUIA-CONVERSAO-NATIVE.md`](src/docs/GUIA-CONVERSAO-NATIVE.md) | Diferenças entre React Native nativo e react-native-web. |
| [`src/docs/docker-commands.md`](src/docs/docker-commands.md) | Comandos Docker explicados, inclusive limpeza segura. |
| [`src/docs/README.md`](src/docs/README.md) | Índice histórico e registro da equipe PEX. |
| [`src/backend/README.md`](src/backend/README.md) | Instruções específicas do backend. |
| [`src/frontend/smart-parking/AGENTS.md`](src/frontend/smart-parking/AGENTS.md) e [`CLAUDE.md`](src/frontend/smart-parking/CLAUDE.md) | Briefings de agentes de código para o frontend. |

---

<a id="solucao-de-problemas"></a>
## 14. Solução de problemas

<details>
<summary><strong>🔎 "Está sem conexão?" — diagnóstico em um comando</strong></summary>

```bash
./scripts/check_conexao.sh
./scripts/check_conexao.sh --fix
```

Exit `0` = health → login → `/me` → próxima-vaga → CORS validados ponta a ponta. Exit `1` = o primeiro `✘` impresso é exatamente o que bloqueia. O script roda de qualquer pasta e só exige `curl`.

</details>

<details>
<summary><strong>⚙️ Achas de configuração (URL, .env, porta e SQLite oculto)</strong></summary>

- Overrides do app: `EXPO_PUBLIC_API_URL_WEB`, `EXPO_PUBLIC_API_URL_MOBILE` e `EXPO_PUBLIC_API_URL`. `DEFAULT_API_URL` **não existe**.
- Sem `.env`, o app resolve sozinho: Web usa o próprio host (`:80`/`:443` same-origin; dev `:8081` → `:8000`); Expo Go usa o IP LAN do `hostUri` publicado pelo Metro; emulador Android usa `10.0.2.2`. Existe **uma única API**; muda apenas a resolução do host no cliente.
- O `.env` do backend vive em `src/backend/`. Porta 8000 ocupada? Ajuste `PORT` lá **e** no env do front, depois `npx expo start -c`.
- `DB_AUTO_SQLITE=true` faz o app silenciar a queda do Postgres e usar um SQLite oculto. Em dupla/trio e na banca, prefira `DB_AUTO_SQLITE=false` para o erro aparecer na hora.
- Mudou qualquer `EXPO_PUBLIC_*`? Reinicie com cache limpo: `npx expo start -c`.

</details>

<details>
<summary><strong>🐳 Docker / Nginx / Gunicorn — notas que já corrigiram 502 e 400</strong></summary>

- [`src/nginx/Dockerfile`](src/nginx/Dockerfile) instala `default.conf` em `conf.d/`; o `COPY . /etc/nginx/` antigo deixava o arquivo onde o Nginx nunca lê.
- [`default.conf`](src/nginx/default.conf) declara as zonas `req_limit_per_ip` (30 r/s), `login_limit` (5 r/min) e `conn_limit_per_ip` (20 conexões). Editou a conf? Rebuilde: a configuração vai **assada na imagem**, sem bind mount.
- [`gunicorn_config.py`](src/backend/gunicorn_config.py) usa `0.0.0.0:8000`; com `localhost`, o Nginx em outro container recebia connection refused.
- `GUNICORN_WORKERS=1` enquanto sessões do simulador/QR e o cache anti-replay forem memória de processo.
- O container usa `ENVIRONMENT=staging` e `DB_AUTO_SQLITE=false`. Produção real = `production` + `TRUSTED_HOSTS` + segredos fortes.
- Healthcheck TCP do backend condiciona a subida do Nginx; `postgres` usa `pg_isready`.

</details>

<details>
<summary><strong>🧯 Dependências do Expo misturaram versões</strong></summary>

**Não aceite "Fix dependencies?" nem rode `npm audit fix --force` para consertar o SDK.** O `expo install` usa o `expo` presente em `node_modules`; se essa pasta for de outro SDK, ele propõe dependências incompatíveis. `audit fix --force` já chegou a sugerir Expo 44, RN 0.72 e NativeWind 2 — uma árvore mista, não uma correção.

Como os manifests **não estão mais no GitHub**, `git restore --source=HEAD -- package.json package-lock.json` **não recupera os arquivos**. Use a cópia local aprovada pela equipe (fora do versionamento) ou reconstrua a árvore pelo fluxo oficial do Expo, sem reintroduzir os manifests no repositório sem autorização. Preserve qualquer diff manual antes de substituir a cópia.

Com a cópia local presente:

```bash
cd src/frontend/smart-parking
rm -rf node_modules .expo
npm ci --no-audit --no-fund
node -p "require('./node_modules/expo/package.json').version"   # esperado: 58.0.21
npx expo start -c
```

Depois, `npx expo install --check` confirma compatibilidade. Se anunciar major inesperada, pare, confira `node_modules` e use somente `npm run update-sdk` para uma atualização intencional. `npm audit` pode ser lido à parte, mas achados transitivos não devem derrubar os pins do SDK.

</details>

<details>
<summary><strong>📱 Expo Go: "Failed to download remote update"</strong></summary>

O projeto não usa OTA/EAS Update (não há `expo-updates` nem `eas.json`); o erro é o Expo Go tentando baixar bundle do servidor da Expo em vez de conectar ao Metro do PC.

1. Use **Expo Go compatível com SDK 58**. Se a loja ainda oferecer só SDK 57, rode por navegador (`npx expo start --web`), emulador ou development build (`npx expo run:android`).
2. Abra pelo **QR do terminal**, não pela aba "Projects/Recentes" do Expo Go, que vai ao expo.dev e exige projeto publicado.
3. Teste `http://IP-DO-PC:8081/status` no navegador do celular. Se não abrir, a rede isola dispositivos (AP isolation): use `npx expo start --tunnel`, lembrando que o túnel do Metro **não** tunela a porta 8000 da API.
4. Desde a correção de 22/10 não é preciso configurar IP manualmente para o Expo Go achar a API; `./scripts/dev-front.sh` cuida do override quando necessário.

</details>

<details>
<summary><strong>⚠️ CLI global legado sequestrando <code>npx expo</code></strong></summary>

Se o erro apontar `~/.nvm/.../node_modules/expo-cli` ou o banner *"The legacy expo-cli does not support Node +17"*, o problema é o `expo-cli` global deprecado, não o projeto.

```bash
npm rm -g expo-cli
cd src/frontend/smart-parking
rm -rf node_modules .expo && npm ci
ls node_modules/.bin/expo
```

Se `npm ci` termina bem mas `.bin` desaparece, o filesystem não cria symlinks (comum em NTFS/exFAT montado em `/media/...`): mova o repositório para uma partição Linux ext4 e reinstale. Os scripts do projeto chamam `npx expo ...`, que prioriza o binário local.

</details>

---

<a id="equipe-contato-e-licenca"></a>
## 15. Equipe, contato e licença

**Equipe PEX:** Breno Santos · Gabriel Almeida · Jonas Almeida — papéis detalhados em [2. Autores e Porquê](#autores-e-porque).

Projeto acadêmico PEX — Manaus/AM · contato: <behsolutionsandautomations@gmail.com>

Distribuído sob licença **MIT** — veja [LICENSE](LICENSE). Copyright © 2026 Breno Santos.

Feito com 💙 para facilitar a ida ao shopping · **Smart Parking Shoppings**
