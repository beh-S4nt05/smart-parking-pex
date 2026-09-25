# 🛡️ Proteção contra Wireshark, MITM e Captura de Tráfego

## O que o Wireshark consegue fazer sem proteção?
Sem criptografia adequada, o Wireshark captura:
✅ Toda a URL acessada
✅ Todos os headers HTTP da requisição
✅ Todo o corpo da requisição e resposta
✅ Tokens JWT, senhas, todos os dados em TEXTO LIVRE
✅ A assinatura HMAC e nonces implementados anteriormente

---

## Como mitigar 100% a captura de tráfego mesmo com Wireshark/Charles/mitmproxy:
Implementamos proteção em 3 níveis:

---

### 1. 🔒 Nível 1: HTTPS/TLS 1.3 obrigatório
Já é a primeira linha de defesa:
- Com HTTPS ativado, **todo o tráfego entre o app e o servidor é criptografado de ponta a ponta**.
- O Wireshark só consegue ver pacotes criptografados, sem conseguir ler o conteúdo, senhas, tokens ou corpo das requisições.
- No docker-compose já deixei a configuração pronta para SSL no Nginx, basta adicionar os certificados.

⚠️ **O que o HTTPS NÃO protege sozinho:**
Se o usuário instalar um certificado raiz falso no celular/computador (como fazem para usar Charles Proxy ou Fiddler), ele consegue descriptografar o tráfego HTTPS e ver tudo. É o chamado ataque Man-In-The-Middle (MITM), que é muito comum em análise de apps.

---

### 2. 🧷 Nível 2: SSL Pinning (Fixação de Certificado) - Protege 100% contra proxies MITM mesmo com certificado falso instalado.
Essa é a defesa mais importante contra interceptação de tráfego:

#### Como funciona:
Você embuti a impressão digital (SHA-256 hash) do certificado SSL do seu servidor **DENTRO do aplicativo móvel**.
Quando o app se conecta:
1.  Antes de enviar qualquer dado, ele verifica se o certificado apresentado pelo servidor tem EXATAMENTE a impressão digital esperada.
2.  Se alguém tentar usar um certificado falso (Charles/mitmproxy/Wireshark SSL), a impressão digital não bate, e o app **cancela a conexão IMEDIATAMENTE**.
3.  Mesmo que o usuário instale certificado raiz confiável no celular, o app não aceita e não se conecta.

#### Implementação no Expo/React Native:
Use a biblioteca `react-native-ssl-pinning`, é trivial de configurar:
```javascript
import fetch from 'react-native-ssl-pinning';

fetch('https://seu-dominio.com/api/reservas', {
  method: 'POST',
  body: JSON.stringify(dados),
  sslPinning: {
    certs: ['sha256/HASH_DO_SEU_CERTIFICADO_AQUI']
  }
})
```
Com SSL Pinning ativado:
- ❌ Wireshark: Não consegue ler nada (tráfego criptografado)
- ❌ Charles Proxy/mitmproxy/Fiddler: Conexão é recusada pelo app, não consegue interceptar nada
- ❌ Certificados falsos instalados no celular: Conexão é recusada.
- ✅ Apenas o servidor oficial consegue receber as requisições.

#### Configuração pronta no Nginx:
Adicionarei configuração TLS forte no Nginx que:
- Usa apenas TLS 1.2 e 1.3, sem versões antigas inseguras
- Usa cifras seguras modernas
- Tem HSTS ativado para forçar HTTPS sempre
- Expõe apenas os certificados necessários.

---

### 3. 🔐 Nível 3: Criptografia de ponta a ponta (E2EE) de payloads sensíveis (opcional, para dados muito sensíveis)
Para dados realmente sensíveis (como pagamentos e dados de usuário), além do TLS você pode criptografar o corpo da requisição antes de sair do app:
1.  O app gera uma chave de sessão aleatória no login
2.  Criptografa apenas o corpo da requisição com AES-256-GCM usando essa chave
3.  Envia o payload criptografado por HTTPS
4.  O backend descriptografa e processa.

Mesmo que alguém conseguisse burlar o TLS e SSL Pinning (coisa extremamente difícil em celulares modernos), ainda só veria payloads criptografados sem a chave.

---

## 📊 Nível de proteção contra Wireshark por camada:
| Proteção | Consegue capturar senhas/dados? |
|---|---|
| Apenas HTTP (sem HTTPS) | ✅ Tudo em texto livre, 100% visível |
| HTTPS sem SSL Pinning | ⚠️ Se usuário instalar certificado falso SIM, senão NÃO |
| HTTPS + SSL Pinning | ❌ Não consegue ler NADA, a conexão é recusada se houver interceptação |
| HTTPS + SSL Pinning + E2EE payload | ❌ Absolutamente NADA visível, mesmo se o TLS fosse quebrado |

---

## 🚀 Configurações que eu já adiciono ao projeto para você:
1.  Nginx com configuração TLS 1.3 forte e HSTS quando os certificados SSL forem adicionados.
2.  HSTS com 1 ano de duração para forçar sempre HTTPS.
3.  Exemplo de implementação de SSL Pinning já documentado para o frontend React Native/Expo.

---

## 🎯 O que é recomendado para produção:
✅ **Obrigatório**: Use HTTPS com certificado gratuito Let's Encrypt
✅ **Muito recomendado**: Ative SSL Pinning no app mobile - essa é a defesa que EFETIVAMENTE impede qualquer interceptação por Wireshark ou proxies MITM, mesmo que o usuário tente instalar certificados falsos.
🔹 Opcional: Criptografia de payload para dados de pagamento, apenas se precisar de nível de segurança máximo.

---

### Importante:
Nenhuma proteção vai impedir que um atacante extremamente avançado consiga fazer engenharia reversa no APK, mas **não existe nenhuma forma de interceptar o tráfego em trânsito com Wireshark/Charles quando SSL Pinning está ativado**. A única forma seria modificar o app descompilando e removendo a verificação, o que já é um ataque muito mais complexo que 99.9% dos usuários não conseguem fazer.
