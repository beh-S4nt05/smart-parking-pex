# 🗺️ Guia Completo de Integração Frontend ↔ SmartParking API
Todos os formatos de dados exatos, payloads de requisição, respostas e autenticação social inclusos.

---

## 🔐 Autenticação: Métodos disponíveis

A API aceita 4 formas de login:
| Método | Rota |
|--------|------|
| 👤 E-mail e senha tradicional | `POST /auth/login` |
| 🔵 Login com Google | `POST /auth/login/google` |
| 🟦 Login com Facebook | `POST /auth/login/facebook` |
| 🍎 Login com Apple ID | `POST /auth/login/apple` |

Todos os métodos de login retornam **exatamente a mesma resposta**: `access_token` + `refresh_token`.
Após o login social, se o usuário não tiver cadastro ele é criado automaticamente.

---

### 🔵 Login com Google:
1.  No frontend use a biblioteca oficial do Google/Firebase para autenticar o usuário
2.  Pegue o `id_token` retornado pelo Google
3.  Envie para o backend:
```http
POST /auth/login/google
Content-Type: application/json
```
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij..."
}
```
O backend valida o token diretamente com os servidores do Google, sem necessidade de guardar senha.

---

### 🟦 Login com Facebook:
1.  No frontend use o Facebook Login SDK
2.  Pegue o `access_token` retornado após autorização
3.  Envie para o backend:
```http
POST /auth/login/facebook
Content-Type: application/json
```
```json
{
  "access_token": "EAAJZCMZA..."
}
```

---

### 🍎 Login com Apple ID:
1.  No frontend use Sign in with Apple
2.  Pegue o `identity_token` retornado
3.  Envie para o backend:
```http
POST /auth/login/apple
Content-Type: application/json
```
```json
{
  "identity_token": "eyJraWQiOiJlWGF1c...",
  "nome": "João da Silva"
}
```

---

## 📝 Todos os payloads de cadastro/envio de dados do frontend
Formato exato do JSON que deve ser enviado no corpo de cada requisição:

---

### 1. 📝 Cadastro de usuário comum (pelo app)
```http
POST /auth/registrar
```
✅ **Campos obrigatórios:**
```json
{
  "nome": "João da Silva",
  "email": "joao@email.com",
  "senha": "minhasenha123"
}
```
⚙️ **Campos opcionais:**
```json
{
  "telefone": "(92)99999-9999",
  "placa_veiculo": "AMZ1234"
}
```
❌ **Validações:**
- `nome`: mínimo 2 caracteres, máximo 120
- `email`: deve ser um e-mail válido
- `senha`: mínimo 6 caracteres
- `placa_veiculo`: máximo 10 caracteres

✅ **Resposta sucesso 201 Created:**
Retorna os dados do usuário cadastrado (sem a senha).

---

### 2. 👤 Login com e-mail (ou telefone) e senha
```http
POST /auth/login
```
**Payload exato:**
```json
{
  "email": "joao@email.com",
  "senha": "minhasenha123"
}
```
> O campo `email` aceita **e-mail OU telefone** (com ou sem máscara — `(92) 99911-0000` funciona).
> Se o telefone for único e o usuário tiver senha cadastrada, o login é realizado.

✅ **Resposta 200 OK (igual para TODOS os métodos de login):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "nome": "João",
    "email": "joao@email.com",
    "role": "usuario",
    "estacionamento_id": null,
    "placa_veiculo": "ABC1D23",
    "is_ativo": true
  }
}
```
> O `user` veio para ficar no login — o frontend não precisa chamar
> `GET /auth/me` logo após autenticar (usa apenas ao reabrir o app com
> token salvo, para validar a sessão).

---

### 3. 🔄 Renovar access token expirado
```http
POST /auth/refresh
```
**Payload:**
```json
{
  "refresh_token": "seu_refresh_token_aqui"
}
```
✅ **Resposta:** Retorna novo `access_token`

---

