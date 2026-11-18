# Smart Parking V1 — Push no dispositivo e publicação sem lojas

Este guia separa **central interna**, **push no aparelho** e **publicação pública**. A central interna funciona via JWT e API; o push exige EAS/FCM/APNs e um backend que processe a fila continuamente.

## 1. O que falhava na V1

- O `app.json` não tinha um `extra.eas.projectId` atribuído. Não é seguro inventar UUID: o identificador é criado no `eas init` da conta proprietária.
- `NOTIFICACOES_PUSH_ENABLED` estava desativado por padrão; sem essa flag o worker não envia tickets.
- O cadastro do token só funciona se `NOTIFICATIONS_ENCRYPTION_KEY` for uma chave Fernet válida.
- **Expo Go no Android com SDK 58 não suporta push remoto.** Use APK nativo (preview/distribuição interna).
- Sem arquivo de configuração Firebase FCM correspondente ao identificador Android, o registro do token pode falhar. A chave FCM V1 de envio é configurada separadamente no EAS Credentials.

A tela **Notificações → Diagnóstico do push** informa flag, disponibilidade de criptografia e quantidade de dispositivos registrados da própria conta. O endpoint `GET /api/notificacoes/push/status` nunca expõe token ou segredo.

## 2. Android APK sem Play Store

No Linux, entre em `src/frontend/smart-parking/`:

```bash
npm ci
npx eas-cli@latest login
npx eas-cli@latest init
# Confirme que o EAS gravou extra.eas.projectId no app.json
npx expo config --type public
```

O identificador Android é `com.behs4nt05.smartparking`. No Firebase Console, crie um app Android com **esse mesmo package**, baixe `google-services.json` e não o versiona. Na área **Environment variables** do projeto Expo/EAS, crie uma variável **FILE/secret** chamada `GOOGLE_SERVICES_JSON` para o ambiente `preview` (e depois `production`). O `app.config.js` já a usa em `android.googleServicesFile`. Configure também as **credenciais de envio FCM V1 (service account)** via:

```bash
npx eas-cli@latest credentials --platform android
```

As credenciais para receber o token no APK e as credenciais FCM para enviar pelo Expo são etapas distintas. Não coloque essas credenciais em `EXPO_PUBLIC_*`.

Configure no ambiente **preview** do Expo:
- `EXPO_PUBLIC_API_URL_MOBILE=https://SUA_API_PUBLICA` (não `localhost` nem o QR/Metro).
- `EXPO_PUBLIC_APP_SIGNING_SECRET`: compatibilidade temporária com o validador legado do backend. **É pública em todo APK/Web e não fornece autenticação real.** O controle de acesso é feito pelo JWT e pelo backend, não por essa assinatura extra.

Depois:

```bash
npx eas-cli@latest build --platform android --profile preview
```

Abra o link do build no telefone e instale o **APK**. Não depende de publicar na Play Store. Ao iniciar, faça login e abra **Notificações → Verificar configuração**. Após o diagnóstico ficar apto, ative o switch. Teste reserva, cancelamento e recebimento **com o aplicativo em primeiro plano, fundo e fechado**.

**iOS:** distribuir binário instalável a terceiros exige os requisitos de assinatura/provisionamento da Apple, normalmente uma conta paga. Sem isso, disponibilize a versão web para Safari; isso não equivale a push nativo iOS.

Fontes oficiais:
- https://docs.expo.dev/push-notifications/push-notifications-setup/
- https://docs.expo.dev/push-notifications/fcm-credentials/
- https://docs.expo.dev/eas/environment-variables/manage/
- https://docs.expo.dev/build-reference/apk/

## 3. Backend e banco públicos para demonstração

O `render.yaml` prepara **dois serviços de demonstração** no Render: backend FastAPI e site web estático. É necessário criar a conta e autorizar o deploy no Render. Para banco persistente separado, use um PostgreSQL externo (por exemplo, Neon Free) e a URL com driver `postgresql+psycopg2://` e TLS adequado. Não habilite fallback SQLite em rede pública.

