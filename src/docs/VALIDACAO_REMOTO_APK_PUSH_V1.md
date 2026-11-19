# Validação cruzada — acesso remoto, APK e notificações push (Smart Parking V1)

Data da auditoria: 18/11/2026. Referências de código: `main` após PR #74, `develop/v2` e correções propostas no PR #75. **Não confundir teste de integração com demonstração em aparelho físico.**

## 1. Sistemas existentes e compatibilidade

| Elemento | Evidência no repositório | Conclusão |
|---|---|---|
| API/DB local | `src/docker-compose.yml`; `src/backend/main.py`; `src/run-dev.sh` | Implementados. Nginx local em 8080, FastAPI em 8000, PostgreSQL em 5432; não há TLS público configurado |
| Inicialização celular na LAN | `scripts/dev-front.sh`, `src/frontend/smart-parking/src/services/apiBaseUrl.ts` | Implementada. `--tunnel` encaminha só o Metro, não o backend na porta 8000 |
| Segurança por papéis | `src/backend/core/deps.py`, `core/escopo.py`, `api/admin.py` | JWT/RBAC no servidor. Gestor limitado aos shoppings vinculados; financeiro ao próprio |
| APK EAS/OTA da V2 | `develop/v2/eas.json` | Possui perfis development/preview/production e preview no canal **v2**; **não é** build V1 comprovado nem OTA operacional |
| Push do motorista | `src/app/notificacoes.tsx`, `services/pushNotificacoes.ts`, `api/notificacoes.py`, `rules/notificacoes_worker.py` | Opt-in → permissão SO → Expo token → cadastro JWT com Fernet → evento → fila → Expo ticket/receipt |
| Avisos de gestor/admin | `rules/notificacoes_service.py` e PR #74 | Internos à central do app/painel, por escopo; **não** vão ao push remoto por padrão |
| Diagnóstico do push | PR #75 | Detecta flag do servidor, Fernet, quantidade de tokens por conta e build sem EAS/Expo Go; não confirma credenciais FCM nem entrega SO |
| API pública HTTPS, banco externo, APK distribuído, credenciais FCM | Integrações externas | **Sem evidência de configuração ativa em contas externas, nem de teste físico de entrega** |

## 2. Fluxo único sem duplicar o backend

```text
APK Android instalado (build EAS preview; sem Play Store)
  ├─ UI React Native/Expo Router: login, reservas, notificações e painel
  ├─ Axios / JWT em SecureStore (escopo verificado pelo FastAPI)
  ├─ EXPO_PUBLIC_API_URL_MOBILE=https://API-PUBLICA-REAL (precisa estar no build)
  │   └─ API FastAPI (uma só) → PostgreSQL persistente
  │        ├─ reserva/cancelamento → transação → notificação interna ao motorista
  │        ├─ mesmo evento → central interna admin/gestor do shopping autorizado
  │        └─ outbox push → worker ativo → Expo Push Service → FCM → Android
  └─ EAS projectId + google-services.json + FCM V1 + permissão Android
          └─ ExpoPushToken → POST /api/notificacoes/dispositivos (JWT)
```

- O **túnel Metro/Expo Go não substitui URL HTTPS da API**.
- A web prevista anteriormente permanece **Cloudflare Pages**; API em **Render**; DB em **Neon**, todos dependentes de configuração real. `render.yaml` só descreve a API. A arquitetura pode usar um backend local acessível por um gateway seguro, mas **não existe no repositório um túnel/VPN público configurado**.
- Render Free entra em suspensão na inatividade; **não é solução confiável de push 24/7**. Registrar token e receber evento em um request não resolve lembretes agendados enquanto o worker está dormindo.
- O build **V1** não deve apontar OTA ao canal `v2`; a estrutura EAS Update da V2 não deve ser mesclada indiscriminadamente. Na `main` V1 não há `expo-updates` integrado, portanto EAS Update não foi validado.
- O EAS projectId **não pode ser inventado**. Obter em `eas init` da conta legítima e gerar novo APK para mudanças nativas.
- A assinatura HMAC com `EXPO_PUBLIC_APP_SIGNING_SECRET` é extraível dos clientes. Autorização real continua no FastAPI (JWT/RBAC), não na assinatura pública.

## 3. Matriz de mensagens da V1

| Evento | Central do motorista | Push dispositivo opt-in | Central do gestor/admin |
|---|---:|---:|---:|
| Reserva criada/confirmada | Sim | Sim | Sim, shopping autorizado |
| Reserva cancelada | Sim | Sim | Sim, shopping autorizado |
| Reserva expirada | Sim | Sim | Sim, shopping autorizado |
| Check-in/conclusão | Sim | Não, por padrão | Sim, shopping autorizado |
| Lembrete de reserva | Sim | Sim | Não |
| Vaga disponível acompanhada | Sim | Sim | Não |
| Pagamento confirmado | Sim (se preferência permite) | Sim (opt-in) | Eventos de atividade, não push gerencial |
| Fechamento/resumo financeiro | Financeiro/admin autorizado | Não | Central interna de financeiro/admin |

O envio push pode falhar mesmo após ticket aceito; verificar recibo Expo e exibição no Android é indispensável.

## 4. Portões para considerar válido

**Automatizados**: CI backend 3.10/3.12; TypeScript/Expo; export Hermes Android/iOS; CNG prebuild; Playwright Chromium usando API de QA. Ver PR #75 e execução de Actions pelo SHA do head.

**Faltam testes externos reais antes de publicar:**
1. Criar/configurar projeto EAS verdadeiro, registrar Android `com.behs4nt05.smartparking` no Firebase, credenciais FCM V1 e arquivo de cliente privado do EAS.
2. Configurar backend HTTPS acessível ao celular de outra rede, banco PostgreSQL persistente, JWT/CORS e migrações. Testar login e reserva sem Expo Go nem computador na mesma LAN.
3. Gerar e instalar **APK de preview assinado**, confirmar `EAS projectId`, permissões Android e cadastro de dispositivo. Nada disso é substituído pelo export Hermes/prebuild em CI.
4. Em dois aparelhos/contas, testar eventos, escopo de gestor/admin, estado de app primeiro plano/fundo/encerrado, logout, troca de conta e reativação do push.
5. Registrar ticket e recibo do Expo, falhas de FCM/DeviceNotRegistered, expiração e reconexão. Não dizer que um recibo comprova apresentação visual.
6. Verificar confiabilidade do worker de 15 segundos enquanto servidor está inativo/reiniciando. Não aprovar SLA 24/7 sobre Render Free.

### Resultado da validação

**Código e caminhos de integração: presentes; CI de software: verificável; acesso remoto publicado / instalação APK / push físico: não comprovados.** Manter PR #75 separado das melhorias de painel (#76) e não mesclar trabalho da V2.
