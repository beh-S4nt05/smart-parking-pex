# 🐳 Guia de Comandos Docker para o SmartParking
Comandos essenciais para gerenciar os containers do PostgreSQL e PgAdmin do projeto

---

## 🚀 Comandos principais de ciclo de vida

| Comando | O que faz | Exemplo de uso no projeto |
|---------|-----------|---------------------------|
| `docker compose up` | Cria e inicia TODOS os containers do projeto (banco + pgadmin), mostrando logs no terminal. Não use em produção sem `-d`. | Use para testar inicialização pela primeira vez e ver erros em tempo real. |
| `docker compose up -d` | Cria e inicia os containers em segundo plano (*detached mode*), sem travar o terminal. | ✅ **Comando mais usado no dia a dia** para subir o ambiente de desenvolvimento. |
| `docker compose down` | Para e remove todos os containers, redes criadas para o projeto. (Mantém os dados do banco salvos!) | Use quando quiser parar o ambiente completamente depois de usar. |
| `docker compose down -v` | Para e remove containers **E APAGA TODOS OS DADOS DO BANCO DE DADOS** (apaga os volumes). Volta o banco para o estado zero. | ⚠️ Cuidado! Use só se quiser recomeçar o banco do zero, apagando todos os estacionamentos, usuários e reservas. |

---

## 📊 Comandos de monitoramento e status

| Comando | O que faz | Exemplo de uso |
|---------|-----------|----------------|
| `docker compose ps` | Lista todos os containers do projeto, mostrando status, portas mapeadas e saúde. | Use para verificar se o PostgreSQL está rodando e saudável antes de iniciar o backend. |
| `docker compose logs` | Mostra todos os logs de todos os serviços em tempo real, anexando ao terminal. | Use para debugar erros de inicialização do banco. Pressione `Ctrl+C` para sair. |
| `docker compose logs -f postgres` | Mostra apenas os logs do PostgreSQL, acompanhando em tempo real (`-f` = follow). | Ideal para ver se o banco aceitou conexões. |
| `docker compose logs -f pgadmin` | Mostra apenas os logs do PgAdmin. | Use se tiver problema para acessar a interface web do PgAdmin. |
| `docker compose logs --tail=50` | Mostra apenas as últimas 50 linhas de logs, sem poluir o terminal. | Boa para checar erros recentes sem ver todo o histórico. |

---

## ⚡ Comandos de controle de serviços sem remover

| Comando | O que faz | Quando usar |
|---------|-----------|-------------|
| `docker compose stop` | Para todos os containers **sem apagar nada**. Os containers ficam parados, com dados intactos. | Use se for só pausar o trabalho por um momento, sem apagar os recursos. |
| `docker compose stop postgres` | Para APENAS o PostgreSQL, mantendo o PgAdmin rodando. | Manutenção rápida do banco. |
| `docker compose start` | Inicia containers que estavam parados (depois de um `stop`). | Use para retomar o trabalho depois de pausar. É mais rápido que `up` porque não recria nada. |
| `docker compose restart` | Reinicia todos os serviços (para e liga de novo). | Se o banco estiver com conexão travada, use para reiniciar. |
| `docker compose restart postgres` | Reinicia só o PostgreSQL, sem mexer no PgAdmin. | Quando precisar reiniciar apenas o banco após alterar configurações. |

---

## 🔨 Comandos de construção e manutenção de imagens

| Comando | O que faz | Quando usar |
|---------|-----------|-------------|
| `docker compose build` | Constrói/recostrui as imagens Docker dos serviços (no nosso caso não precisa muito porque usamos imagens prontas do PostgreSQL/PgAdmin). | Se você futuramente adicionar um Dockerfile para o próprio backend FastAPI, use esse comando para reconstruir a imagem depois de alterar dependências. |
| `docker compose build --no-cache` | Reconstrói as imagens SEM usar cache, do zero. | Se estiver com problema de versão antiga da imagem, use para forçar download da versão mais nova. |
| `docker compose pull` | Baixa a versão mais recente das imagens do Docker Hub. | De vez em quando execute para atualizar o PostgreSQL 15 e PgAdmin para as versões mais novas de segurança. |

---

## 🛠️ Comandos úteis para manutenção do SmartParking

### 1. Acessar o banco de dados PostgreSQL diretamente pelo terminal (sem PgAdmin):
```bash
docker exec -it smartparking-postgres psql -U postgres -d smartparking
```
Você entra direto no console psql e pode rodar comandos SQL manualmente. Digite `\q` para sair.

### 2. Fazer backup do banco de dados para um arquivo:
```bash
docker exec smartparking-postgres pg_dump -U postgres smartparking > backup_smartparking.sql
```
Isso cria um arquivo `backup_smartparking.sql` com todos os dados e estrutura do seu banco.

### 3. Restaurar backup do banco:
```bash
cat backup_smartparking.sql | docker exec -i smartparking-postgres psql -U postgres -d smartparking
```

### 4. Verificar o uso de espaço dos volumes (dados persistidos):
```bash
docker system df -v
```

### 5. Limpar recursos não utilizados (libera espaço em disco):
```bash
docker system prune
```
⚠️ Apaga imagens, redes e containers parados que não estão sendo usados. Não apaga volumes de dados do seu projeto SmartParking.

---

## 📋 Fluxo do dia a dia de desenvolvimento do SmartParking:

### 1. Ligar o ambiente para trabalhar:
```bash
# 1. Entra na pasta raiz do projeto
cd caminho/para/seu/projeto

# 2. Sobe o banco em segundo plano
docker compose up -d

# 3. Espera 5 segundos pro banco ficar pronto, depois inicia o backend
cd src/backend
python main.py
```

### 2. Quando terminar de trabalhar:
```bash
# 1. Pare o servidor FastAPI com Ctrl+C no terminal

# 2. Volta para pasta raiz e para os containers
cd ../..
docker compose stop
```

### 3. Quero apagar tudo e recomeçar o banco do zero:
```bash
docker compose down -v
docker compose up -d
```
Na próxima vez que rodar o backend ele cria um banco novo, com a conta de admin padrão `admin@smartparking.com / admin123`

---

## ❓ Problemas comuns e soluções

| Problema | Comando para resolver |
|----------|------------------------|
| Porta 5432 já está em uso por outro PostgreSQL na sua máquina | Pare o outro PostgreSQL, ou altere a porta mapeada no docker-compose.yml de `"5432:5432"` para `"5433:5432"` (lembre de alterar também a DATABASE_URL no .env para `postgresql://postgres:postgres@localhost:5433/smartparking`) |
| O backend não consegue conectar no banco | Execute `docker compose ps` e verifique se o postgres está com status `healthy`. Se não estiver, espere mais uns 10 segundos e tente novamente ou use `docker compose restart postgres`. |
| Erro de permissão no PgAdmin | Use `docker compose restart pgadmin` |
| Quero resetar a senha do admin sem apagar tudo | Acesse o psql com o comando `docker exec -it smartparking-postgres psql -U postgres -d smartparking` e rode um UPDATE na tabela usuarios para redefinir o senha_hash. |

---

## 🔗 URLs úteis quando os containers estão rodando:
- 📚 Documentação da API FastAPI: http://localhost:8000/docs
- 🐘 Interface do PgAdmin: http://localhost:5050
- Banco de dados PostgreSQL: `localhost:5432`