### 4. 🅿️ Criar reserva (usuário motorista logado)
```http
POST /api/reservas
Authorization: Bearer {access_token}
```
**Payload exato:**
```json
{
  "vaga_id": "uuid-da-vaga",
  "horario_inicio": "2026-10-01T14:00:00",
  "horario_fim": "2026-10-01T16:00:00"
}
```
⚙️ **Campos opcionais:**
```json
{
  "observacoes": "Reserva para consulta médica"
}
```
❌ **Validações:**
- Datas em formato ISO 8601
- `horario_fim` deve ser maior que `horario_inicio`
- Vaga deve estar com status "livre"

---

### 5. ⚙️ Atualizar status de vaga (sensor/manual/simulador)
```http
PATCH /api/vagas/{uuid-da-vaga}/status
```
**Payload exato:**
```json
{
  "status": "ocupada",
  "origem": "simulador"
}
```
`origem` (opcional): `"sensor"` · `"simulador"` · `"app_motorista"` · `"manual"` —
fica registrado no histórico e aparece no feed de eventos do painel.

### 5.1 ⚡ Lote de status (simulador — várias vagas em 1 request)
```http
PATCH /api/vagas/lote/status
```
```json
{
  "vaga_ids": ["uuid-1", "uuid-2"],
  "status": "livre",
  "origem": "simulador"
}
```
Resposta: `{ "solicitadas": 2, "atualizadas": 2, "nao_encontradas": [], "vagas": [...] }` —
somente o que **mudou de verdade** gera histórico/evento.

### 5.2 🔎 Listar vagas com filtro (público)
```http
GET /api/vagas?estacionamento_id={uuid}&andar_id={uuid}&status=livre&tipo=pcd
```
Usado pelo painel para inspeção rápida; retorna as mesmas vagas do mapa
(código, posição no grid, status, tipo, andar).
✅ **Status aceitos:**
- `"livre"`: Vaga disponível
- `"ocupada"`: Vaga com veículo
- `"reservada"`: Vaga reservada
- `"inativa"`: Vaga em manutenção

---

## 🔧 Rotas exclusivas do Painel (Admin, Gestor, Financeiro)

---

### 👑 Criar novo usuário (admin global)
```http
POST /api/admin/usuarios
Authorization: Bearer {admin_token}
```
**Payload exato (todos os cargos):**
```json
{
  "nome": "Maria Souza",
  "email": "maria@estacionamento.com",
  "senha": "senha123",
  "role": "gestor",
  "estacionamento_id": "uuid-do-estacionamento",
  "telefone": "(92)99999-9999",
  "placa_veiculo": null
}
```
✅ **Valores aceitos para `role`:**
- `"publico"`
- `"usuario"` (padrão para motoristas)
- `"financeiro"`
- `"gestor"`
- `"admin"`
⚠️ **Para `gestor` e `financeiro`: O campo `estacionamento_id` É OBRIGATÓRIO**

---

### 🅿️ Criar novo estacionamento (admin global)
```http
POST /api/admin/estacionamentos
Authorization: Bearer {admin_token}
```
**Payload exato:**
```json
{
  "nome": "Shopping Ponta Negra",
  "endereco": "Av. Coronel Teixeira, 1000",
  "total_andares": 3,
  "total_vagas": 150,
  "hora_abertura": "06:00",
  "hora_fechamento": "23:00",
  "taxa_hora": 10.0
}
```
⚙️ **Campos opcionais:**
```json
{
  "telefone": "(92)3000-1234",
  "latitude": -3.0853,
  "longitude": -60.1088
}
```

---

### 📊 Criar novo andar (admin/gestor)
```http
POST /api/admin/andares
```
**Payload exato:**
```json
{
  "estacionamento_id": "uuid-do-estacionamento",
  "numero_andar": 2,
  "capacidade": 50
}
```

---

### 🅿️ Criar vaga individual (admin/gestor)
```http
POST /api/admin/vagas
```
**Payload exato:**
```json
{
  "andar_id": "uuid-do-andar",
  "codigo": "C15",
  "tipo": "comum",
  "posicao_x": 40,
  "posicao_y": 12
}
```
✅ **Valores para `tipo`:** `comum`, `idoso`, `pcd`, `moto`, `eletrico`

