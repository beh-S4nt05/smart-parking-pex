# Smart Parking — Notificações Inteligentes da V1

**Reentrega corretiva após PR #70 (mesclado incompleto) e PR #71 (reversão segura).**
Implementação em PR Draft separado. **Não faz parte do escopo V2.**

## Comportamento

- **Central interna**: `/notificacoes` com leitura, histórico e preferências por usuário
- **Reservas**: confirmação, cancelamento, expiração e check-in somente após transação real
- **Lembrete**: quando uma reserva confirmada estiver a até 15 minutos do vencimento
- **Vagas**: acompanhamento explícito de vagas comuns, com estabilização de 10s,
  máximo de 3 mensagens por usuário/dia e intervalo mínimo de 30 minutos
- **Financeiro**: pagamento confirmado, caixa fechado, resumo do dia anterior
  às 07h de Manaus, apenas para financeiro do estacionamento e administrador
- **Antispam**: idempotência no banco por chave única + suspensão da entrega se
  a reserva terminar, a vaga ocupar, a preferência mudar ou o dispositivo for desativado
- **Push**: desligado por padrão; opt-in do usuário e credenciais do build são
  obrigatórios. O armazenamento interno funciona mesmo sem push.

## Segurança e infraestrutura

As notificações são geradas na **mesma transação** do evento operacional,
enquanto a entrega externa é feita por uma outbox persistente. O worker roda
fora da requisição do usuário e pode repetir o envio em caso de falha.

Novas tabelas (revisão Alembic `f065b001a1c0`):

- `notificacoes`
- `preferencias_notificacao`
- `dispositivos_notificacao`
- `acompanhamentos_vagas`
- `entregas_notificacao`

A API restringe todas as leituras ao proprietário do JWT; usuários do financeiro
somente recebem avisos do estacionamento ao qual estão vinculados. O usuário
não escolhe o destinatário de notificações.

O token Expo é **cifrado em repouso** com uma chave Fernet exclusiva do servidor,
nunca derivada do segredo HMAC compartilhado com clientes. Não registrar tokens
em logs nem enviar dados financeiros detalhados no payload push.

### Variáveis do backend

```bash
# PRIVADA: gerar uma chave, guardar exclusivamente no backend e nunca
# publicar em EXPO_PUBLIC_* ou repositório.
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# Colocar no .env local/segredo de produção:
NOTIFICATIONS_ENCRYPTION_KEY=<Fernet-key-base64-gerada-acima>
NOTIFICACOES_PUSH_ENABLED=false
# Ativar somente após certificados, projectId e builds próprios configurados:
# NOTIFICACOES_PUSH_ENABLED=true
# EXPO_ACCESS_TOKEN=<segredo-do-servidor>
```

**Aviso:** alterar a chave Fernet invalida tokens de dispositivos já cadastrados;
planejar rotação e novo registro de dispositivos. O serviço de push não envia
nada com a flag `false`.

## Configuração nativa — Expo SDK 58

`expo-notifications` e seu plugin estão declarados. Para push remoto:

1. Configurar projeto EAS real com `npx eas-cli@latest init` e
   `extra.eas.projectId` no `app.json` (valor obtido de conta Expo válida).
2. Definir `android.package` e `ios.bundleIdentifier` próprios.
3. Configurar FCM v1 no Android e APNs no iOS com credenciais reais.
4. Produzir e instalar **development builds**; Expo Go Android não suporta
   push remoto nesse SDK.
5. Conceder permissão no aparelho e ativar push na página `/notificacoes`.
6. Conferir no servidor tickets e recibos do Expo Push Service.

**Os push tokens só podem ser obtidos após configuração nativa/EAS.** Não
inventar identificadores de projeto, certificados, chaves ou tokens.

O Expo Push Service aceita mensagens mas não garante que o sistema operacional
as apresente na tela, especialmente em economia de bateria/offline.

## Foco nas operações da V1

Notificações não substituem o status real das vagas, relatórios financeiros ou
histórico de reservas. O usuário deve revalidar a vaga ao abrir o mapa; um
aviso de vaga disponível não cria nem garante uma reserva.

O polling do mapa em 1.500 ms não aciona envio push em cada atualização.
O backend cria notificações a partir de transições reais, não de consultas.

## Testes e critérios de merge

Antes do merge:
- `ruff check .`, `pytest tests -q` em Python 3.10/3.12;
- `npm ci`, `npm run typecheck`, Expo Doctor, SDK check e Playwright;
- testes de isolamento (usuário A não lê alertas de B, financeiro não recebe
  alertas de outro shopping);
- reserva -> cancelamento -> atualização de central; lembrete idempotente;
- disponibilidade condicionada ao sensor e cooldown;
- validação em PostgreSQL existente com backup e sem `docker compose down -v`;
- testes reais de push em builds Android e iOS antes da ativação produtiva.

### Limitações deliberadas

Não há garantia de entrega push em tempo exato. A camada de recibos e tentativas
não transforma uma notificação em operação financeira ou reserva. A funcionalidade
remota permanece sob feature flag, enquanto a central interna pode ser
implantada independentemente após aprovações de CI e segurança.

## Histórico de incidentes

- PR #70: integração prematura do módulo backend sem todas as camadas.
- PR #71: reversão mesclada depois do CI verde para preservar V1 estável.
- PR #72: implementação completa em branch própria e Draft, sujeita a CI.
