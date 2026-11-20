# Smart Parking V1 — piloto público por até 14 dias, custo de serviço R$ 0

**Alvo:** preservar funcionalidades existentes (FastAPI + React Native/Expo + PostgreSQL + web), notificação remota nativa no APK Android e painéis por papel. **Fora de escopo:** módulos da V2, EAS Update/OTA, Play Store, App Store e backend em Render Free com worker suspenso.

A alternativa escolhida para testes acadêmicos de duas semanas é:
- Site no **Cloudflare Pages Free** (URL *.pages.dev, sem comprar domínio).
- APK Android pelo **Expo EAS Build Free** (preview, instalação direta fora da loja).
- API FastAPI e PostgreSQL no computador Linux que já roda o projeto; só a API é exposta usando **Tailscale Funnel (HTTPS)** e o computador deve permanecer ligado e conectado.
- Push nativo da V1 usando **Expo Push Service + Firebase Cloud Messaging (FCM V1)**, com credenciais EAS e worker da API ativo.

O Funnel Personal gratuito é indicado para uso pessoal/acadêmico sujeito aos termos da Tailscale; não usar como hospedagem comercial com SLA. Se o computador desligar, API, reservas e worker pararão; web estática ainda carrega, mas não funciona online. Internet/energia locais continuam sendo necessários.

## Fase zero: comprovar que o computador suporta o piloto (somente leitura)

Antes de expor a API, na cópia do repositório que contém o PR #75:

```bash
bash scripts/piloto_preflight.sh
```

Ele identifica Docker/Compose, Node 24.19+, Tailscale, porta do FastAPI, arquivo de configuração e espaço em disco sem imprimir segredos. O comando **não inicia serviços nem abre nenhuma porta**. Avisos de Tailscale não autenticado e ausência do arquivo `.env.piloto` são esperados antes da configuração; bloqueios precisam ser corrigidos.

**Portão de aprovação:** scripts e Compose validados no CI + preflight Linux local aprovado + `GET /health` local aprovado. Só então ativar Funnel. Depois testar via 4G, Cloudflare Pages e APK/Firebase reais.

### Expiração obrigatória do piloto

Ao iniciar a disponibilidade pública (não antes), agendar imediatamente o encerramento em **14 dias de calendário** pelo systemd do Linux:

```bash
bash scripts/piloto_agendar_encerramento.sh
systemctl list-timers smartparking-piloto-expira.timer --no-pager
```

Esse script cria um temporizador `Persistent=true` em `/etc/systemd/system/`, para que o encerramento seja executado mesmo após reinicialização. Na expiração, `scripts/piloto_encerrar.sh` desliga o Tailscale Funnel e para os containers, preservando o volume do PostgreSQL. **Verifique o agendamento e o fuso horário do Linux**; o site Cloudflare Pages precisa ser despublicado manualmente ao final. Não trate apenas esse temporizador como substituto de supervisão humana.

## 1. Pré-condições antes de qualquer divulgação

1. PR #75 mesclado após CI e validação; PR #76 é independente. Sem merge, o push de V1 que estava em draft não estará na main.
2. Não reutilizar a infraestrutura de desenvolvimento com senha `admin123`, banco contendo dados pessoais reais ou `ENVIRONMENT=staging`. **O compose do piloto é novo e isolado**, com `production` e sem seed.
3. No Linux, instalar Docker/Compose, Tailscale e Node/npm compatíveis com Expo SDK 58; configurar conta gratuita Tailscale Personal para uso acadêmico. Confirmar `tailscale status`.
4. Usar a identidade `com.behs4nt05.smartparking` (Android) para o mesmo app no EAS e Firebase. Não versionar credenciais.

## 2. Obter URLs antes de compilar

