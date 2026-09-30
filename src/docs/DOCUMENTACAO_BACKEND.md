# 🅿️ Documentação Completa do Backend - SmartParking API
Backend de gerenciamento inteligente de estacionamentos construído em FastAPI, com arquitetura limpa, desacoplada, segura e pronta para produção.

---

## 📋 Visão Geral
API RESTful para gerenciamento de estacionamentos com:
- Cadastro e gestão de estacionamentos, andares e vagas
- Sistema de reservas de vagas para usuários
- Motor de atribuição automática de próxima vaga disponível
- Integração nativa com sensores IoT de ocupação de vagas
- Módulo financeiro completo para controle de pagamentos e faturamento
- Relatórios de fluxo de veículos e taxa de ocupação
- Autenticação JWT + login social (Google, Facebook, Apple)
- 5 níveis de permissão de usuário
- Painel administrativo e dashboard de gestão
- Proteções completas de segurança contra ataques comuns
- Pronto para deploy com Docker, Load Balancer e PostgreSQL

---

## 🏗️ Arquitetura
O projeto segue a **Arquitetura Limpa (Clean Architecture)** com separação clara de responsabilidades em camadas, facilitando manutenção, testes e evolução sem acoplamento:

```
src/backend/
├── main.py                      # Ponto de entrada da aplicação
├── core/                        # Camada de infraestrutura transversal
│   ├── config.py               # Carregamento centralizado de variáveis de ambiente
│   ├── security.py             # Hash de senhas e geração/validação de JWT
│   ├── deps.py                 # Dependências reutilizáveis (sessão BD, permissões)
│   ├── security_middleware.py  # Middleware de segurança geral, proteção SQLi/XSS
│   ├── rate_limiter.py         # Rate limiting por rota/usuário
│   └── request_validator.py    # Assinatura HMAC de requisições, anti-replay/bloqueio Postman
├── api/                         # Camada de Apresentação (Rotas HTTP)
│   ├── api.py                  # Rotas públicas da API de estacionamentos, reservas, relatórios
│   ├── auth.py                 # Rotas de autenticação e login social
│   └── admin.py                # Rotas do painel administrativo e financeiro
├── models/                      # Camada de Dados
│   ├── database.py             # Configuração conexão SQLAlchemy, pool de conexões
│   ├── db_models.py            # Modelos ORM do banco de dados
│   └── schemas.py              # Schemas Pydantic de validação de entrada/saída
└── rules/                       # Camada de REGRAS DE NEGÓCIO (desacoplada de HTTP/BD)
    ├── auth_service.py             # Lógica de autenticação e criação de usuários
    ├── social_auth_service.py      # Lógica de login Google/Facebook/Apple
    ├── estacionamento_service.py   # Lógica de gestão de estacionamentos, busca de vagas
    ├── vaga_service.py             # Lógica de atualização de status de vagas e sensores
    ├── reserva_service.py          # Lógica de criação/cancelamento de reservas
    ├── financeiro_service.py       # Lógica de preços, pagamentos e relatórios financeiros
    ├── relatorio_service.py        # Lógica de relatórios de fluxo e ocupação
    └── admin_service.py            # Lógica de gerenciamento de usuários e permissões
```

### Princípios da arquitetura:
✅ **Independência de Framework**: As regras de negócio dentro de `rules/` não dependem de FastAPI nem de banco de dados, podem ser reutilizadas em qualquer outra interface.
✅ **Inversão de Dependência**: Rotas HTTP só chamam os serviços, nunca contém regra de negócio diretamente.
✅ **Separação de Responsabilidades**: Cada camada tem uma única função.
✅ **Fácil de testar**: Você pode chamar as funções de serviço diretamente sem subir o servidor HTTP.

---

## 👥 Níveis de Usuário e Permissões
| Cargo | Permissões |
|---|---|
| 🌐 **Público** | Acesso sem login: consulta de estacionamentos, mapa de vagas, busca de vaga disponível, atualização de status de sensor. |
| 👤 **Usuário (Motorista)** | Pode fazer/cancelar reservas, ver próprio perfil e histórico. |
| 💰 **Financeiro** | Vinculado a UM estacionamento específico: visualiza relatórios financeiros, registra pagamentos. Não pode editar vagas/estacionamento. |
| 🧑‍💼 **Gestor** | Vinculado a UM estacionamento específico: gerencia andares, vagas, preços e acessa todos os relatórios do seu estacionamento. |
| 🔴 **Admin Global** | Acesso TOTAL a todos os estacionamentos, cria novos estacionamentos, gerencia todos os usuários e permissões. |

