# SmartParking API - Backend FastAPI Desacoplado

Backend 100% compatível com os arquivos que você já possui, construído com arquitetura limpa e desacoplada, seguindo os princípios SOLID.

## Estrutura final de arquivos (compatível com o que você já criou)
```
src/
└── backend/
    ├── main.py              # Entrada da aplicação, inicializa FastAPI e middlewares
    ├── .env                 # Variáveis de ambiente locais
    ├── .env-sample          # Exemplo de variáveis de ambiente
    ├── requirements.txt     # Dependências do projeto
    ├── core/                # Camada de configurações e utilitários centrais
    │   ├── config.py        # Carrega variáveis de ambiente do .env
    │   ├── security.py      # Hash de senhas + funções JWT (PyJWT como no seu auth.py original)
    │   └── deps.py          # Dependências reutilizáveis (get_db, get_usuario_logado)
    ├── api/                 # Camada de apresentação (rotas)
    │   ├── api.py           # Rotas principais do SmartParking (todos os endpoints do escopo)
    │   └── auth.py          # Rotas de autenticação (registrar, login, refresh, me)
    ├── models/              # Camada de dados (compatible com seus db_models.py)
    │   ├── database.py      # Conexão SQLAlchemy (PostgreSQL como padrão, pool configurado)
    │   ├── db_models.py     # Modelos ORM (Usuario, Estacionamento, Andar, Vaga, Reserva, Historico)
    │   └── schemas.py       # Schemas Pydantic para validação de entrada/saída
    └── rules/               # Camada de REGRAS DE NEGÓCIO (desacoplada das rotas)
        ├── auth_service.py       # Lógica de autenticação e geração de tokens
        ├── estacionamento_service.py # Lógica de estacionamentos, andares e busca de vaga
        ├── vaga_service.py       # Lógica de gerenciamento de status de vagas e sensores
        ├── reserva_service.py    # Lógica de criação/cancelamento de reservas
        └── relatorio_service.py  # Lógica de relatórios de fluxo e ocupação
```

## Principais características
✅ **Totalmente desacoplado**: Rotas não contém lógica de negócio, só recebem requisições e chamam os serviços
✅ **Compatível com seus arquivos originais**: Mantive a configuração PostgreSQL, UUID como ID, PyJWT e estrutura de Andares/Vagas
✅ **Autenticação JWT completa**: Access token (15min) + Refresh token (7dias), exatamente como seu auth.py
✅ **Segurança**: Senhas com hash bcrypt, CORS configurado para app mobile React Native/Expo
✅ **Relacionamentos corretos**: Estacionamento → Andar → Vaga, conforme seu modelo
✅ **Histórico automático**: Atualização de status de vaga já cria registro de entrada/saída automaticamente
✅ **Validação com Pydantic**: Todos os dados de entrada são validados
✅ **Documentação automática Swagger/Redoc**: Acesse `/docs` para testar todos endpoints

## Como rodar o projeto

### 1. Pré-requisitos
- Python 3.10+
- PostgreSQL rodando com banco `smartparking` criado (ou use SQLite em desenvolvimento)

### 2. Instalação
```bash
cd src/backend
python -m venv venv

# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configuração
Copie o arquivo `.env-sample` para `.env` e ajuste a `DATABASE_URL` se necessário:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartparking
SECRET_KEY=sua_chave_secreta_de_producao_aqui
```

### 4. Rodar o servidor
```bash
python main.py
```

A API estará disponível em `http://0.0.0.0:8000` (acessível pelo seu celular na mesma rede Wi-Fi para testar com Expo/React Native).

### 5. Documentação
- Swagger UI: http://localhost:8000/docs (teste todos os endpoints diretamente no navegador)
- Redoc: http://localhost:8000/redoc

## Endpoints implementados (exatamente o escopo que você pediu):

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET | `/` | Status da API | Não |
| GET | `/api/status` | Status do backend | Não |
| GET | `/api/health` | Health check (banco de dados incluso) | Não |
| GET | `/api/version` | Versão da API | Não |
| POST | `/auth/registrar` | Cadastro de novo usuário | Não |
| POST | `/auth/login` | Login (retorna access + refresh token) | Não |
| POST | `/auth/refresh` | Renova access token | Não |
| GET | `/auth/me` | Dados do usuário logado | Sim (JWT) |
| GET | `/api/estacionamentos` | Lista todos os estacionamentos com contagem de vagas por andar | Não |
| GET | `/api/estacionamentos/{id}/vagas` | Mapa de vagas detalhado, organizado por andares | Não |
| GET | `/api/estacionamentos/{id}/proxima-vaga` | Consulta ao motor de atribuição de próxima vaga | Não |
| POST | `/api/reservas` | Cria nova reserva vinculada ao usuário | Sim (JWT) |
| DELETE | `/api/reservas/{id}` | Cancela reserva e libera vaga imediatamente | Sim (JWT) |
| GET | `/api/reservas/minhas` | Lista reservas do usuário logado | Sim (JWT) |
| PATCH | `/api/vagas/{id}/status` | Atualiza status da vaga (manual/sensor) | Não |
| GET | `/api/relatorios/fluxo` | Relatório de entradas/saídas por período | Não |
| GET | `/api/relatorios/ocupacao` | Taxa de ocupação e dados por andar (mapas de calor) | Não |

## Diferença para o seu código inicial
1. **Desacoplamento total**: Toda lógica de negócio foi movida para a pasta `rules/` como serviços reutilizáveis — suas rotas em `api/` são finas e só tratam HTTP.
2. **Configurações centralizadas**: Todas as variáveis de ambiente são carregadas via pydantic-settings no `core/config.py`
3. **Segurança melhorada**: Adicionei hash de senha com bcrypt e dependência de usuário logado reutilizável em todas as rotas que precisam de autenticação.
4. **Tratamento de erros padronizado**: Exceções HTTP com mensagens claras e código de status correto.
5. **Compatibilidade com PostgreSQL**: Mantive sua configuração original de pool de conexões.
6. **Estrutura de múltiplos andares**: Suporte nativo a estacionamentos com vários andares, diferente da estrutura plana de setores que tinha inicialmente.
7. **Histórico automático**: Quando uma vaga muda de status para ocupada/livre o sistema já automaticamente registra entrada/saída para os relatórios.

## Para desenvolvimento com SQLite (sem precisar instalar PostgreSQL)
Basta alterar a `DATABASE_URL` no `.env`:
```env
DATABASE_URL=sqlite:///./smartparking.db
```