Variáveis fundamentais do backend (configurar **privadamente** no Render):
- `DATABASE_URL` — conexão real ao PostgreSQL. Nunca commitar credenciais.
- `SECRET_KEY` — segredo JWT robusto, gerado automaticamente no Blueprint.
- `APP_SIGNING_SECRET` — valor forte para o middleware legado; a cópia `EXPO_PUBLIC_APP_SIGNING_SECRET` do frontend **não é confidencial**.
- `TRUSTED_HOSTS` — JSON com domínio concreto da API, por exemplo `["smartparking-api.onrender.com"]` **somente se esse for o endereço efetivo**.
- `CORS_ORIGINS` — JSON com o endereço HTTPS real do frontend, sem `*`.
- `ENVIRONMENT=production`; `DEBUG=false`; `DB_AUTO_SQLITE=false`; `SEED_DEMO_ON_STARTUP=false`.
- `NOTIFICATIONS_ENCRYPTION_KEY` — gere com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`; não rotacione sem migrar tokens cifrados existentes.
- `NOTIFICACOES_PUSH_ENABLED=true` **depois de configurar FCM e validar a API**. `EXPO_ACCESS_TOKEN` pode ser necessário se o serviço Expo push estiver configurado com autenticação adicional.
- `SIMULADOR_BASE_URL` — endereço público do app para o QR, se o simulador for publicado.

Variáveis públicas do site Render:
- `NODE_VERSION=24.19.0`
- `EXPO_PUBLIC_API_URL_WEB=https://DOMINIO_REAL_DA_API`
- `EXPO_PUBLIC_APP_SIGNING_SECRET` — mesmo valor do backend **para compatibilidade atual**, nunca considerado proteção de identidade.

**Importante:** em `production` o projeto intencionalmente **não cria conta admin com senha padrão nem seed de demonstração**. Faça provisionamento seguro do primeiro administrador por script privado, após subir banco e migrações. Não exponha `admin123` ou outras senhas do seed publicamente.

**Limites do plano gratuito:** o Render Free pode suspender o backend após cerca de 15 minutos ocioso; enquanto suspenso o worker de push, lembretes e expiração de reservas **não roda**. Por isso este blueprint serve para **demonstração/testes**, não para alertas 24/7 ou produção com SLA. Para push contínuo use hospedagem sempre ativa (por exemplo, seu Linux local com conexão e acesso HTTPS estáveis, ou um plano cloud apropriado). Ver https://render.com/docs/free.

O banco Neon Free é adequado para pequenos testes persistentes, mas sujeito a cota e política de recursos, não substitui backup. https://neon.com/pricing

## 4. Smoke test antes da abertura pública

1. `curl -f https://DOMINIO_REAL_DA_API/api/health` deve indicar banco saudável.
2. Entre com conta de teste não privilegiada no site e faça login a partir do APK.
3. Verifique `GET /api/notificacoes/push/status` **autenticado**: `pronto=true`; nunca faça log dos tokens/segredos.
4. Ative push no Android, confirme `dispositivos_ativos >= 1`. O valor representa cadastro, **não prova entrega**.
5. Crie uma reserva real; confira entrada na central, ticket/recibo nos logs do servidor e alerta no celular. **Recibo Expo não garante exibição pelo sistema operacional.**
6. Com contas de gestor/admin/financeiro, valide o escopo de cada shopping, os relatórios financeiros e a ausência de acessos cruzados.
7. Verifique CORS, HTTPS, JWT e usuários de seed DESABILITADOS antes de compartilhar o link.

## 5. Segurança a resolver antes de tratar o deploy como produção comercial

O middleware atual usa HMAC com chave incorporada ao cliente `EXPO_PUBLIC_APP_SIGNING_SECRET`. Qualquer usuário consegue extrair esse valor do JS/APK, portanto ele **não diferencia aplicativo legítimo de script malicioso**. Não prometa integridade de cliente ou antirreplay global baseado nesse segredo. JWT, autorização por recurso no servidor e TLS são necessários, mas ainda não equivalem a uma auditoria de pentest. O simulador e demais recursos sensíveis precisam de análise específica antes de expor usuários reais.