- No painel Tailscale, com MagicDNS/HTTPS habilitados, identificar o nome real do computador, por exemplo `nome-do-dispositivo.tailnet.ts.net` (não é URL inventada).
- No Cloudflare Pages, criar projeto ligado ao GitHub `beh-S4nt05/smart-parking-pex`, com `main` quando PR #75 já estiver mesclado. Obter endereço real `https://SEU-PROJETO.pages.dev`.
- Configurar build Cloudflare Pages: raiz do repositório; comando:
  ```bash
  cd src/frontend/smart-parking && npm ci --no-audit --no-fund && npx expo export --platform web
  ```
  diretório de saída `src/frontend/smart-parking/dist`, variável `NODE_VERSION=24.19.0`. Colocar no painel, ANTES do build, `EXPO_PUBLIC_API_URL_WEB=https://SEU-DISPOSITIVO.tailnet.ts.net`. Verificar as rotas geradas pelo Expo; revisar fallback de navegação do Pages se uma URL acessada diretamente retornar 404.
- A URL de Funnel é pública. JWT + RBAC de verdade continuam obrigatórios. Nunca expor PostgreSQL, PgAdmin, ferramentas de manutenção ou documentação aberta.

## 3. Subir o backend local ISOLADO

Na raiz do repositório:

```bash
cp src/.env.piloto.example src/.env.piloto
openssl rand -hex 32
python3 -c 'import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
```

Edite `src/.env.piloto` localmente: senha do Postgres (somente caracteres HEX), `SECRET_KEY` e `APP_SIGNING_SECRET` gerados separadamente por `openssl rand -hex 32`, Fernet gerada pelo comando Python (32 bytes codificados em base64), host real do Funnel em `TRUSTED_HOSTS` e origem Cloudflare real em `CORS_ORIGINS`. Configure `SIMULADOR_BASE_URL` com o site Cloudflare. **Nunca envie essas chaves no chat ou GitHub.**

Se já houver FastAPI na porta 8000, encerre-o ou troque `PILOT_API_PORT` e o destino do Funnel em conjunto. Não execute o Compose padrão ao mesmo tempo se houver conflito.

```bash
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml up -d --build
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml ps
curl -fsS http://127.0.0.1:8000/health
```

O banco do piloto usa **volume próprio** e não publica portas, o backend publica somente `127.0.0.1:8000`, e nenhum PgAdmin é iniciado. `/health` é o endpoint real (não `/api/health`). A saúde do banco deve também ser validada no `docker compose ps`.

Criar conta administrativa com senha forte, sem qualquer admin padrão público:

```bash
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml exec backend python piloto_criar_admin.py
```

Use a interface da V1 para criar gestores/financeiros de teste, vinculando cada usuário ao estacionamento autorizado e criando senhas próprias.

### Popular somente shoppings/vagas simuladas, sem contas demo (recomendado para a banca)

Em um **banco de piloto vazio**, carregue os oito shoppings reais de Manaus (endereços corrigidos), com andares e vagas **fictícias**, sem executar `seed_demo.py` e sem criar nenhuma senha padrão:

```bash
# Inspecionar o que seria criado, SEM gravar:
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
  exec backend python piloto_popular_shoppings.py

# Se a lista estiver correta, autorizar explicitamente:
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
  exec backend python piloto_popular_shoppings.py --apply
```

A importação é **opcional, idempotente e só funciona se o banco ainda não tiver estacionamentos**. Não apaga reservas, não altera cadastros existentes e não cria administradores/gestores/financeiros/motoristas. As capacidades, ocupações, preços e disponibilidade são **dados de demonstração**, não sensores reais nem dados oficiais dos shoppings. Os empreendimentos citados são referências geográficas acadêmicas, **não parcerias comerciais confirmadas**. Não apresentar esses números como disponibilidade real dos estacionamentos.

Para bancos existentes com o seed antigo e endereços incorretos, faça backup e consulte `src/docs/ROTAS_GOOGLE_MAPS_MANAUS.md`; há uma migração **opt-in** separada.



Depois de confirmar que o backend está em `production` e protegido, habilite o endereço público via Tailscale:

```bash
sudo tailscale funnel --bg http://127.0.0.1:8000
tailscale funnel status
curl -fsS https://SEU-DISPOSITIVO.tailnet.ts.net/health
```

Confira `TRUSTED_HOSTS` com o host exato do Funnel, CORS com o site Cloudflare, HTTPS válido e login real **de outro Wi-Fi/4G**.

