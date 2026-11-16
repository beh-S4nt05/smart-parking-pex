# Smart Parking — auditoria de segurança e resposta a incidentes (V1)

> **PR #65 em draft.** Nenhum merge automático. Esta é uma implementação inicial
> auditável, não uma homologação de segurança para acesso público à internet.

## Escopo implementado

- `SecurityAuditMiddleware` registra **decisões produzidas pelo backend**
  de acesso negado (401/403), login negado/limitado (401/403/429), sensores
  recusados e mutações administrativas bem-sucedidas.
- Nenhum evento armazena senha, token, query string, headers de autorização,
  IP preciso, documento oficial, corpo de requisição ou URL arbitrária.
- O banco registra apenas: categoria, método, rota normalizada, status,
  identificador do usuário quando identificável por JWT válido, shopping
  quando fornecido por uma operação de serviço verificada e horário.
- Administração global pode consultar todos os eventos em
  `GET /api/admin/seguranca/eventos` (máximo 100 por requisição).
  Gestores e financeiros só consultam suas próprias tentativas e eventos
  explicitamente associados a estacionamentos autorizados.
- Admin pode revogar sessões de uma conta por ação **explícita** com
  `POST /api/admin/seguranca/usuarios/{id}/revogar-sessoes`.
  A operação é auditada e não altera papéis, dados de reservas nem histórico.
- Migração aditiva: `f065b001a1c0`, depois de #60, #61 e #63.
  Fazer backup antes de aplicar. Rollback destrutivo não é automático.

## Segurança do desenho

1. Uma negativa de autorização é efetiva **antes** da auditoria; inserir um
   evento não transforma uma operação negada em permitida.
2. Falha no armazenamento da auditoria não derruba os usuários legítimos.
   Em vez disso, fica um erro no log do servidor para operador investigar.
3. O usuário da UI não define sua própria identidade, papel nem
   estacionamento autorizado. A leitura da auditoria aplica RBAC/escopo.
4. O acesso à auditoria deve usar HTTPS quando remoto e nunca ser público.
5. Logs antigos não são apagados automaticamente.

## Pontos não concluídos — bloqueiam aceite de segurança total

- [ ] Envio de alerta automático ao administrador por canal verificado
      (e-mail ou outro canal aprovado, não só consulta de eventos).
- [ ] Proteção contra alteração de eventos pelo operador do banco
      (exportação assinada / trilha append-only externa).
- [ ] Políticas de retenção e minimização LGPD aprovadas pelo responsável.
- [ ] Teste de negação de acesso em TODAS as rotas de recursos/tenant.
- [ ] Testes adversariais de ataque paralelo sobre sessões, sensores e
      reservas, com PostgreSQL real.
- [ ] Metadados de estacionamento em eventos gerais: a ausência de
      `estacionamento_id` significa que o evento não pode ser mostrado
      indiscriminadamente a gestores.
- [ ] Verificação de acesso não autorizado ao host Docker e observabilidade
      do piloto em Android físico, navegador e sensores.
- [ ] Rever migrações de bancos legados e validar restauração de backup.

## Critério de aceite por PR

**O CI verde é necessário, mas não suficiente.** É obrigatório confirmar que
cada ataque negativo:
- recebe 401 ou 403 conforme apropriado;
- não altera recursos não autorizados;
- gera evento de auditoria verificável, sem segredo;
- não impede acesso de um usuário legítimo ao mesmo serviço.

Quando cumprir os critérios restantes e aprovar manualmente #60 → #65,
poderá ser executada a homologação de segurança da V1.
