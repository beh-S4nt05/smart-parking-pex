# 💰 Módulo de Pagamentos e Faturamento - SmartParking
Documentação completa do sistema de cobrança, pagamento e fechamento de caixa.

---

## 🔄 Fluxo completo de pagamento
O fluxo é 100% automatizado desde a entrada do veículo até a saída:

```
1. Veículo entra na vaga → Sensor atualiza vaga para OCUPADA → Registro de entrada criado automaticamente
2. Veículo sai da vaga → Sensor atualiza vaga para LIVRE → Registro de saída criado, tempo calculado
3. Sistema calcula tarifa automaticamente baseado no tempo e tipo de vaga
4. (Opcional) Usuário/operador aplica cupom de desconto
5. Usuário pode pagar:
   ✅ Dinheiro no caixa
   ✅ Cartão de crédito/débito
   ✅ PIX pelo app, com QR Code gerado automaticamente
6. Pagamento confirmado → Ticket marcado como pago, libera saída
7. Valores são automaticamente contabilizados no caixa aberto
```

---

## 🧮 Cálculo automático de tarifa
O sistema calcula o valor de forma automática sem intervenção manual, com suporte a diferentes regras:

### Regras de cobrança configuráveis por tipo de vaga:
| Configuração | Finalidade |
|---|---|
| `tolerancia_minutos` | Tempo de tolerância SEM cobrança após entrada (padrão 15 minutos). Usuário que ficou menos que esse tempo não paga nada. |
| `valor_hora` | Valor por hora cheia de permanência (padrão). |
| `valor_fração_15min` | (Opcional) Se habilitado, cobra por fração de 15 minutos ao invés de hora cheia. |
| `valor_minimo` | Valor mínimo da cobrança (ex: R$5,00 mesmo que o valor calculado seja menor). |
| `valor_diaria` | Valor da diária (cobra diária ao invés de hora a hora quando o usuário ficar 9h ou mais). |

### Exemplo prático:
- Tolerância de 15 minutos → até 15min gratuito
- R$8/hora, sem fração → após 15min, 1h a 8min cobra 1 hora inteira = R$8,00
- 2h10min = 3 horas = R$24,00
- Se ficar mais de 9h → cobra diária de R$50 ao invés de 9 horas.

---

## 🎟️ Sistema de Cupons de Desconto
Tipos de cupom suportados:
1.  **Porcentagem**: Desconto de X% sobre o valor total (ex: DESC10 = 10% de desconto)
2.  **Valor fixo**: Desconto de R$ X fixo
3.  **Isenção total**: Isenta 100% do valor (ex: para visitantes, moradores, clientes com isenção)

Funcionalidades dos cupons:
- Código único alfanumérico (ex: BLACKFRIDAY10)
- Limite de usos por cupom (ex: só os primeiros 100 usos)
- Data de validade
- Contagem de usos realizados
- Vinculado por estacionamento, cada local pode criar seus próprios cupons.

---

## 💳 Formas de pagamento suportadas:
| Método | Funcionamento |
|---|---|
| 💵 Dinheiro | Pagamento no caixa presencial, calcula troco automaticamente se for enviado valor recebido. |
| 💳 Cartão de Crédito | Registrado no caixa após aprovação da máquina. |
| 💳 Cartão de Débito | Registrado no caixa após aprovação. |
| 📱 PIX | Geração automática de QR Code + código copia e cola para pagamento pelo aplicativo. |
|  | *Nota: Em produção, basta integrar com gateway (Mercado Pago, Efí, Pix Efí) usando o webhook de confirmação. O fluxo de geração já está pronto.* |

---

## 👨‍💼 Gestão de Caixa (Turnos)
Sistema de abertura e fechamento de caixa por turno/operador:

1.  **Abertura de caixa**:
    - Operador abre o caixa no início do turno informando o valor inicial do troco.
    - Só pode existir UM caixa aberto por estacionamento por vez.
    - Todos os pagamentos registrados enquanto o caixa está aberto são automaticamente contabilizados nos valores de PIX, Cartão e Dinheiro.

2.  **Durante o turno**:
    - Cada pagamento já soma automaticamente no caixa, por forma de pagamento.
    - É possível registrar sangria (retirada de dinheiro do caixa).

3.  **Fechamento de caixa**:
    - Operador fecha o caixa no final do turno.
    - Sistema consolida todos os valores:
      - Total em PIX
      - Total em cartão de crédito
      - Total em cartão de débito
      - Total em dinheiro
      - Quantidade total de pagamentos
      - Valor total de descontos dados
    - Gera um resumo para conferência no fechamento.

---

## 📡 Endpoints do módulo de pagamentos:
Todos os endpoints são protegidos e só podem ser acessados por usuários Financeiro, Gestor ou Admin. Os endpoints de geração de PIX são acessíveis também para o usuário comum que vai pagar pelo app.

| Método | Rota | Função |
|---|---|---|
| POST | `/api/admin/financeiro/calcular-tarifa?historico_id=` | Calcula valor da tarifa e aplica cupom se fornecido |
| POST | `/api/admin/financeiro/pagamento/registrar` | Registra pagamento presencial (dinheiro/cartão) |
| POST | `/api/admin/financeiro/pagamento/gerar-pix?historico_id=` | Gera QR Code PIX para pagamento pelo app |
| POST | `/api/admin/financeiro/pagamento/{id}/confirmar` | Webhook/confirmação manual de pagamento online |
| POST | `/api/admin/financeiro/caixa/abrir` | Abre novo caixa de turno |
| POST | `/api/admin/financeiro/caixa/{id}/fechar` | Fecha caixa e consolida valores |
| GET | `/api/admin/financeiro/caixa/aberto/{estacionamento_id}` | Retorna caixa aberto atualmente |
| POST | `/api/admin/financeiro/cupons` | Cria novo cupom de desconto |
| GET | `/api/admin/financeiro/cupons/{estacionamento_id}` | Lista cupons do estacionamento |

---

## 📊 Resumo financeiro atualizado com valores reais:
O endpoint de resumo financeiro já contabiliza:
- Faturamento total por período
- Ticket médio por estadia
- Total de pagamentos por método
- Valor total por forma de pagamento
- Faturamento por dia
- Total de descontos aplicados

---

## 🔌 Integração com gateways de pagamento:
Para produção com PIX/Cartão online, o fluxo já está preparado:
1.  Usuário clica em "Pagar com PIX" no app
2.  Backend cria registro de pagamento pendente
3.  Você chama a API do seu gateway (Mercado Pago/Efí) para gerar QR Code e salva o retorno nos campos `qr_code_pix` e `copia_cola_pix`
4.  Gateway chama o webhook `/api/admin/financeiro/pagamento/{id}/confirmar` quando o pagamento for aprovado
5.  Sistema automaticamente marca o ticket como pago e contabiliza valor no caixa.

Todo o resto do fluxo já está funcionando, você só precisa implementar a chamada para o gateway de pagamento de sua preferência.

---

## 🛡️ Segurança no faturamento:
- Todos registros de pagamento são auditáveis
- Somente usuários com permissão de Financeiro/Gestor podem registrar pagamentos ou abrir/fechar caixa
- Valores não podem ser alterados depois de confirmar o pagamento
- Todo fechamento de caixa registra qual operador abriu e qual fechou o turno
- Controle automático de valor de troco no pagamento em dinheiro evita erros de operador.
