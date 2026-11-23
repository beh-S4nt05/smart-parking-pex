# Smart Parking V1 — instalacao Android e iPhone (piloto publico)

## Estado do piloto

- Web: Cloudflare Pages, app Expo Web SPA responsivo.
- API: FastAPI/PostgreSQL no Linux, HTTPS pelo Tailscale Funnel.
- Web: navegação e layout adaptados ao tamanho da tela, incluindo celulares.
- Android APK e iOS IPA/TestFlight: precisam de builds assinados e testes
  físicos; publicação do Pages **não** produz APK/IPA.
- Os shoppings são reais como referências geográficas, mas **vagas, ocupação,
  quantidade por andar e tarifas são simuladas** (piloto acadêmico).
- Para atualizar o backend no Linux, atualizar a branch após aprovação do PR
  e recriar SOMENTE o backend com os DOIS Compose (base e local), preservando
  o bind mount do banco. Nunca `down -v`. Faça backup antes.

## iPhone — instalacao agora, sem conta Apple (Web App)

1. Abra o endereço HTTPS verdadeiro do projeto `*.pages.dev` no **Safari**.
2. Toque em **Compartilhar > Adicionar à Tela de Início**.
3. Quando o iOS apresentar **Abrir como App**, mantenha-o habilitado.
4. Confirme **Adicionar** e abra o ícone Smart Parking na tela inicial.

O build `npm run build:web:piloto` publica agora o manifesto, a identidade
visual e `display: standalone`, com ícone/título Apple. Assim o iPhone mantém
a **interface mobile responsiva**, não passa a executar React Native nativo.
O comportamento de câmera, notificações, cache offline e APIs do sistema
segue as limitações do Safari/WebKit.

**Web Push no iPhone NÃO está implementado só com o manifesto.** Exige Service
Worker, Push API, consentimento do usuário e infraestrutura de Web Push, a ser
testada em aparelhos compatíveis. A implementação nativa atual é outra,
baseada em expo-notifications/Expo Push Service.

Referência Apple: https://support.apple.com/guide/iphone/turn-a-website-into-an-app-iph42ab2f3a7/ios

## Android — aplicativo React Native nativo (APK)

O perfil `preview` em `src/frontend/smart-parking/eas.json` já tem:
`distribution: internal`, `android.buildType: apk`.

**Antes do primeiro build:**

- faça login na conta Expo/EAS e vincule o projeto real (`eas init`);
- configure no EAS ambiente `preview`:
  `EXPO_PUBLIC_API_URL_MOBILE=https://HOST-HTTPS-REAL.ts.net`;
- para push nativo, configure Firebase do Android
  `com.behs4nt05.smartparking`, as credenciais FCM V1 do projeto EAS e
  `GOOGLE_SERVICES_JSON` como variável EAS do tipo **FILE**;
- não copie `SECRET_KEY`, `APP_SIGNING_SECRET`, senha do Postgres ou
  `NOTIFICATIONS_ENCRYPTION_KEY` para `EXPO_PUBLIC_*`.

```bash
cd src/frontend/smart-parking
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest build --platform android --profile preview
```

Quando EAS concluir, compartilhe SOMENTE o link oficial do APK gerado.
Validar instalação real (Android fora da LAN), login, reserva/cancelamento,
mapa, navegação, permissões e notificações antes de liberar aos usuários.

## iPhone — aplicativo React Native realmente nativo (IPA)

O código contém `ios.bundleIdentifier: com.behs4nt05.smartparking`.
**EAS Build pode compilar em nuvem mesmo trabalhando no Linux**, mas para
instalar/distribuir em iPhone físico são necessários Apple Developer Program,
assinatura/certificados, provisioning e/ou App Store Connect.

Opção A (teste restrito): cadastrar aparelhos de teste (UDID/ad hoc) e
usar o perfil `preview` (`distribution: internal`). Necessita equipe Apple
habilitada e provisionamento para os dispositivos.

```bash
cd src/frontend/smart-parking
npx eas-cli@latest build --platform ios --profile preview
```

Opção B (grupo de testadores): criar o app no App Store Connect, gerar
build `production` (`distribution: store`) e submeter ao TestFlight.
A aprovação externa da Apple pode ser necessária conforme a modalidade.

```bash
npx eas-cli@latest build --platform ios --profile production
npx eas-cli@latest submit --platform ios --latest
```

Sem conta Apple/credenciais de assinatura, oferecer a Web App na tela
inicial é a alternativa imediata, mas **não equivale a um IPA nativo**.

Documentação Expo:
- https://docs.expo.dev/build/internal-distribution/
- https://docs.expo.dev/submit/testflight/
- https://docs.expo.dev/app-signing/apple-developer-program-roles-and-permissions/

## Segurança e testes antes de liberar usuários

Na V1 corrigida, o bundle não carrega `APP_SIGNING_SECRET`: a assinatura
HMAC compartilhada não autenticava o cliente, pois poderia ser extraída do
APK, IPA ou JavaScript. O backend continua exigindo JWT, sessões válidas,
RBAC, escopo por shopping, rate limit e `X-Device-Key` para IoT.

No Compose piloto corrigido, `REQUIRE_CLIENT_HMAC=false`; instalações
legadas podem optar pelo mecanismo antigo, sabendo de suas limitações.
A aplicação antiga (antes de atualizar o backend do Linux) continua com
o requisito antigo: publique Web/Android/iOS **somente depois de atualizar
o servidor e validar que operações autenticadas funcionam**.

**Matriz mínima de aceitação:** GET listagem com oito shoppings; soma de
`andares[*].vagas_livres` igual a `vagas_disponiveis_total`; login com
conta de teste; leitura de painel por cargo; criação/cancelamento de reserva
em conta de teste; API sem token dá 401 e papel incorreto dá 403; Android
APK físico e iOS Safari/PWA físico; push Android e iOS nativo dependem de
credenciais, permissão e confirmação de entrega real.

O usuário optou pelo encerramento MANUAL do piloto: quando for encerrar,
remover a exposição do Funnel, parar os containers com `stop` (não apagar
volumes), despublicar o Pages e retirar links de instalação. Não assumir
que desabilitar uma só camada encerra todas.
