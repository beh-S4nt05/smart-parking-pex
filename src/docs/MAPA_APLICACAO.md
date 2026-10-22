# Mapa completo da aplicação e do fluxo de acesso

> Rodada de 22/10 (auditoria "tudo amarrado, nada solto"). Este documento é o
> **índice navegável do sistema inteiro**: camadas, cada rota e quem pode
> chamá-la, o caminho de um pedido desde o toque na tela até o banco, o grafo
> de exclusões, os tokens de animação e as amarrações de erro. Se algo aqui
> divergir do código, o código manda — e o trecho aqui é bug de doc a reportar.

- Contrato funcional (o que o sistema faz): [`SDD.md`](SDD.md)
- Régua de entrega: [`MARCAS_ENTREGA.md`](MARCAS_ENTREGA.md)
- Regras de migração: [`MIGRACOES.md`](MIGRACOES.md)

---

## 1. Camadas e arquivos que importam

```
usuário (Expo Go / navegador)
  └─ src/frontend/smart-parking          RN + Expo SDK 57 + NativeWind 4
       src/app/*.tsx        telas (router)
       src/components/ui.tsx  primitivas visuais + animações (RN core Animated)
       src/services/api.ts    48 métodos → UM ponto de saída HTTP
       src/hooks/*            estado + cache AsyncStorage (sp:cache:*)
  └─ HTTP (JSON, Bearer)  ← mesma URL p/ web e mobile (EXPO_PUBLIC_API_URL)
       └─ src/backend                       FastAPI (porta 8000; prod 80 via nginx)
            main.py                composição: middleware, CORS, lifespan (zapador)
            core/security_middleware.py  headers, scanners, tamanho corpo, anti-duplic.
            core/deps.py           decode JWT → usuário da requisição
            core/hmac_verify.py    (produção) assinatura de request — PROTECAO_REQUISICOES.md
            api/auth.py            registrar/login/refresh/logout/me/sensores-sociais
            api/api.py             leitura pública + motorista (reserva/pagamento/histórico)
            api/admin.py           CRUD de gestão (111 rotas no total no app)
            api/sensores.py        ingestão por X-Device-Key (idempotente por (sensor,seq))
            rules/*                REGRA PURA, testável sem HTTP
            models/db_models.py    14 tabelas (authoritative schema)
            migrations/            Alembic baseline 3c79cee6fe1f (PG) — SQLite dev = create_all
```

Regra da casa: **rotas finas, regras em `rules/`**. Se uma rota tem `if` de
negócio, o `if` deveria estar num service.

## 2. Fluxo de acesso — do toque ao banco

```
1. Login (auth.tsx)
   POST /api/login {email|telefone, senha}
   → {access_token (15min), refresh_token (7d), user}
   → salvo em AsyncStorage (sp:auth.*) — web e mobile usam o MESMO storage.

2. Cada pedido (api.ts)
   headers = Authorization: Bearer <access>  [+ X-HMAC-* só em produção]
   401 → fila de refresh single-flight (1 refresh para N requests 401)
         → re-tenta os pendentes; refresh morto → signOut global + /login.

3. Servidor (por request, nesta ordem)
   SecurityHeadersMiddleware  [só produção]
     · headers anti-sniff · bloqueia UA de scanner · corpo ≤ MAX_BODY_KB
     · anti-duplicidade (POST/PUT/PATCH/DELETE idênticos <1s → 429)
       — desligável por BLOQUEIO_DUPLICIDADE=false (padrão)
   CORS (origens .env) → TrustedHost (prod) → [HMAC verify (prod)]
   get_db (sessão SQLAlchemy; close no fim = rollback implícito)
   Depends(get_usuario_*): decode JWT → Usuario no banco (is_ativo?) →
     revogação: timestamptz do logout vs iat do token (auth_service)
   regra de escopo (garantir_estacionamento_no_escopo / garantir_vagas_no_escopo):
     gestor/financeiro só toca na FILIAL dele — 403 com mensagem nomeada

4. Saída
   schemas pydantic → JSON · erro → {detail} → apiErrorMessage() → Alert/BlocoErro
```

