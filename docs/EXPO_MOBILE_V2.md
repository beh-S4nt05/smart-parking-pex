# Smart Parking — Android, iOS, Expo Go e atualizações automáticas (V2)

> Aplicação: Expo SDK 58 / React Native 0.88.1, FastAPI 8000, Metro 8081.
> A interface da V1 aprovada permanece na `main`; preparação aqui ocorre na `develop/v2`.

## 1. Erro fatal: Failed to download remote update

A mensagem do **Expo Go Android** `Uncaught Error: java.io.IOException: Failed to download remote update` significa que o cliente não baixou o pacote/manifesto de desenvolvimento ou uma atualização remota. **Não identifica por si só** falha na API FastAPI ou no banco. Verificar estes itens **na ordem**, sem apagar dados do PostgreSQL:

1. Instalar/atualizar **Expo Go oficial** pela loja do celular: <https://expo.dev/go>. O projeto usa **SDK 58**, e o cliente precisa oferecer suporte a esse SDK. O comando de Android `a` do Expo CLI já foi investigado por upstream por potencial instalação de versão incorreta (expo/expo#53391). Prefira atualizar a partir da loja.
2. Encerrar o Expo Go; no Android, limpar **cache** do Expo Go (não apagar os dados do Smart Parking). No iPhone, permitir acesso à **Rede Local** em Ajustes caso solicitado.
3. Subir a API: `./scripts/docker.sh up-nb` (caso já tenha imagem construída); se necessário, `./scripts/docker.sh up` (rebuild sem apagar volumes).
4. Na raiz do repositório: `./scripts/dev-front.sh`. O script escolhe LAN, configura `EXPO_PUBLIC_API_URL_MOBILE=http://IP_DO_PC:8000`, verifica `/health` localmente e inicia `npx expo start --clear --lan`.
5. Testar no navegador de **cada celular**:
   - `http://IP_DO_PC:8000/health` → JSON com `"status":"ok"` (API).
   - `http://IP_DO_PC:8081/status` → `packager-status:running` (Metro, se disponível).
   - Se uma ou ambas falharem, o problema é rede, firewall, AP isolation, VPN ou interface/IP incorreto. Não mexer em CORS, JWT nem no PostgreSQL.
6. Reabrir o QR **novo** do terminal Expo Go. Não reutilizar link antigo. Se o dispositivo utilizar rede celular/guest Wi-Fi, tentar Wi-Fi do PC ou configurar infraestrutura acessível por HTTPS.

Se a máquina tem diversas interfaces (Docker, VPN, Wi-Fi), fixar:
```bash
LAN_IP=192.168.1.42 ./scripts/dev-front.sh
```
Use o endereço real do **computador** mostrado por `ip -4 addr`; não copie `192.168.1.42` literalmente.

### Alternativa quando o Metro não pode ser alcançado pela LAN

```bash
./scripts/dev-front.sh --tunnel
```

O túnel encaminha o **Metro**, não a API da porta 8000. O aplicativo continuará precisando alcançar `EXPO_PUBLIC_API_URL_MOBILE`; fora do Wi-Fi local, publique a **API por HTTPS com autenticação e host confiável**, e configure essa URL manualmente, sem abrir a porta do PostgreSQL na Internet.

### Diferenciar os três sintomas

| Sintoma | Camada | Diagnóstico |
|---|---|---|
| `Failed to download remote update` **antes** da primeira tela | Expo Go / Metro / atualização | Versão do Expo Go, host/porta 8081, conectividade e cache |
| Tela abre, mas `Network Error` em login, vagas, reservas | Axios / FastAPI | URL da API 8000 no celular, firewall, TLS e token |
| Tela abre, mas alguma ação retorna `HTTP 500` | Backend | Capturar traceback de `docker compose -f src/docker-compose.yml logs -f backend` |

## 2. O que significa "atualizar automaticamente"

| Tipo de atualização | Tecnologia | Funciona quando |
|---|---|---|
| **Durante desenvolvimento**: alterações em JS/TS/estilos refletem no celular | Metro / Fast Refresh do Expo Go ou development build | Metro ligado e aparelho conectado; não precisa novo QR para cada edição |
| **Dados operacionais** (ocupação/reservas) | Busca/polling na FastAPI | API acessível; não depende de publicar novo aplicativo |
| **Depois de distribuir um aplicativo próprio**: JS e assets remotos | EAS Update | Build contém `expo-updates`, ID/configuração EAS válida, canal correspondente e Internet |
| **SDK, dependências nativas, permissões ou ícones nativos** | Novo EAS Build/distribuição | Não podem ser garantidos apenas via OTA |