> Conta de administrador padrão criada automaticamente na primeira execução:
> ```
> Email: admin@smartparking.com
> Senha: admin123
> ```

---

## ⚙️ Funcionalidades Principais

### 🅿️ Gestão de Estacionamentos
- Cadastro, edição e exclusão de estacionamentos
- Suporte a múltiplos andares por estacionamento
- Cadastro individual ou em lote de vagas (criação automática de códigos sequenciais como A01, A02)
- Tipos de vaga: Comum, Idoso, PCD, Moto, Vaga para carro elétrico
- Mapa completo de vagas por andar, com status e posição para desenhar mapa visual no frontend
- Motor de busca de próxima vaga disponível, com filtro por tipo de vaga

### 📅 Reservas
- Criação de reservas por usuário logado
- Validação automática de disponibilidade da vaga
- Atualização imediata de status da vaga para `reservada`
- Cancelamento de reserva com liberação automática da vaga
- Lista de reservas do usuário

### 🛰️ Integração com Sensores IoT
- Endpoint simples para receber atualização de status de vaga (`livre`/`ocupada`)
- Registro automático de entrada quando vaga fica ocupada
- Registro automático de saída quando vaga fica livre, com cálculo de tempo de permanência em minutos para cálculo de tarifa
- Sem necessidade de autenticação para facilitar integração com dispositivos

### 💰 Módulo Financeiro
- Configuração de preço por tipo de vaga (valor hora, diária, tolerância sem cobrança)
- Registro de pagamentos (PIX, Cartão, Dinheiro)
- Resumo financeiro por período (diário/semanal/mensal) com:
  - Faturamento total
  - Ticket médio
  - Quantidade de pagamentos por método
  - Valor total por forma de pagamento
  - Faturamento por dia
- Dashboard próprio para gestor/financeiro com dados do seu estacionamento
- Dashboard global para admin com visão consolidada de todos os locais

### 📊 Relatórios
- Relatório de fluxo de veículos: total de entradas, saídas e tempo médio de permanência
- Relatório de ocupação: taxa de ocupação geral e por andar para mapas de calor
- Todos relatórios podem ser filtrados por período e por estacionamento.

### 🔐 Autenticação
- Cadastro de usuários com senha em hash bcrypt
- Login por e-mail e senha com tokens JWT
- Access token de curta duração (15min) para uso rotineiro
- Refresh token de longa duração (7 dias) para renovar acesso sem novo login
- Login social nativo com:
  - Google
  - Facebook
  - Apple ID
- Criação automática de conta para usuários que logam com provedores sociais
- Renovação automática de token no frontend com interceptor Axios

---

## 🛡️ Segurança Implementada
O projeto foi construído com segurança em múltiplas camadas:

1.  **Proteção contra SQL Injection**:
    - Filtro de padrões maliciosos antes de chegar nas queries
    - 100% das consultas usando ORM SQLAlchemy com parâmetros preparados, sem concatenação de strings.

2.  **Bloqueio de abusos e Rate Limiting**:
    - Primeira camada no Nginx: 30 requisições por segundo por IP
    - Limite extremamente restrito para login/cadastro: 5 requisições por MINUTO por IP (anti-brute force)
    - Limites específicos por rota no backend
    - Bloqueio de requisições duplicadas em intervalo curto
    - Sistema de detecção e bloqueio de scanners automatizados (SQLMap, Nmap, Burp, etc.)

3.  **Bloqueio de acesso não autorizado por Postman/navegador**:
    - Assinatura HMAC obrigatória em requisições de escrita em produção
    - Apenas o app oficial sabe gerar a assinatura correta
    - Anti-replay com nonce único por requisição e timestamp de 5 minutos de validade
    - Bloqueio de User-Agents de navegador, Postman, curl/scripts em requisições de modificação.

4.  **Proteção contra interceptação de rede (Wireshark/MITM)**:
    - Configuração TLS/SSL forte pronta para produção
    - Documentação completa de implementação de SSL Pinning no aplicativo móvel, que impede completamente interceptação de tráfego mesmo com certificados falsos instalados no dispositivo.
    - HSTS para forçar sempre conexão HTTPS.

5.  **Segurança geral**:
    - Senhas armazenadas apenas com hash bcrypt + salt
    - CORS configurado para acesso do app React Native/Expo
    - Headers de segurança recomendados pela OWASP em todas as respostas
    - Remoção de headers que expõem versão do servidor/tecnologia
    - Execução em containers Docker com usuário não-root (sem privilégios de administrador)
    - Trusted Host Middleware bloqueia acessos com Host header falso em produção.
    - Desativação completa da documentação Swagger/Redoc em produção.