**Dois caminhos que NÃO usam login humano:**
- **Sensores** (`api/sensores.py`): header `X-Device-Key` (SHA-256 na tabela
  `sensores`, emitido/revogado só pelo admin). Idempotência por
  `(sensor_id, seq)` — retransmissão de rede devolve 200, não 2ª estadia.
- **Simulador QR** (`api/admin.py` + `rules/simulador_service.py`): admin cria
  sessão em memória → URL/QR tokenizados → a câmera do app abre
  `/simulador?sessao=` → operações exigem JWT admin → sessão morre por
  expiração, revogação manual **ou exclusão do estacionamento** (amarração
  desta rodada, §6).

## 3. Matriz papel × recurso (o "quem pode o quê" completa)

| Papel | Ver mapa/vagas | Reservar/pagar | Gerir filial | Gerir todas filiais | Usuários | Sensores | Simulador |
|---|---|---|---|---|---|---|---|
| anônimo | ✅ público | ❌ (login pedido) | ❌ | ❌ | ❌ | ❌ | ❌ |
| motorista (usuario) | ✅ | ✅ (o próprio) | ❌ | ❌ | só o próprio perfil | ❌ | ❌ |
| gestor | ✅ | — | ✅ **só a filial dele** (escopo) | ❌ | ❌ | ❌ | ❌ |
| financeiro | ✅ | — | ✅ filial: caixa/relatórios/preços | ❌ | ❌ | ❌ | ❌ |
| admin global | ✅ | — | ✅ todas | ✅ | ✅+guards | ✅ emite/revoga chave | ✅ |

Guards do admin (novos/verificados nesta rodada):
- `PATCH /usuarios/{id}/ativar-desativar` **recusa admin** (400) — não existe
  rota que desligue o próprio admin por engano.
- `PUT /usuarios/{id}`: **último admin ativo** não pode ser rebaixado nem
  desativado (422, `atualizar_usuario_admin`).
- `POST /admin/usuarios` + promover/demover: validação de role e vínculo de
  gestor/financeiro a uma filial (SIM102 consolidado).

## 4. Inventário de rotas (71) — gerado do código em 22/10

