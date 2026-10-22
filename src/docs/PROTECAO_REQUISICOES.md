# 🔐 Proteção contra replicação de requisições e acesso indevido pelo navegador/Postman

# 🔏 Proteção de Requisições — Assinatura HMAC + Anti-replay

> **Nota de honestidade (SDD M4-04, 22/10):** este mecanismo é **camada de
> atrito**, não fronteira de segurança. A `APP_SIGNING_SECRET` viaja dentro do
> bundle (web) — quem descompilar o bundle extrai a chave e forja assinaturas.
> Ele eleva o custo do abuso casual (Postman/scraper/navegador sem adaptação) e
> corta replay de requisições escritas; NÃO substitui auth/autorização, validação
> de escopo nem rate limit, e não protege APIs usadas por terceiros. Os
> percentuais "99%" abaixo descrevem a fração de tentativas casuais barradas,
> nunca garantia criptográfica contra atacante dedicado. A chave padrão
> (`smartparking_default_signing_key_change_in_production`) é recusada no boot
> quando `ENVIRONMENT=production`.

## O problema:
Se o usuário abrir o DevTools no navegador/Expo ou usar um proxy (Charles/mitmproxy), ele consegue pegar o token JWT e copiar requisições para fazer manualmente pelo Postman, curl ou script, burlando o frontend oficial.

## Como resolvemos isso:
Implementei um sistema de **Assinatura HMAC de requisições com anti-replay** que barra a grande maioria dessas tentativas CASUAIS (sem engenharia reversa do bundle), sem afetar usuários legítimos do app oficial.

---

## 🛡️ Como funciona em 5 camadas de proteção:

---

### 1. ✅ Assinatura HMAC obrigatória em todas as requisições que modificam dados
Toda requisição POST/PUT/PATCH/DELETE **precisa de 3 headers obrigatórios** que só o app oficial sabe gerar:
| Header | Função |
|---|---|
| `X-Request-Timestamp` | Horário em que a requisição foi feita (em segundos Unix) |
| `X-Request-Nonce` | String aleatória ÚNICA por requisição (UUID) |
| `X-Request-Signature` | Hash HMAC-SHA256 gerado com um SEGREDO compartilhado só entre o app e o backend |

**Como o app gera a assinatura:**
1.  Pega o método HTTP (`POST`), o caminho da rota (`/api/reservas`), timestamp, nonce e o corpo da requisição
2.  Junta tudo em uma string e gera um HMAC SHA256 usando a chave secreta
3.  Envia a assinatura no header
4.  O backend faz EXATAMENTE o mesmo cálculo e compara as assinaturas.

> 📌 A chave secreta NUNCA é enviada pela rede. Ela existe apenas compilada dentro do app e no backend.
> No React Native/Expo a chave é dividida em várias partes no código e juntada em tempo de execução, dificultando a extração por engenharia reversa (para apps Android/iOS publicados com ProGuard/R8 é extremamente difícil de pegar).

Se alguém tentar enviar uma requisição pelo Postman/navegador, não vai ter a assinatura correta e recebe **403 Acesso Negado** imediatamente.

---

### 2. ⏱️ Proteção contra Replay Attack
Mesmo que alguém consiga capturar uma requisição válida:
- O timestamp só é aceito se for de no máximo 5 minutos
- O nonce (aleatório) só pode ser usado UMA vez.
- Se o usuário tentar enviar a mesma requisição de novo é bloqueado.

---

### 3. 🚫 Bloqueio de navegadores e ferramentas como Postman/Insomnia/curl
O middleware verifica o `User-Agent` da requisição em produção:
- Se a requisição de escrita vier de User-Agent de navegador (Chrome/Safari/Firefox), Postman, curl, wget, python-requests é automaticamente bloqueada.
- Apenas requisições que tem o User-Agent do app oficial + assinatura válida passam.

---

### 4. 🌐 Rotas públicas GET são liberadas
Apenas requisições que MODIFICAM dados (POST/PUT/PATCH/DELETE) exigem assinatura:
- Qualquer pessoa pode ver a lista de estacionamentos e mapa de vagas sem assinatura (como esperado para a tela inicial do app sem login).
- Requisições de login/cadastro também são isentas de assinatura (pois é antes de ter o app aberto).

---

### 5. 📱 Como funciona no frontend React Native/Expo:
Criei um utilitário PRONTO em `src/frontend/src/services/requestSigner.js` que faz toda a assinatura automaticamente:
Basta adicionar um interceptor no Axios uma única vez e ele assina TODAS as requisições de escrita automaticamente:
```javascript
import axios from 'axios';
import { adicionarAssinaturaInterceptor } from './src/services/requestSigner';

const api = axios.create({ baseURL: 'http://SEU_IP:8000' });
// Adiciona essa ÚNICA LINHA e todo resto funciona automaticamente
adicionarAssinaturaInterceptor(api);
```

