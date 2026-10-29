# Conectividade mobile com API local — Expo sem liberação global

Este guia vale para o backend FastAPI na porta `8000` e o frontend Expo na
`8081`. O objetivo é permitir que um aparelho na **mesma rede privada** alcance o
PC sem CORS curinga, ATS arbitrário ou cleartext Android irrestrito.

> **Limite da validação automatizada:** testes, export e prebuild não provam um
> aparelho físico. O teste no Android/iPhone real continua obrigatório antes de
> publicar. Nenhum dos procedimentos abaixo pede desativar JWT, HMAC, Trusted
> Host, rate limit ou firewall.

## 1. Entenda os quatro ambientes

| Ambiente | Como a URL é resolvida | Configuração de rede aplicável |
|---|---|---|
| **Expo Go em aparelho físico** | `EXPO_PUBLIC_API_URL_MOBILE`; sem ela, o IP publicado pelo Metro em `hostUri` | O `app.json`/plugin do projeto **não modifica o Expo Go**. O celular precisa alcançar o PC; no iPhone, permita **Rede Local** ao Expo Go |
| **Emulador/simulador** | Android Emulator: `10.0.2.2:8000`; simulador iOS: `localhost:8000`; overrides continuam tendo prioridade | O alias aponta para o computador, não para um aparelho físico. Não é evidência de teste em Android/iPhone real |
| **Development build** (`run:android`/`run:ios`) | Mesma prioridade do Expo Go | O plugin `withLocalNetwork` entra no **prebuild** e permite HTTP somente no host privado configurado. Mudou o IP? Refaça o prebuild |
| **Build de produção** | URL **HTTPS** explícita da API | Sem exceção LAN por padrão: Android bloqueia cleartext e iOS não recebe acesso arbitrário. CORS de domínio Web e Trusted Hosts são explícitos |

CORS é uma regra de **navegador**. Ele pode bloquear a Web, mas não é a causa de
um `Network Error` no Axios nativo do Expo Go/development build.

## 2. Expo Go em Android ou iPhone (caminho recomendado para desenvolvimento)

1. Suba a API normalmente. Ela escuta em `0.0.0.0:8000`; não exponha a porta no
   roteador. No firewall do PC, permita TCP `8000` **somente na sub-rede privada
   do Wi-Fi** (no Windows, use o perfil **Privado**, não Público).
2. Na raiz do repositório, execute:

   ```bash
   ./scripts/dev-front.sh
   ```

   O script detecta o IP LAN atual, grava somente
   `EXPO_PUBLIC_API_URL_MOBILE=http://IP-DO-PC:8000` no `.env` local e inicia
   `expo start -c`. A Web continua sem override e resolve o próprio host.
   Se houver várias interfaces/VPN e o IP escolhido não for o do Wi-Fi, informe
   explicitamente: `LAN_IP=192.168.1.20 ./scripts/dev-front.sh`.
3. No navegador **do celular**, abra `http://IP-DO-PC:8000/health`.
   - Se não abrir, o problema ainda é Wi-Fi/isolamento/firewall; não altere CORS.
   - Se abrir, escaneie o QR do terminal com um Expo Go compatível com SDK 58.
4. No iPhone, se o sistema solicitar acesso à rede local, toque em **Permitir**.
   Se foi negado: **Ajustes → Privacidade e Segurança → Rede Local → Expo Go**.
5. Confira no log do Metro a linha `[smart-parking] API_URL = ...`: deve ser o
   IP do PC na porta `8000`, nunca `localhost` nem a porta `8081`.

Diagnóstico no PC:

```bash
./scripts/check_conexao.sh
```

O verificador testa health, login/sessão, leituras, LAN, CORS permitido e a
rejeição de uma origem pública. O teste físico ainda deve ser feito no aparelho.

## 3. Emulador Android e simulador iOS

Sem `.env`, o resolvedor usa:

