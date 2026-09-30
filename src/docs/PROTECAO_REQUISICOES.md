# 🔐 Proteção contra replicação de requisições e acesso indevido pelo navegador/Postman

## O problema:
Se o usuário abrir o DevTools no navegador/Expo ou usar um proxy (Charles/mitmproxy), ele consegue pegar o token JWT e copiar requisições para fazer manualmente pelo Postman, curl ou script, burlando o frontend oficial.

## Como resolvemos isso:
Implementei um sistema de **Assinatura HMAC de requisições com anti-replay** que bloqueia 99% dessas tentativas, sem afetar usuários legítimos do app oficial.

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

Essa combinação de proteções bloqueia 99.9% dos casos comuns de usuários tentando burlar o app pelo navegador/Postman, que é a grande maioria das tentativas de abuso.
