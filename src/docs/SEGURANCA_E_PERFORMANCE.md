# 🛡️ Mapa de Segurança e Performance da API
Todas as proteções implementadas contra acessos indevidos, ataques e otimizações de carga.

---

## ❌ O que usuários NÃO conseguem fazer:
1.  **Acessar documentação da API /docs e /redoc em produção**: desativado automaticamente quando `ENVIRONMENT=production`, não expõe os endpoints para quem acessar a URL diretamente.
2.  **Acessar a API com User-Agent de scanners automatizados**: SQLMap, Nikto, Burp, Nmap, Acunetix são bloqueados automaticamente.
3.  **Acessar arquivos sensíveis (.env, .py, .sql, .md)**: Bloqueado diretamente pelo Nginx antes mesmo de chegar no backend.
4.  **Enviar requisições com SQL Injection**: Verificação automática em TODOS os parâmetros (query string, path, corpo JSON) com padrões comuns de injeção SQL/XSS.
5.  **Fazer brute force em login**: Limite restrito de 10 tentativas por minuto no backend e 5 por minuto no Nginx.
6.  **Enviar requisições duplicadas**: Bloqueio de requisições idênticas no intervalo de 1 segundo evita cliques duplos e repetição automática.
7.  **Fazer flood de requisições**: Rate limiting em várias camadas (Nginx + Backend) com limites diferentes por tipo de rota.
8.  **Ver qual tecnologia a API usa**: Headers `Server` e `X-Powered-By` são removidos para não expor que é FastAPI/Uvicorn.
9.  **Inserir scripts XSS nos parâmetros**: Detectado pelo mesmo filtro de SQL Injection.

---

## 🚦 Sistema de Rate Limiting (Limite de requisições):
Camadas duplas de proteção:

### 1. Primeira camada: Nginx (bloqueia antes de chegar no backend)
| Tipo de rota | Limite por IP |
|---|---|
| Geral | 30 requisições por segundo, com burst de 50 |
| Login/Cadastro | 5 requisições por MINUTO (anti brute force) |
| Conexões simultâneas por IP | 20 |

### 2. Segunda camada: Backend SlowApi (distinção por usuário logado ou IP)
| Rota | Limite |
|---|---|
| Login/Registro | 10/minuto |
| Refresh token | 20/minuto |
| Cadastro | 5/minuto |
| Atualizar status de vaga (sensores) | 60/minuto |
| Criar reserva | 30/minuto |
| Registrar pagamento | 15/minuto |
| Consultas públicas (vagas/estacionamentos) | 120/minuto |
| Relatórios | 30/minuto |
| Limite global padrão | 200/minuto |

> ✅ Quando o usuário está logado, o limite é atrelado ao token dele, não ao IP. Se ele mudar de rede continua com seu limite.

---

## 🩺 Proteção contra SQL Injection:
Implementei verificação em MULTIPLAS camadas:
1.  **Bloqueio no middleware**: Padrões clássicos de injeção como `UNION SELECT`, `DROP TABLE`, `OR 1=1`, comentários `--`, aspas não fechadas, comandos `xp_/sp_` do SQL Server são detectados imediatamente na requisição e retorna erro 400 antes mesmo de chegar na query do banco.
2.  **SQLAlchemy usa queries parametrizadas POR PADRÃO**: Todas as consultas ao banco usam parâmetros preparados, nunca concatenação de string. O SQLAlchemy escapa automaticamente todos os valores, impossibilitando injeção mesmo que o filtro falhe.
3.  **Permissões do banco de dados**: O usuário do PostgreSQL usado pela aplicação deve ter somente permissões de SELECT/INSERT/UPDATE/DELETE, sem permissão de DROP/ALTER/CREATE em produção.

---

## ⚖️ Load Balancing e Pool de Conexões:
### Arquitetura de produção Docker:
```
Usuário → Nginx (Proxy Reverso/Load Balancer) → Múltiplas instâncias do Backend → PostgreSQL
```