---

### ⚡ Criar lote de vagas (cadastro rápido - admin/gestor)
```http
POST /api/admin/vagas/lote
```
Cria várias vagas automaticamente com códigos sequenciais!
**Payload exato:**
```json
{
  "andar_id": "uuid-do-andar",
  "quantidade": 50,
  "prefixo_codigo": "C"
}
```
✅ Resultado: Cria 50 vagas: C01, C02, C03... C50 de uma vez!

---

### 💰 Configurar preço de vaga (admin/gestor)
```http
POST /api/admin/financeiro/precos
```
**Payload exato:**
```json
{
  "estacionamento_id": "uuid-do-estacionamento",
  "tipo_vaga": "comum",
  "valor_hora": 8.0,
  "valor_diaria": 50.0,
  "tolerancia_minutos": 15
}
```
💡 Se já existir preço para o tipo de vaga, ele é atualizado automaticamente.

---

### 💳 Registrar pagamento (admin/gestor/financeiro)
```http
POST /api/admin/financeiro/pagamentos
```
**Payload exato:**
```json
{
  "historico_id": "uuid-do-registro-de-entrada",
  "metodo_pagamento": "pix",
  "valor_total": 16.0,
  "comprovante_url": "https://url-do-comprovante.jpg",
  "observacoes": "Pagamento realizado no caixa"
}
```
✅ **Valores para `metodo_pagamento`:** `pix`, `cartao`, `dinheiro`

---

## 📋 Formato padrão de erros do backend
Todos os erros de qualquer endpoint seguem EXATAMENTE esse formato, sem exceção:
```json
{
  "detail": "Mensagem de erro clara para exibir para o usuário"
}
```

Códigos de erro comuns:
| Código | Significado |
|--------|-------------|
| 400 | Erro de regra de negócio (ex: vaga não disponível) |
| 401 | Token inválido/expirado ou login/senha errados |
| 403 | Sem permissão para acessar o recurso |
| 404 | Recurso não existe |
| 422 | Formato de dado inválido (ex: e-mail errado, campo faltando) |
| 503 | Serviço não configurado (ex: login Google não configurado) |

---

