# SmartParking - Sistema de Gerenciamento Inteligente de Vagas

Projeto completo com backend em FastAPI (desacoplado) e frontend para React Native/Expo.

## Estrutura do projeto
```
.
├── docker-compose.yml    # Configuração Docker do PostgreSQL + PgAdmin
├── run-dev.sh            # Script para iniciar tudo com um comando
├── src/
│   ├── backend/          # Código do FastAPI
│   └── frontend/         # Futuro código React Native/Expo
└── README.md
```

## 🐳 Como rodar o BANCO DE DADOS com Docker

Não precisa instalar PostgreSQL na sua máquina! Tudo já está configurado no `docker-compose.yml`.

### 1. Iniciar apenas o banco de dados
```bash
docker compose up -d
```

Isso irá subir:
- ✅ PostgreSQL 15 na porta `5432`
  - Usuário: `postgres`
  - Senha: `postgres`
  - Banco: `smartparking`
- ✅ PgAdmin (interface gráfica para gerenciar o banco) em http://localhost:5050
  - E-mail: `admin@admin.com`
  - Senha: `admin`

### 2. Verificar se o banco está rodando
```bash
docker compose ps
```

### 3. Iniciar o backend FastAPI
```bash
cd src/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

A API estará disponível em http://localhost:8000/docs (Swagger).

## 🚀 Iniciar TUDO com UM comando
Use o script que preparei para você:
```bash
./run-dev.sh
```
Ele vai:
1. Subir o PostgreSQL no Docker
2. Esperar o banco ficar pronto
3. Instalar dependências do backend
4. Iniciar o servidor FastAPI automaticamente

## 🛑 Parar o banco de dados
```bash
docker compose down
```

## 🗑️ Parar e apagar todos os dados do banco (cuidado!)
```bash
docker compose down -v
```

## Credenciais de conexão
Todas já estão pré-configuradas no arquivo `.env` do backend:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartparking
```

### Conectar PgAdmin ao banco:
Quando abrir o PgAdmin em http://localhost:5050:
1. Clique em "Add New Server"
2. Name: `SmartParking`
3. Aba Connection:
   - Host name/address: `postgres` (nome do serviço no docker-compose, use localhost se conectar de fora do container)
   - Port: `5432`
   - Username: `postgres`
   - Password: `postgres`
4. Clique em Save