- Android Emulator: `http://10.0.2.2:8000` (alias do host);
- simulador iOS: `http://localhost:8000` (o simulador compartilha a rede do Mac).

Se for gerar um development build para emulador com exceção nativa, configure a
URL correspondente **antes do prebuild**. Para testar o caminho LAN de um
aparelho físico, não use esses aliases.

## 4. Development build em aparelho físico

O Android e o iOS compilados não herdam as exceções do Expo Go. O projeto usa
`plugins/withLocalNetwork.js` para gerar:

- Android: `base-config cleartextTrafficPermitted="false"` e uma
  `domain-config` somente para o IP/host privado de
  `EXPO_PUBLIC_API_URL_MOBILE`;
- iOS: `NSAllowsLocalNetworking=true` somente quando há host local, com
  `NSAllowsArbitraryLoads=false` e o texto da permissão de Rede Local.

Depois de trocar de Wi-Fi/IP, regenere os projetos nativos:

```bash
./scripts/dev-front.sh --no-start
cd src/frontend/smart-parking
npx expo prebuild --clean
npx expo run:android --device   # Android, com SDK/ADB configurados
# ou, num Mac:
npx expo run:ios --device       # iPhone, com Xcode configurado
npx expo start -c
```

`expo export` não gera nem instala esses projetos nativos e não substitui esse
procedimento. Se o erro for `CLEARTEXT communication not permitted`, confira se
o development build foi gerado **depois** da URL correta e do novo prebuild.

## 5. Produção fechada por padrão

Use HTTPS e gere o build sem o override HTTP da LAN:

```dotenv
EXPO_PUBLIC_API_URL_MOBILE=https://api.seudominio.com
```

Sem URL HTTP local, o prebuild gera Android sem `domain-config` e iOS sem
`NSAllowsLocalNetworking`. HTTP público é rejeitado pelo resolvedor e pelo
plugin; não existe flag para transformar isso em liberação global.

Para a Web em domínio diferente da API, configure no backend somente as origens
necessárias, por exemplo:

```dotenv
CORS_ORIGINS=["https://app.seudominio.com"]
TRUSTED_HOSTS=["api.seudominio.com"]
```

Não use `CORS_ORIGINS=["*"]`; produção recusa esse valor no boot. Same-origin
atrás do Nginx não precisa de CORS adicional. Mantenha segredos próprios, HMAC,
JWT, Trusted Host e rate limit ativos.

## 6. Diagnóstico por sintoma

| Sintoma | Próxima verificação |
|---|---|
| `http://IP-DO-PC:8000/health` não abre no celular | Mesma Wi-Fi, AP/client isolation, VPN e firewall privado. Não é CORS |
| Health abre, mas o app usa outra URL | Leia `[smart-parking] API_URL`; rode `./scripts/dev-front.sh` para atualizar IP e limpar o cache |
| Funciona no Expo Go, mas não no development build | Refaça `expo prebuild --clean` e o build nativo com a URL LAN atual |
| iOS não alcança a LAN | Permissão **Rede Local** para o Expo Go ou para o development build |
| `Failed to download remote update` | É o carregamento do bundle/Expo Go, não a API. Abra o QR do Metro e confira a compatibilidade do SDK |
| `npx expo start --tunnel` carrega o app, mas não a API | O túnel do Metro não encaminha a porta `8000`; use LAN ou uma API HTTPS alcançável |

## 7. Regressões automatizadas

```bash
cd src/backend && pytest -q
cd ../frontend/smart-parking && npm run typecheck
npm run check-native
node ../../../scripts/test_frontend_core.cjs
node ../../../scripts/test_local_network.cjs
```

O `check-native` faz dois prebuilds: um sem nenhuma exceção e outro com uma
exceção Android exclusiva para `192.168.1.44`, além de verificar o ATS do iOS.
Esses testes protegem a configuração; não substituem o teste em dispositivos.