1.  **Nginx como Load Balancer**:
    - Método `least_conn` envia nova requisição para o worker com menos conexões ativas, distribuindo carga igualmente.
    - Configurado com 2 réplicas do backend por padrão (escalável para quantas instâncias você precisar, só alterar o `replicas` no docker-compose).
    - Timeouts configurados para não travar requisições.

2.  **Gunicorn como servidor de produção**:
    - Roda `(2 * núcleos de CPU) + 1` workers por padrão. Cada worker é um processo separado do Uvicorn, aproveitando todos os núcleos da CPU.
    - Reinicia automaticamente workers após 1000 requisições para evitar vazamentos de memória, com aleatoriedade para não cair todas de uma vez.
    - Usa `/dev/shm` para arquivos temporários para maior performance.

3.  **Pool de conexões com banco de dados**:
    - Configurado no SQLAlchemy com `pool_size=10, max_overflow=20` (10 conexões permanentes + 20 temporárias em pico).
    - `pool_pre_ping=True` recupera automaticamente conexões quebradas com o banco sem dar erro.

---

## 🔒 Headers de Segurança aplicados em TODAS as respostas:
| Header | Função |
|---|---|
| `X-Content-Type-Options: nosniff` | Bloqueia navegadores de adivinhar tipo de arquivo, evita download executável indevido. |
| `X-Frame-Options: DENY` | Bloqueia a API de ser carregada em iframes, evita ataques de clickjacking. |
| `X-XSS-Protection: 1; mode=block` | Ativa proteção nativa dos navegadores contra XSS. |
| `Referrer-Policy: strict-origin-when-cross-origin` | Não envia URL completa como referenciador para sites externos. |
| `Content-Security-Policy` | Bloqueia carregamento de scripts externos e conteúdo inline. |
| `Permissions-Policy` | Desativa acesso a microfone e geolocalização por padrão. |
| `Strict-Transport-Security` | Força HTTPS em produção por 1 ano. |
| `Cache-Control: no-store` | Não armazena respostas da API em cache do navegador. |
| Remoção de `Server` e `X-Powered-By` | Não expõe versões de Nginx/Uvicorn/FastAPI para atacantes. |

---

## 📋 Outras proteções implementadas:
✅ Anti-duplicação de requisições: Requisições idênticas do mesmo IP em menos de 1 segundo são rejeitadas.
✅ Validação automática de dados pelo Pydantic: Todos os campos de entrada são validados antes de chegar na lógica de negócio, tipos de dados incorretos são rejeitados com erro 422.
✅ Tokens JWT com expiração curta (15min) e refresh token separado.
✅ Senhas armazenadas com hash bcrypt com salt, nunca texto puro.
✅ Em Docker, o backend roda como usuário NÃO-ROOT, minimizando danos em caso de vulnerabilidade.
✅ Health check do banco + containers com restart automático se algum serviço cair.

---

## 🚀 Como rodar em produção com todas proteções:
```bash
# 1. Altere SECRET_KEY no .env para uma chave segura (gere com):
openssl rand -hex 32

# 2. Altere ENVIRONMENT=production no .env para desativar /docs e ativar headers de HTTPS
ENVIRONMENT=production

# 3. Suba tudo com docker compose:
docker compose up -d --build
```

Isso sobe Nginx + múltiplos backends + PostgreSQL já com todas as proteções ativadas automaticamente.

---

## 📈 Escalabilidade:
- Se precisar de mais capacidade é só aumentar o `replicas` do serviço `backend` no docker-compose para 3, 4, 10 instâncias, o Nginx distribui o tráfego automaticamente.
- Se for usar múltiplos servidores, pode colocar o Nginx como load balancer na frente de vários servidores backend.
- Para rate limiting compartilhado entre múltiplas instâncias, basta mudar o `storage_uri` no rate_limiter.py para usar Redis ao invés de memória.