## 4. Gerar APK V1 com push real

Na pasta `src/frontend/smart-parking`:

```bash
npm ci
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest credentials --platform android
npx eas-cli@latest build --platform android --profile preview
```

O comando `eas init` precisa gravar o `extra.eas.projectId` verdadeiro no app config. No Firebase Console, criar o aplicativo Android `com.behs4nt05.smartparking`, provisionar `google-services.json` e chave FCM V1 de service account. A variável **EAS FILE** `GOOGLE_SERVICES_JSON` (ambiente `preview`) fornece o arquivo ao `app.config.js` sem salvar credenciais no Git. Configurar `EXPO_PUBLIC_API_URL_MOBILE` para HTTPS do mesmo Funnel no EAS `preview`.

`EXPO_PUBLIC_APP_SIGNING_SECRET` deve ser compatível com o middleware atual em production, mas **é pública dentro do APK e do JS e não autentica usuários**. O controle de segurança real permanece no JWT/RBAC do FastAPI.

Somente após credenciais FCM, APK e backend funcionando, altere `NOTIFICACOES_PUSH_ENABLED=true` no arquivo privado do piloto e recrie somente o backend:

```bash
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml up -d backend
```

No APK, faça login, abra Notificações e confirme diagnóstico apto. Ative push voluntariamente. Teste reserva/criação/cancelamento/expiração com outro aparelho, no primeiro plano, segundo plano e com app encerrado, e verifique tickets **e** recibos da fila Expo. O teste CI Android/TypeScript/Web não substitui o teste físico FCM.

## 5. Validação antes de distribuir o link

- Testar via **4G** em vez do Wi-Fi local, web e APK apontando para a mesma API.
- Não haver `admin123` ou usuários com senha demo; MFA e autorização por shopping não podem ser contornados.
- Motorista nunca lê reserva de outro usuário; gestor só enxerga os shoppings vinculados; financeiro só o próprio.
- Fazer reserva/cancelamento e observar atualização no painel sem refresh manual e a central persistente.
- Confirmar que push de reserva chega no Android com o app em 1º plano, fundo e encerrado. Histórico financeiro e dados de checkout não aparecem em notificações públicas.
- Confirmar que `postgres:5432` e PgAdmin **não** são publicamente acessíveis.
- Registrar data/hora de início e **data/hora limite 14 dias depois**; não compartilhar links antes do checklist.

## 6. Desligamento após no máximo 14 dias

Não basta parar o frontend: é preciso **remover a exposição da API** no Tailscale Funnel e despublicar o Cloudflare Pages ao final do piloto. Também retire o link do APK. No Linux:

```bash
sudo tailscale funnel --https=443 off
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml stop
```

`stop` preserva o volume para eventual relatório/backup. **Não execute `down -v` sem backup e autorização**, pois apaga os dados. Se quiser encerrar sem risco de esquecer, programe uma tarefa local persistente de desativação do Funnel para o horário de término e deixe uma segunda verificação manual para Cloudflare Pages. A configuração desse timer precisa ser revisada na máquina real (inclusive após reinícios). Tailscale `funnel off` não elimina os arquivos locais.

## 7. Alternativa totalmente cloud, com limitação importante

Cloudflare Pages + Render Free (API) + Neon Free (Postgres) + EAS Free + Firebase FCM custam R$ 0 dentro das cotas, mas **Render Free suspende a API após 15 minutos sem tráfego**. Worker, lembretes e expiração de reserva não rodam enquanto dorme. Para mostrar a interface em uma apresentação curta é possível; para testar push de maneira confiável durante 14 dias, prefira o Linux local com Tailscale Funnel.

## Referências oficiais

- https://tailscale.com/docs/features/tailscale-funnel
- https://tailscale.com/docs/use-cases/application-testing/share-local-dev-server-with-internet
- https://developers.cloudflare.com/pages/get-started/git-integration/
- https://expo.dev/pricing
- https://docs.expo.dev/build-reference/apk/
- https://docs.expo.dev/push-notifications/fcm-credentials/
- https://firebase.google.com/products/cloud-messaging
- https://render.com/docs/free