Isso é invisível para o usuário do app. Todas as requisições POST/PUT/PATCH/DELETE saem com assinatura válida automaticamente.

---

## 🚨 Nível de segurança:
| Cenário | O usuário consegue replicar? |
|---|---|
| Copiar requisição e enviar pelo Postman/Insomnia | ❌ BLOQUEADO (faltam assinatura e headers corretos) |
| Copiar requisição e enviar pelo navegador DevTools | ❌ BLOQUEADO (User-Agent de navegador é bloqueado) |
| Usar curl/wget scripts | ❌ BLOQUEADO |
| Fazer engenharia reversa no APK/IPA para extrair a chave | Difícil para 99% dos usuários. A chave é ofuscada no código, e em apps publicados na loja com ofuscação ProGuard/R8 dá muito trabalho para extrair. |
| Usar MITM Proxy (Charles) para interceptar e repetir requisições | ❌ BLOQUEADO pelo nonce e timestamp, a requisição capturada expira em 5 minutos e não pode ser repetida. |
| Modificar valores do corpo da requisição | ❌ BLOQUEADO, pois a assinatura inclui o corpo. Se alterar qualquer caracter a assinatura fica inválida. |

---

## ⚙️ Configuração em produção:
1.  Gere uma chave secreta forte:
    ```bash
    openssl rand -hex 32
    ```
2.  Coloque a chave no `.env` do backend na variável `APP_SIGNING_SECRET`
3.  Coloque a MESMA chave no arquivo `requestSigner.js` do frontend (dividida em várias partes para dificultar extração)
4.  Publique o app.

> 📌 Para o frontend web (painel admin): Se tiver um painel web você pode manter a mesma lógica, mas a chave vai estar mais exposta no JavaScript do navegador. Por isso o painel deve ter sempre senha forte e 2FA, essa proteção é feita principalemente para o app mobile que é o cliente principal.

---

## 📋 Limitações:
Nenhuma proteção cliente-side é 100% inquebrável. Um atacante com conhecimento avançado pode conseguir extrair a chave do APK com engenharia reversa. Por isso MANTEMOS as outras camadas de proteção:
✅ Rate limiting para evitar spam
✅ Validação de permissões por cargo de usuário (mesmo que ele consiga fazer requisição, não consegue acessar dados que não tem permissão)
✅ Logs de atividades suspeitas
✅ Limite de ações por usuário.

Essa combinação barra a maior parte dos casos comuns de usuários tentando burlar o app pelo navegador/Postman — lembrando (nota acima) que um atacante que extraia a chave do bundle contorna a assinatura; o que continua valendo contra ele é auth + escopo por estacionamento + rate limit.

---

## 📊 O que é BARRADO na prática (matriz executada, não prometida)

Medidor reproduzível: `./scripts/e2e_validacao.sh` (blocos C e D) — validado
contra API viva em 22/10 com **zero falhas** (27 pontos de matriz de acesso
+ 28 checkpoints de jornada). O que o controle de acesso faz, visto no
executar (não em tabela de design):

| Ação indevida | Barreira | Resultado real |
|---|---|---|
| GET/POST em `/api/admin/*` sem token | `permissao_necessaria` | **401** |
| Motorista tentando criar estacionamento / operar vaga no mapa / emitir sensor | role check | **403** (D5a no E2E) |
| Não-declarado reservando vaga PCD | regra RF-47 no serviço | **403 "exclusiva…"** (D3e) |
| Dispositivo com chave revogada | tabela de revogação | **401** (D6e) |
| QR de simulador já revogado | sessão de simulação | **410** (D7d) |
| Brute-force de login | rate limiter `10/min` | **429 + Retry-After** |
| Flood de cadastro | rate limiter `5/min` | **429** |

**O 429 é mecanismo funcionando, não pane.** Ele já derrubou diagnóstico
aqui: rodar `check_conexao`/smokes em loop estoura o bucket e o login do
app passa a "recusar" por 1 minuto — parece "sem conexão", é proteção.
O E2E lida com isso como cliente educado (espera `retry_after` e segue).

No frontend a mesma régua é espelhada em duas camadas: guardas de rota
(`dashboard` exige painel, `simulador*` exigem admin — e nada é renderizado
antes da validação, inclusive com cache local: sem token o cache de usuário
é descartado no boot, fechando a "sessão fantasma" pós-logout achada na
auditoria de 22/10) **e** o backend, que é a autoridade: mesmo com o
front adulterado, os códigos acima continuam valendo.
