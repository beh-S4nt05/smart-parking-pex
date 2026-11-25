# Gmail API + OAuth 2.0 — e-mails transacionais Smart Parking

## Objetivo e arquitetura

**Não precisamos pedir a senha normal do Gmail nem uma senha de app.**
O responsável pela caixa postal empresarial autoriza o **Smart Parking** uma
única vez no navegador local do Linux, usando um cliente OAuth do tipo
**Aplicativo para computador** no Google Cloud. O script obtém um
`refresh_token` com o escopo limitado `gmail.send` e guarda os segredos
no `src/.env.piloto`, com permissão `0600`.

Durante o funcionamento:

```text
Cadastro Web / APK / iOS
        | POST /auth/registrar
        v
   Backend FastAPI
        | cria OTP, armazena HMAC (10 min / 5 tentativas)
        v
   core.gmail_api
        | refresh_token --> access_token (OAuth 2.0) com cache
        | POST users/me/messages/send { raw: base64url(MIME) }
        v
     Gmail API  -- e-mail da empresa --> destinatário
        | insere código em /confirmar-email
        v
   API confirma e habilita login
```

O aplicativo do motorista jamais recebe tokens Google. A autorização OAuth
diz respeito somente ao **remetente empresarial**, não ao usuário cadastrado.

## Preparação no Google Cloud

1. No <https://console.cloud.google.com/>, crie ou selecione um projeto
   administrado pela empresa. Habilite **Gmail API** na biblioteca de APIs.
2. No **Google Auth Platform**, configure a tela de consentimento / Branding,
   Audience e Data access; escolha o público adequado. Para Gmail pessoal,
   o teste normalmente é **External**, com o e-mail do remetente em
   **Test users**. Para Workspace, o administrador pode disponibilizar
   **Internal** quando aplicável.
3. Autorize somente o escopo
   `https://www.googleapis.com/auth/gmail.send`.
4. Crie um cliente OAuth 2.0 do tipo **Desktop app / Aplicativo para computador**
   (não é preciso adicionar callback de produção). Baixe o JSON no Linux
   sob uma pasta privada.
5. Execute a autorização pelo navegador **da própria máquina**. Se o Google
   mostrar a escolha de conta, selecione a conta empresarial que realmente
   enviará as mensagens. O remetente configurado deve ser a própria conta
   ou um alias de envio autorizado previamente no Gmail.
6. O Google poderá exigir confirmação/revisão do aplicativo conforme o
   escopo e o tipo de publicação. O modo de teste serve para homologação,
   não equivale à aprovação para distribuição pública.

## Autorizar no Linux sem colar senhas nem tokens

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "httpx>=0.27"

python src/backend/piloto_autorizar_gmail.py \
  --client-json ~/Downloads/SEU_CLIENT_SECRET_OAUTH_DESKTOP.json \
  --env-file src/.env.piloto \
  --remetente EMAIL_DA_EMPRESA@gmail.com
```

O script:
- usa navegador do sistema e callback somente em `127.0.0.1`;
- usa `state` aleatório e PKCE SHA-256;
- solicita **acesso offline**, para renovar a autorização no backend;
- registra `EMAIL_PROVIDER=gmail_api` e as variáveis `GMAIL_*` no
  `src/.env.piloto` privado, sem imprimir segredos no terminal;
- mantém `SECURITY_VERIFIED_EMAIL_REQUIRED=false` até que o envio real
  esteja validado.

Não copie o JSON OAuth nem o `refresh_token` para o GitHub, para o APK,
para o frontend, para documentação pública nem para o chat.

## Backend Docker (piloto acadêmico)

O Compose recebe `EMAIL_PROVIDER=gmail_api`,
`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`,
`GMAIL_REFRESH_TOKEN` e `GMAIL_SENDER` **somente no container backend**.

```bash
docker compose --env-file src/.env.piloto \
  -f src/docker-compose.piloto.yml up -d --build backend

# Caixa autorizada para verificar o envio de verdade:
docker compose --env-file src/.env.piloto \
  -f src/docker-compose.piloto.yml exec backend \
  python piloto_testar_email.py --destino EMAIL_DE_TESTE_AUTORIZADO
```

O backend confirma apenas que a API aceitou a mensagem. Verifique caixa
de entrada, spam e endereço remetente. Após o teste, altere **somente** em
`src/.env.piloto`:

```dotenv
SECURITY_VERIFIED_EMAIL_REQUIRED=true
```

Recrie o container backend; os novos motoristas deverão confirmar seus
e-mails, enquanto usuários anteriores continuam com suas regras existentes.

## Erros frequentes

| Sintoma | Diagnóstico |
| --- | --- |
| `503 Gmail API não configurada` | OAuth JSON não autorizado ou `GMAIL_*` ausentes no backend |
| `503 Falha na autorização` | Refresh token revogado/expirado, cliente incompatível, conta mudou permissões |
| `503 Falha no envio` | Gmail API não habilitada, escopo insuficiente, remetente não autorizado, quota/limite |
| `redirect_uri_mismatch` | Cliente OAuth incorreto; use **Desktop app** |
| `access_denied` | Conta não é test user, consentimento recusado ou restrição de administrador Workspace |
| Código não chegou | Caixa de spam, erro de remetente ou Gmail aceitou mas não entregou |
| Código errado ou vencido | 6 dígitos, válido por 10 min, máximo 5 tentativas |

**Atenção:** em projetos Google OAuth *External + Testing*, o Google informa
que refresh tokens com escopos além de perfil/identidade expiram em
**7 dias**. Para uma implantação duradoura, regularize a publicação e a
verificação OAuth quando exigidas, ou use um provedor transacional adequado.
A feira desta semana não elimina essa limitação.

## Segurança

- Nunca compartilhar `client_secret` ou `refresh_token` em mensagens.
- Não montar URLs/credenciais OAuth no JavaScript público.
- Nunca usar um OAuth token de visitante; remetente é a empresa.
- `gmail.send` concede envio, não leitura de caixa postal.
- Não habilitar fallback SMTP silencioso quando `EMAIL_PROVIDER=gmail_api`.
- O envio SMTP continua **opcional**, com `EMAIL_PROVIDER=smtp`.
- Os testes automatizados usam cliente HTTP simulado; o teste real é
  separado e exige a autorização do responsável pelo e-mail.

## Documentação oficial

- <https://developers.google.com/identity/protocols/oauth2/native-app>
- <https://developers.google.com/identity/protocols/oauth2>
- <https://developers.google.com/workspace/gmail/api/guides/sending>
- <https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send>