| # | Arquivo | Método | Rota | Quem chama |
|---:|---|---|---|---|
| 1 | api | GET | `/` | público |
| 2 | api | GET | `/health` | público |
| 3 | api | GET | `/version` | público |
| 4 | api | GET | `/status` | público |
| 5 | api | GET | `/estacionamentos` | público |
| 6 | api | GET | `/estacionamentos/{id}/vagas` | público |
| 7 | api | GET | `/estacionamentos/{id}/proxima-vaga` | público |
| 8 | api | POST | `/reservas` | logado |
| 9 | api | DELETE | `/reservas/{id}` | logado |
| 10 | api | GET | `/reservas/minhas` | logado |
| 11 | api | GET | `/vagas` | público |
| 12 | api | PATCH | `/vagas/lote/status` | gestor/financeiro + escopo |
| 13 | api | PATCH | `/vagas/{id}/status` | gestor/financeiro + escopo |
| 14 | api | GET | `/relatorios/fluxo` | gestor/financeiro + escopo |
| 15 | api | GET | `/relatorios/fluxo/publico` | público |
| 16 | api | GET | `/relatorios/ocupacao` | gestor/financeiro + escopo |
| 17 | api | GET | `/relatorios/ocupacao-historica` | gestor/financeiro + escopo |
| 18 | api | GET | `/relatorios/rotacao` | gestor/financeiro + escopo |
| 19 | api | GET | `/relatorios/fluxo/csv` | gestor/financeiro + escopo |
| 20 | api | GET | `/relatorios/financeiro/csv` | gestor/financeiro + escopo |
| 21 | auth | POST | `/registrar` | público |
| 22 | auth | POST | `/login` | público |
| 23 | auth | POST | `/refresh` | público |
| 24 | auth | POST | `/logout` | logado |
| 25 | auth | PUT | `/me` | logado |
| 26 | auth | PUT | `/senha` | logado |
| 27 | auth | GET | `/me` | logado |
| 28 | auth | POST | `/login/google` | público |
| 29 | auth | POST | `/login/facebook` | público |
| 30 | auth | POST | `/login/apple` | público |
| 31 | admin | POST | `/estacionamentos` | admin |
| 32 | admin | PUT | `/estacionamentos/{id}` | admin |
| 33 | admin | DELETE | `/estacionamentos/{id}` | admin |
| 34 | admin | POST | `/andares` | admin |
| 35 | admin | DELETE | `/andares/{id}` | admin |
| 36 | admin | PUT | `/andares/{id}` | admin |
| 37 | admin | PUT | `/vagas/{id}` | admin |
| 38 | admin | POST | `/usuarios/{id}/reset-senha` | admin |
| 39 | admin | POST | `/sensores` | admin |
| 40 | admin | GET | `/sensores` | admin |
| 41 | admin | POST | `/sensores/{id}/revogar` | admin |
| 42 | admin | POST | `/vagas` | admin |
| 43 | admin | POST | `/vagas/lote` | admin |
| 44 | admin | DELETE | `/vagas/{id}` | admin |
| 45 | admin | POST | `/usuarios` | admin |
| 46 | admin | PUT | `/usuarios/{id}` | admin |
| 47 | admin | GET | `/usuarios` | admin |
| 48 | admin | PATCH | `/usuarios/{id}/ativar-desativar` | admin |
| 49 | admin | PATCH | `/usuarios/{id}/promover-admin` | admin |
| 50 | admin | GET | `/dashboard` | admin |
| 51 | admin | POST | `/simulador/sessoes` | admin |
| 52 | admin | GET | `/simulador/sessoes` | admin |
| 53 | admin | DELETE | `/simulador/sessoes/{token}` | admin |
| 54 | admin | GET | `/simulador/sessoes/{token}/validar` | público |
| 55 | admin | GET | `/eventos` | gestor/financeiro + escopo |
| 56 | admin | GET | `/ocupacao-andares/{estacionamento_id}` | gestor/financeiro + escopo |
| 57 | admin | POST | `/financeiro/precos` | gestor/financeiro + escopo |
| 58 | admin | GET | `/financeiro/precos/{estacionamento_id}` | gestor/financeiro + escopo |
| 59 | admin | GET | `/financeiro/pagamentos/{estacionamento_id}` | gestor/financeiro + escopo |
| 60 | admin | GET | `/financeiro/resumo` | gestor/financeiro |
| 61 | admin | GET | `/gestor/dashboard` | gestor/financeiro |
| 62 | admin | POST | `/financeiro/calcular-tarifa` | gestor/financeiro + escopo |
| 63 | admin | POST | `/financeiro/pagamento/registrar` | gestor/financeiro + escopo |
| 64 | admin | POST | `/financeiro/pagamento/gerar-pix` | público |
| 65 | admin | POST | `/financeiro/pagamento/{id}/confirmar` | gestor/financeiro + escopo |
| 66 | admin | POST | `/financeiro/caixa/abrir` | gestor/financeiro + escopo |
| 67 | admin | POST | `/financeiro/caixa/{id}/fechar` | gestor/financeiro + escopo |
| 68 | admin | GET | `/financeiro/caixa/aberto/{estacionamento_id}` | gestor/financeiro + escopo |
| 69 | admin | POST | `/financeiro/cupons` | gestor/financeiro + escopo |
| 70 | admin | GET | `/financeiro/cupons/{estacionamento_id}` | gestor/financeiro + escopo |
| 71 | sensores | POST | `/eventos` | chave do sensor |

Leitura: "público" = sem token algum (só leitura de mapa ou auth);
"gestor/financeiro + escopo" = token da pessoa **e** a filial do corpo/rota tem
de ser a dela. Rotas novas = registrar aqui + `INTEGRACAO_FRONTEND.md`.

## 5. Tela ↔ endpoint ↔ tabela

