# Smart Parking — gerar APK e publicar via TestFlight (2026)

Este guia usa o Expo EAS para gerar arquivos NATIVOS assinados. Não há
APK/IPA gerados apenas por adicionar a configuração ao GitHub.

## Pré-requisitos obrigatórios

- Node 24.19+, npm 11.17, conta Expo/EAS autorizada e projeto vinculado (eas init).
- HTTPS público REAL da API FastAPI: deve responder GET /health status=ok
  também em 4G, e o host do Linux/Tailscale Funnel precisa estar ligado.
- Apple Developer Program e App Store Connect com app
  com.behs4nt05.smartparking para o fluxo iOS/TestFlight.
- Credenciais de assinatura nativa do Android/iOS no EAS.
- Código do repositório com CI aprovada. Não usar localhost, Expo Metro
  :8081 nem IP da rede local no build de distribuição.

## Build manual no Linux do responsável (primeira execução)

Na raiz da pasta smart-parking-pex:

~~~bash
git pull --ff-only origin main
export EXPO_PUBLIC_API_URL_MOBILE="https://SEU-HOST-REAL.tailnet.ts.net"

node scripts/mobile_release_preflight.cjs --check-api

cd src/frontend/smart-parking
npx eas-cli@latest login
npx eas-cli@latest init
cd ../../..

# APK Android instalável em aparelho físico:
bash scripts/gerar_apps_mobile.sh android

# IPA iOS assinado e envio para TestFlight:
bash scripts/gerar_apps_mobile.sh ios

# Ou as duas plataformas:
bash scripts/gerar_apps_mobile.sh ambos
~~~

Substitua SEU-HOST-REAL pelo URL público que realmente aponta para a API.
O comando de build configura EXPO_PUBLIC_API_URL_MOBILE no ambiente EAS
preview para Android e production para iOS. Não adicione nenhuma senha
ou chave de servidor no EXPO_PUBLIC_*: essas variáveis ficam dentro do app.

O primeiro EAS Build pode solicitar a geração da assinatura Android;
preserve a chave para futuras atualizações. No iOS será necessário vincular
o time Apple, certificados e provisionamento ao EAS.

## Publicação via GitHub Actions

Arquivo .github/workflows/mobile-release-eas.yml

1. No Expo, crie um access token para a conta proprietária e salve SOMENTE
   como secret EXPO_TOKEN em GitHub > Settings > Secrets and variables > Actions.
2. Informe o UUID REAL do projeto EAS como repository variable
   EXPO_EAS_PROJECT_ID no mesmo painel (não é segredo).
3. Prepare credenciais de assinatura Android/iOS no EAS e App Store Connect.
4. Em GitHub > Actions > Publicar Mobile (APK e TestFlight) > Run workflow,
   escolha Android, iOS ou ambos e informe a API HTTPS pública no campo api_url.
5. Abra o build do Expo nos logs e baixe o APK do link verdadeiro do EAS.
   O iOS usa --auto-submit para enviar o IPA para processamento no TestFlight.

O workflow manual NÃO publica na Google Play nem coloca o iOS na App Store.
O TestFlight pode exigir revisão beta da Apple e definição de grupos de teste.

## Matriz de aceitação em aparelhos reais

Android e iPhone: instalar e abrir sem Expo Go; ícones visíveis; câmera/QR,
cadastro, confirmação de e-mail, login/logout, mapa e vagas, reserva,
cancelamento, roles e rede externa via HTTPS. Push requer configuração
adicional FCM V1 (Android) e APNs (iOS), não deve ser declarado como validado
sem testes de recebimento. Vagas e tarifas continuam simuladas no piloto.

## Quando bloquear a entrega

- API/health fora do ar no HTTPS público, ou apontando para localhost.
- Expo projectId ainda não vinculado.
- Sem credenciais Android EAS ou Apple Developer/App Store Connect.
- CI falha ou teste funcional falha num aparelho físico.
- App de TestFlight em processamento ou ainda não liberado para testadores.

Referências oficiais:
https://docs.expo.dev/build-reference/apk/
https://docs.expo.dev/eas/environment-variables/
https://docs.expo.dev/submit/testflight/