## 📱 Configuração recomendada do Axios no frontend
```javascript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const api = axios.create({
  baseURL: 'http://SEU_IP_LOCAL:8000',
  timeout: 10000,
});

// Interceptor adiciona token JWT automaticamente
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Interceptor renova token automaticamente quando expirar
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refresh = await AsyncStorage.getItem('refresh_token');
        const { data } = await api.post('/auth/refresh', {refresh_token: refresh});
        await AsyncStorage.setItem('access_token', data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (e) {
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        // Navegar para tela de login aqui
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## ⚙️ Configuração dos provedores OAuth:
Para ativar login social adicione as chaves no arquivo `.env`:
- **Google**: Crie credenciais OAuth em https://console.cloud.google.com/, autorize os URIs de redirecionamento do seu app Expo/React Native
- **Facebook**: Crie o app em https://developers.facebook.com/
- **Apple**: Configure no https://developer.apple.com/ (obrigatório para App Store)

Login social é totalmente opcional: você pode deixar as chaves vazias no `.env` que as rotas funcionam, só vão retornar erro 503 se chamadas sem configuração.

---

## 🎯 Resumo rápido de permissões:
| Cargo | O que pode fazer? |
|-------|-------------------|
| 🌐 Público | Ver estacionamentos e mapa de vagas, sem login |
| 👤 Usuário | Fazer reservas, ver próprio perfil |
| 💰 Financeiro | Ver relatórios financeiros do seu estacionamento, registrar pagamentos |
| 🧑‍💼 Gestor | Tudo do financeiro + gerenciar vagas, andares e preços do seu estacionamento |
| 🔴 Admin | TUDO na plataforma |

---

## 📲 Frontend real (Expo) — telas web + mobile na MESMA rota

O app em `src/frontend/smart-parking` usa a API de ponta a ponta (sem mocks):

| Camada | Arquivo | Papel |
|---|---|---|
| HTTP | `src/services/api.ts` | axios + refresh automático + `parkingApi` tipado por endpoint |
| Assinatura | `src/services/requestSigner.ts` | HMAC `X-Request-*` exigido **só em produção** (ver `PROTECAO_REQUISICOES.md`) |
| Sessão | `src/context/AuthContext.tsx` + `src/hooks/useAuth.ts` | guarda tokens/usuário no storage; restaura sessão no boot |
| Dados | `src/hooks/useEstacionamentos.ts` · `useMapaVagas.ts` · `useReservas.ts` | polling (`pollingMs`) + cache de última resposta para offline |
| Telas | `src/app/*.tsx` | responsivas: `useWindowDimensions()` escolhe layout web largo vs. stack mobile na mesma rota |

**URL da API**: `.env` → `EXPO_PUBLIC_API_URL` (dev local: `http://localhost:8000`;
Expo Go no celular: IP LAN; preview: URL pública do backend). O token é o mesmo
entre web e mobile (mesma origem de storage por dispositivo).

### Fluxo admin: QR do simulador
1. Painel → aba **Simulador QR** (`/simulador-qr`): escolhe shopping + andar +
   validade → `POST /api/admin/simulador/sessoes` retorna
   `{ token, url, qr_png_base64, expira_em }` (QR pronto para `<Image>`).
2. Admin escaneia no celular (ou abre no navegador do computador — a mesma
   rota é responsiva) → `/simulador?sessao={token}` → o app valida com
   `GET /api/admin/simulador/sessoes/{token}/validar` (pública; `410` =
   expirada/revogada) e exige JWT de **administrador global** para operar —
   gestor/financeiro NÃO acessam o simulador (nem as rotas de sessão
   `POST/GET/DELETE /api/admin/simulador/sessoes`, agora `get_usuario_admin`).
3. Toque na vaga / ações em lote → `PATCH /api/vagas/.../status` com
   `origem: "simulador"`; o dashboard reflete via polling + `GET /api/admin/eventos`.
4. `DELETE /api/admin/simulador/sessoes/{token}` revoga na hora.

### Endpoints do painel (novos no contrato)
```http
GET  /auth/me                              → usuário + estacionamento_nome
GET  /api/admin/dashboard                  → totais globais (admin)
GET  /api/admin/eventos?estacionamento_id=&limite=20
GET  /api/admin/ocupacao-andares/{est}     → [{andar_id, numero_andar, total_vagas, ocupadas, livres, percentual}]
GET  /api/relatorios/fluxo?periodo=diario  → total_entradas/saidas, tempo_medio_permanencia_min, registros[]
```
⚠️ **Mudança de acesso (auditoria 20/10):** `/api/relatorios/fluxo` e
`/api/relatorios/ocupacao` passaram a exigir token de **painel**
(admin/financeiro/gestor; gestor/financeiro escopados no próprio
estacionamento). Para a **Home pública** (visitante sem login) existe
`GET /api/relatorios/fluxo/publico?periodo=diario[&estacionamento_id=]` com os
mesmos agregados e **sem** `registros[]` (não expõe valores/placas) — é o que
`parkingApi.fluxoHoje()` consome agora. As rotas `PATCH /api/vagas/*/status`
também exigem admin/gestor (o app sempre chamou com token; integrações de
sensor devem autenticar).
O gráfico **"Fluxo de veículos por hora"** do dashboard é montado no cliente
agrupando `registros[].entrada_em` por hora — não há endpoint por hora.

### Login/redirect mesclado
`/login` aceita **e-mail ou telefone**; após `POST /auth/login`, redireciona por
papel (`admin|gestor|financeiro → /dashboard`, `usuario → /`). Cadastro:
`POST /auth/registrar` (`nome`, `email`, `senha ≥ 6`, `telefone?`, `placa_veiculo?`)
com auto-login em seguida.