| Tela (src/app) | Endpoints que chama | Tabelas que lê/escreve |
|---|---|---|
| `index` (splash) | `GET /health` | — |
| `login` / `cadastro` | `POST /login` `/registrar` | usuarios |
| `mapa` (busca) | `GET /estacionamentos`, `/estacionamentos/{id}/vagas`, `/proxima-vaga` | estacionamentos, andares, vagas |
| `shopping/[id]` | idem + `POST /reservas` (logado) | + reservas |
| `pagamento/[id]` | `POST /pagamentos` · `/pagamentos/{id}/confirmar` | pagamentos, historicos |
| `minhas-estadias` | `GET /historico` | historicos |
| `perfil` | `PUT /auth/me`, `POST /auth/reset-senha`, `POST /logout` | usuarios, revogacoes |
| `dashboard` (5 abas) | `GET /admin/resumo`, CRUD estacionamentos/andares/vagas, `PATCH /vagas/{id}/status`, `/vagas/lote/status`, usuarios, financeiro, relatórios CSV | todas as 14 |
| `simulador-qr` / `simulador` | `POST /admin/simulador/sessoes`, validar, operar | vagas (+estado memória) |
| admin Sensores | `POST /admin/sensores` (+eventos/últimos) | sensores, sensor_eventos |

## 6. Grafo de exclusões — ordem do `_purgar_operacional` (blindado nesta rodada)

`DELETE /api/admin/estacionamentos/{id}` → o serviço DELETES na ordem —
Postgres honra `ondelete` do banco, mas **a linha de frente é sempre o
serviço** (SQLite dev não tem FK ligado):

```
1. historicos.pagamento_id ← NULL        (FK RESTRICT apontando p/ pagamento vivo)
2. pagamentos (por est)                    · historicos (por est)
3. fechamentos_caixa (por est)             antes dos usuários (RESTRICT em usuario_abertura_id)
4. sensores + sensor_eventos (por est)     ← NOVO: sem relationship no ORM, ficava órfão
5. reservas dos usuários vinculados        ← NOVO: gestor que reservou em OUTRA filial
   pagamentos desses usuários → NULL
6. usuarios gestor/financeiro da filial    ← NOVO: a conta existia PARA a filial
7. sessões do simulador (memória)          ← NOVO: revogar_por_estacionamento()
8. andares → vagas → estacionamento        (cascade do ORM; reserva/cupom/config/delete-orphan)
```

Cascata por alvo menor: `deletar_andar`/`deletar_vaga` fazem o mesmo purge
restrito aos `vaga_ids` (sensor_eventos dessas vagas → `vaga_id` NULL: o log
bruto sobrevive como auditoria, o elo com a estadia morre com a vaga).
`ondelete` defensivo adicionado nos modelos (13 FKs) vale para **bancos
novos**; bancos existentes mantêm o que têm — o serviço cobre os dois casos.
Testes: `tests/test_exclusao_admin.py` (7 casos, todos os passos acima).

## 7. Animações — tokens e tempos (RN core Animated, zero pacote novo)

| Peça | Movimento | Tempo | Onde |
|---|---|---|---|
| `Botao` (press) | **nativo**: scale 1→0.96 spring friction 7 · tension 180 + `hitSlop` 4/8 · **web**: `active:scale-[0.97]` em CSS puro (`transition-transform duration-100`) — ver nota abaixo | ~100–140ms | ui.tsx |
| `ModalForma` | Modal fade + folha entra scale 0.95→1 & fade | 170ms | ui.tsx |
| `FadeTroca` (abas do painel) | fade puro ao trocar aba (nativo; web renderiza direto) | **130ms** | ui.tsx |
| `AnimarEntrada` (cards/listas 1º paint) | fade + subida 12px | 320ms | ui.tsx |
| `BarraOcupacao` | tween da largura | 400ms | ui.tsx |
| teclado no modal | `KeyboardAvoidingView` (padding no iOS) | nativo | ModalForma |