O Expo Go é **ambiente de desenvolvimento**, não o cliente estável de atualizações remotas da aplicação. Para distribuição com atualização automática, usar development build/preview próprio no iOS e Android.

## 3. Preparação EAS Update para V2

Existe `src/frontend/smart-parking/eas.json` com perfis:
- `development`: dev client, canal `development`;
- `preview`: distribuição interna, canal **`v2`**;
- `production`: canal **`production`** (sem publicação automática da `main`).

Faltam **credenciais e configuração Expo específicas da sua conta**. Nenhum `projectId` foi inventado, e não há publicação OTA ativa até concluir:

```bash
cd src/frontend/smart-parking
npm ci
npx expo install expo-updates
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest update:configure
npx expo install --check
npx expo-doctor
# Commitar app.json, package.json e package-lock.json depois de validar.
# Em EAS, configurar identificadores nativos válidos para sua organização.
npx eas-cli@latest build --profile preview --platform android
# Para iOS: build/teste em iPhone exige fluxos adequados de assinatura Apple.
npx eas-cli@latest build --profile preview --platform ios
```

`eas init` associa o projeto a uma conta Expo real, gerando `extra.eas.projectId`.
`eas update:configure` configura `updates.url` e `runtimeVersion`.
Não modifique esses IDs manualmente para valores aleatórios.

**Atenção**: `EXPO_PUBLIC_*` fica visível no bundle. **Nunca** coloque senhas, JWTs, chaves HMAC ou segredos nesse prefixo. A URL do backend para a build OTA deve ser HTTPS estável, acessível dos dois sistemas, com autenticação implementada no servidor. HTTP LAN é apenas para o desenvolvimento local.

### Ativar a publicação automática após os testes

No GitHub do repositório, configure:

- **Actions Secret** `EXPO_TOKEN` — token de acesso ao Expo criado na sua conta.
- **Actions Variable** `V2_API_HTTPS_URL` — endereço **HTTPS** da API acessível ao iOS e Android, por exemplo `https://api.exemplo.com` (substitua pelo endereço real).

O job `ota-v2` de `.github/workflows/ci.yml` roda **somente após** backend, frontend e Playwright aprovados em um push à `develop/v2`. Ele verifica token, HTTPS, `expo-updates`, `projectId`, `updates.url` e `runtimeVersion`. Se faltarem requisitos, **pula a publicação com mensagem**, em vez de publicar um bundle que aponta para localhost.

Se estiver configurado, publica `eas update --branch v2 --platform all`, destinado ao canal do **build preview V2**, não à V1/produção. O aparelho baixa a atualização quando inicia (sujeito à rede/cache) e normalmente aplica após nova abertura. Para **atualizar instantaneamente enquanto o app está aberto**, precisaria implementar estratégia específica com `expo-updates`, cuidando para não interromper uma reserva ativa.

**Limite importante**: o script e o workflow não podem atualizar sozinho um app quando o Metro/Internet estiver indisponível, nem substituir builds nativos. Não faça `docker compose down -v`: isso remove o banco.

## 4. Diagnóstico rápido no Linux

```bash
# Da raiz do repo
./scripts/docker.sh status
curl -i http://localhost:8000/health
ip -4 addr show
./scripts/check_conexao.sh

# Use o IP real do Wi-Fi:
LAN_IP=192.168.1.42 ./scripts/dev-front.sh

# Em caso de erro: confira o que a CLI imprimiu.
# Abra http://IP_DO_PC:8000/health e http://IP_DO_PC:8081/status no telefone.
```

Se a API responder no PC mas não no celular, conferir firewall (TCP 8000/8081 somente em LAN), isolamento Wi-Fi, VPN e redes guest. Não expor PostgreSQL (5432) ou pgAdmin (5050) à rede pública. Em caso de conflito no SDK do Expo Go, coletar versão no aplicativo e resultado do `npx expo-doctor`.