---

## ⚡ Performance e Escalabilidade
- **Pool de conexões com banco**: 10 conexões permanentes + 20 conexões em pico, com `pool_pre_ping` para recuperar conexões quebradas.
- **Load Balancer Nginx** na frente da aplicação distribuindo tráfego entre múltiplos workers.
- **Gunicorn como servidor de produção** com múltiplos workers: `(2 * núcleos CPU) + 1` processos para aproveitar todos os cores do servidor.
- Balanceamento de carga por método `least_conn` que envia requisição para o worker menos carregado.
- Reinício automático de workers após 1000 requisições para evitar vazamentos de memória.
- Configuração Docker Compose pronta com:
  - Nginx como proxy reverso
  - Múltiplas réplicas do backend (configurável)
  - PostgreSQL 15 com volume persistente
  - PgAdmin opcional para gerenciamento do banco de dados
- Você pode aumentar a capacidade simplesmente aumentando o número de réplicas no docker-compose, sem outras alterações.

---

## 🚀 Como rodar o projeto

### Pré-requisitos
- Docker e Docker Compose instalados
- Python 3.10+ (para desenvolvimento local sem Docker)

### Ambiente de desenvolvimento rápido:
Use o script automatizado:
```bash
chmod +x run-dev.sh
./run-dev.sh
```
Ele sobe o PostgreSQL no Docker automaticamente, instala dependências e inicia o backend com recarga automática.

### Ambiente de produção:
1.  Gere uma chave secreta segura:
    ```bash
    openssl rand -hex 32
    ```
2.  Altere as variáveis no `.env` para produção:
    - Coloque `ENVIRONMENT=production`
- Insira sua `SECRET_KEY`
- Adicione chaves de login social se for usar
3.  (Opcional) Adicione certificados SSL na pasta `nginx/ssl`
4.  Suba a stack completa com Docker:
    ```bash
    docker compose up -d --build
    ```
Isso sobe Nginx, múltiplas instâncias do backend e PostgreSQL já com todas as proteções ativadas.

### Documentação automática
Em ambiente de desenvolvimento, acesse:
- Swagger UI: http://localhost:8000/docs → Teste todos os endpoints diretamente no navegador
- Redoc: http://localhost:8000/redoc → Documentação alternativa

---

## 📦 Dependências Principais
| Biblioteca | Finalidade |
|---|---|
| FastAPI | Framework web rápido e moderno para APIs |
| Uvicorn/Gunicorn | Servidores ASGI de produção |
| SQLAlchemy 2.0 | ORM para banco de dados, queries seguras |
| Psycopg2 | Driver para PostgreSQL |
| PyJWT | Geração e validação de tokens JWT |
| bcrypt | Hash seguro de senhas |
| SlowAPI | Rate limiting |
| HTTPX | Cliente HTTP para validação de tokens OAuth |
| Pydantic | Validação de dados de entrada e saída |
| Pydantic Settings | Carregamento de variáveis de ambiente |

---

## 📚 Documentações complementares na raiz do projeto:
- `README.md` → Introdução e comandos iniciais
- `docker-commands.md` → Guia com todos comandos do Docker/Docker Compose
- `INTEGRACAO_FRONTEND.md` → Guia de integração com o frontend React Native, payloads exatos das requisições, autenticação social e código de exemplo do Axios
- `SEGURANCA_E_PERFORMANCE.md` → Detalhes das proteções de segurança
- `SEGURANCA_TLS_WIRESHARK.md` → Explicação de como proteger o tráfego contra Wireshark/MITM com SSL Pinning
- `PROTECAO_REQUISICOES.md` → Funcionamento da assinatura HMAC de requisições contra replicação
- `NGINX_EXPLICADO.md` → Documentação linha por linha da configuração do Nginx

---

## ✅ Status do projeto
- ✅ Estrutura desacoplada completa
- ✅ Todos endpoints funcionando e testados (26 rotas)
- ✅ Todos os níveis de permissão implementados
- ✅ Módulo financeiro completo
- ✅ Relatórios de ocupação e fluxo
- ✅ Autenticação JWT + Login social
- ✅ Docker Compose pronto para produção
- ✅ Todas camadas de segurança implementadas
- ✅ Configuração Nginx com balanceamento de carga
- ✅ Pronto para integração com frontend React Native/Expo e painel web administrativo