**Dualidade web×nativo (corrigida por medição em 22/10, rodada UI/UX):**
`Animated.createAnimatedComponent` é invisível ao css-interop do NativeWind na
web e derrubava o `className` inteiro de quem o usasse (o `<button>` do login
saía do pré-render sem bg/padding = "botão invisível"). O `Botao` agora roda
Pressable puro na web (feedback por `:active` CSS) e Animated no nativo (guarda
do crash Fabric do PR#7). Pelo mesmo motivo, `AnimarEntrada`/`FadeTroca` dão
short-circuit na web: inline `opacity:0` do SSR que não hidrata a tempo deixava
cards deslocados sobre a lista de baixo. Medida de QA que provou ambos: grepar
o `dist/*.html` do `expo export web` (inlines com `opacity: 0` = 0; botão com
`bg-blue-600 px-5` = presente). Métodos completos em `QA_UI_UX.md`.

Regras que sustentam o "tempo de resposta": feedback de toque < 150ms;
animação de navegação/entrada pode chegar a 320ms; tudo `useNativeDriver:
true` (sem JS thread no meio); nenhuma animação bloqueia input; o
`AnimatedPressable` (compat Fabric, PR#7) continua sendo a base — **não**
substituir por reanimated (proibido: política "zero npm install na V-02").

**Edge-to-edge (Android/iOS, pedido do usuário em 22/10):** `app.json` já traz
`android.edgeToEdgeEnabled: true` — o app ocupa a tela inteira com as barras do
sistema flutuando transparentes sobre o conteúdo. O `_layout.tsx` usa
`useSafeAreaInsets()` (react-native-safe-area-context, já era dependência — zero
pacote novo) para dar a TODAS as telas `paddingTop = insets.top` e
`paddingBottom = max(insets.bottom, 8)` via `Stack contentStyle`: nenhum botão
fica inatingível sob a barra de status e nenhuma lista termina embaixo da barra
de navegação/gesto. Na web os insets são 0 → comportamento idêntico ao antigo.
Escondimento total da barra (immersive) foi rejeitado de propósito: engolir
relógio/bateria em app de operação não é acessível, e o usuário marcou o respiro
seguro como o ideal.

Layout — travas contra quebra: nomes/endereços/e-mails longos com
`numberOfLines={1}` (card de estacionamento e de usuário; e-mail com
`ellipsizeMode="middle"`); modal limitado a `88%` da altura da janela +
`ScrollView` 420 → formulário alto não some atrás da barra do sistema;
VagaMapa recalcula colunas por `useWindowDimensions` (4/6/8).

## 8. Amarrações de erro (código → o que a pessoa vê)

| Origem | UI |
|---|---|
| 401 em qualquer request | fila de refresh 1× → retry; sem refresh → volta ao login (nunca tela morta) |
| 403 escopo | mensagem nomeia o recurso ("fora da sua filial") — apiErrorMessage passa o `detail` |
| 409 reserva/pagamento | alerta + recarrega o mapa (estado pode ter mudado na mão de outro) |
| 429 rate-limit (logarametador) e anti-duplicidade | toast/alerta "muito rápido" — pedido já foi bloqueado no servidor |
| 422 validação | campo a campo via `Campo` (erro inline), nunca alert nu |
| 5xx / rede fora | `BlocoErro` com botão "tentar de novo" — tela nunca fica em branco |
| rede lenta no boot | cache `sp:cache:*` mostra o último dado + selo "desatualizado" |

No backend, "nada solto" = `ruff check` **0** com regras de correção ligadas
(F/B/S/PERF/SIM/C4/DTZ — `src/backend/ruff.toml` com exceções justificadas
linha a linha) + 38 testes. Estilo opinativo (isort/UP) fica fora de
propósito: sem reforma estética em código em uso.

## 9. Flags de configuração novas (dev/test já coerentes)

| Flag | Default | Efeito |
|---|---|---|
| `BLOQUEIO_DUPLICIDADE` | `false` | middleware de produção: request idêntico <1s → 429 (a chave era calculada e ignorada — virou guard real nesta rodada) |

## 10. "Mexi em X, atualize Y" 

| Mudou | Atualizar junto |
|---|---|
| coluna no banco | `db_models` + schema pydantic + `api.ts` (types) + tela + **migration** (MIGRACOES.md) + tabela §4/§5 deste mapa |
| rota nova | deps de guarda → tabela §4 → `INTEGRACAO_FRONTEND.md` → método em api.ts → chamada na tela |
| exclusão em cascata | §6 (purga + teste em `test_exclusao_admin.py`) + FK `ondelete` no modelo |
| timing/animação | §7 + manter `useNativeDriver: true` |
| flag/env | `core/config.py` + `.env.example` + README + §9 |
