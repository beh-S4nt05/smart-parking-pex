# 📖 Guia COMPLETO da configuração do Nginx
Todas as opções explicadas linha por linha, com o porquê de cada configuração e como alterar para produção.

---

## Por que usamos Nginx?
O Nginx fica na FRENTE do backend FastAPI como **proxy reverso e balanceador de carga**. Ele é o primeiro ponto que recebe todas as requisições dos usuários antes mesmo de chegar na aplicação. Ele resolve diversos problemas:

1.  🚀 **Desempenho**: Ele é muito mais rápido para servir arquivos estáticos e gerenciar milhares de conexões simultâneas que o Uvicorn/Gunicorn diretamente.
2.  ⚖️ **Balanceamento de carga**: Distribui requisições entre múltiplas instâncias do backend automaticamente.
3.  🛡️ **Segurança**: Bloqueia ataques antes de chegar na sua aplicação (rate limiting, acesso a arquivos sensíveis, etc).
4.  🔒 **SSL/TLS**: Gerencia certificados HTTPS/HTTP2 de forma performática.
5.  📊 **Logs e monitoramento**: Registra todos os acessos.

---

## Estrutura dos arquivos de configuração:
```
nginx/
├── nginx.conf           # Configurações GLOBAIS do Nginx
└── conf.d/
    ├── smartparking.conf    # Configuração específica do site SmartParking
    └── ssl-strong.conf      # Configuração SSL/TLS forte para produção (comentado por padrão)
```

---

## 📝 Explicação linha por linha do `nginx.conf`
```nginx
user nginx;
```
> Executa o processo do Nginx com um usuário não privilegiado (`nginx`), não como root. Boa prática de segurança: se houver vulnerabilidade no Nginx o atacante não ganha acesso root ao servidor.

---
```nginx
worker_processes auto;
```
> Define quantos processos trabalhadores o Nginx vai usar. `auto` usa automaticamente a QUANTIDADE DE NÚCLEOS DE CPU do servidor, maximizando performance. Para uma máquina de 4 núcleos ele cria 4 processos, cada um usando 1 core 100%.

---
```nginx
worker_rlimit_nofile 10000;
```
> Aumenta o limite de arquivos abertos por processo para suportar muitas conexões simultâneas.

---
```nginx
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;
```
> Configura logs de erro em nível `warn` (apenas avisos e erros, não polui com informações) e define o caminho do arquivo PID do processo principal.

---
```nginx
events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}
```
Bloco de configuração de conexões:
- `worker_connections 4096`: Cada worker aceita até 4096 conexões simultâneas. Com 4 núcleos = 16 mil conexões simultâneas no total.
- `use epoll`: Usa o método de I/O mais eficiente do Linux (epoll), essencial para alta performance.
- `multi_accept on`: Aceita todas as conexões novas de uma vez ao invés de uma por uma.

---
```nginx
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
```
Início do bloco de configurações HTTP:
- Carrega todos os tipos MIME padrão para dizer ao navegador que tipo de arquivo está sendo servido (ex: imagem jpg, css, javascript).
- Se não reconhecer o tipo de arquivo, trata como download binário.

---
```nginx
    server_tokens off;
    client_max_body_size 10M;
```
- `server_tokens off`: **ESCONDE a versão do Nginx nas respostas**. Impede que atacantes saibam qual versão do Nginx você está rodando para procurar vulnerabilidades específicas dessa versão.
- `client_max_body_size 10M`: Limita o tamanho máximo do corpo da requisição em 10MB (evita uploads gigantes que travem o servidor).

---
```nginx
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'tempo_resposta=$request_time';

    access_log /var/log/nginx/access.log main;
```
Define o formato dos logs de acesso com:
- IP do usuário
- Horário da requisição
- Rota acessada
- Código de status HTTP
- Bytes enviados
- User Agent
- IP real atrás de proxy
- Tempo de resposta da requisição em segundos (muito útil para detectar lentidão).

---
```nginx
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 30;
    keepalive_requests 100;
```
Configurações de performance TCP:
- `sendfile on`: Usa chamada de sistema `sendfile()` para enviar arquivos diretamente do kernel para a placa de rede, sem copiar para memória de usuário (extremamente mais rápido).
- `tcp_nopush`: Envia cabeçalhos e dados em pacotes maiores, reduzindo quantidade de pacotes na rede.
- `tcp_nodelay`: Envia dados pequenos imediatamente, sem esperar para encher pacote, diminuindo latência.
- `keepalive_timeout 30`: Mantém conexões abertas por 30 segundos, evita ter que fazer handshake TCP toda hora.
- `keepalive_requests 100`: Fecha conexão depois de 100 requisições na mesma conexão keepalive.

---
```nginx
    # Zonas de rate limit em nível de Nginx
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
    limit_req_zone $binary_remote_addr zone=req_limit_per_ip:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```
**Cria as zonas de memória compartilhada para rate limit (funcionam antes mesmo de chegar no backend!)**:
- `conn_limit_per_ip:10m`: Zona de memória de 10MB para contar conexões por IP, suficiente para ~160 mil IPs. Limita conexões simultâneas.
- `req_limit_per_ip:10m rate=30r/s`: Limite GLOBAL de 30 requisições POR SEGUNDO por IP. Bloqueia flood/DDoS automaticamente antes de chegar na API.
- `login_limit:10m rate=5r/m`: Limite MUITO restrito APENAS para rotas de login/cadastro: MÁXIMO 5 REQUISIÇÕES POR MINUTO por IP. Essencial contra ataques de brute force.

> 💡 Essa é a PRIMEIRA camada de proteção: se alguém mandar milhares de requisições por segundo o Nginx bloqueia imediatamente devolvendo erro 429 sem nem mesmo encostar na sua aplicação FastAPI, evitando que ela trave.

---
```nginx
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```
Headers de segurança padrão aplicados em TODAS as respostas:
- `X-Frame-Options: DENY`: Não permite que seu site seja carregado dentro de iframes em outros sites, evita ataques de clickjacking.
- `X-Content-Type-Options: nosniff`: Bloqueia navegadores de adivinhar tipo de arquivo, evita execução de scripts maliciosos.
- `Referrer-Policy`: Não envia a URL completa como referenciador para sites externos.

---
```nginx
    include /etc/nginx/conf.d/*.conf;
}
```
Inclui todos os arquivos de configuração de sites dentro da pasta `conf.d/`.

---

## 📝 Explicação linha por linha do `conf.d/smartparking.conf`
Esse arquivo é a configuração específica do domínio do SmartParking:

```nginx
upstream backend_pool {
    least_conn;
    server backend:8000;
}
```
**Define o POOL DE SERVIDORES BACKEND para balanceamento de carga:**
- `upstream backend_pool` é o nome do grupo de servidores.
- `least_conn`: Método de balanceamento de carga: **envia nova requisição para o servidor/worker com MENOS conexões ativas no momento**. Isso distribui a carga de forma inteligente, evitando mandar mais requisições para um worker que já está sobrecarregado. Existem outros métodos:
  - `round_robin` (padrão): Envia uma para cada servidor em sequência.
  - `ip_hash`: Envia o mesmo IP sempre para o mesmo servidor (bom para sessões em memória, mas não precisamos pois usamos JWT).
- `server backend:8000`: Adiciona o serviço chamado `backend` (definido no docker-compose) rodando na porta 8000.
  > 🚀 Se você quiser aumentar a capacidade basta adicionar mais replicas do backend no docker-compose, ou adicionar mais linhas `server ip:port` apontando para outros servidores backend, o Nginx automaticamente distribui a carga entre todos.

---
```nginx
server {
    listen 80 default_server;
    server_name _;
```
Bloco do servidor que escuta na porta 80 (HTTP padrão), responde por qualquer domínio.

---
```nginx
    limit_conn conn_limit_per_ip 20;
    limit_req zone=req_limit_per_ip burst=50 nodelay;
```
- Limita em MÁXIMO 20 CONEXÕES SIMULTÂNEAS por IP.
- Aplica o limite global de 30 requisições/segundo por IP, com `burst=50`: aceita até 50 requisições em rajada curta sem bloquear, depois limita a 30/s.
- `nodelay`: Responde imediatamente as requisições no burst ao invés de atrasar elas.

---
```nginx
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    location ~ \.(env|py|sh|sql|md)$ {
        deny all;
        access_log off;
    }
```
**Bloqueia ACESSO DIRETO a arquivos sensíveis**:
- Qualquer arquivo que comece com `.` (ex: `.env`, `.git`) retorna 403 Proibido.
- Qualquer arquivo com extensão `.env`, `.py`, `.sh`, `.sql`, `.md` é bloqueado diretamente.
- Não gera log dessas requisições para não poluir os logs.
> Impede que alguém acesse diretamente seu `.env` com senhas ou código fonte pelo navegador!

---
```nginx
    location / {
        limit_req_status 429;
        limit_conn_status 429;

        proxy_pass http://backend_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }
```
Regra padrão que envia TODAS as requisições para o pool de backends:
- Define código 429 para quando o limite de requisições for excedido.
- `proxy_pass http://backend_pool`: Encaminha a requisição para o balanceador de carga que definimos anteriormente.
- `proxy_set_header`: Passa headers corretos para o backend saber quem é o cliente real:
  - `Host`: Qual domínio o usuário acessou.
  - `X-Real-IP`: IP real do usuário final.
  - `X-Forwarded-For`: Cadeia de proxies que a requisição passou.
  - `X-Forwarded-Proto`: Diz ao backend se a conexão foi HTTP ou HTTPS.
- Timeouts de 30 segundos para conexão/envio/leitura.
- Desativa cache para respostas da API (nenhuma resposta da API fica armazenada em cache no Nginx).

---
```nginx
    location ~ ^/(auth/login|auth/registrar) {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://backend_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```
Regra ESPECÍFICA para as rotas sensíveis de login e cadastro:
- Aplica o limite rigoroso de 5 requisições POR MINUTO por IP contra brute force.
- Encaminha para o backend.

---
```nginx
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```
Regra para arquivos estáticos (imagens, css, js):
- Esses arquivos são servidos DIRETAMENTE pelo Nginx, sem passar pela aplicação, muito mais rápido!
- Define cache de 7 dias no navegador do usuário, assim eles não precisam baixar o mesmo arquivo toda hora.

---

## 🔒 Configuração HTTPS/SSL (`ssl-strong.conf`)
O arquivo já está pré-configurado e comentado. Para habilitar HTTPS em produção:
1.  Obtenha certificado SSL gratuito pelo Let's Encrypt com `certbot`.
2.  Descomente as linhas no arquivo `ssl-strong.conf`.
3.  Coloque os arquivos `fullchain.pem` e `privkey.pem` na pasta `nginx/ssl`.
4.  O Nginx automaticamente:
    - Usa apenas TLS 1.2 e 1.3 (versões antigas como SSLv3 estão desabilitadas por serem inseguras)
    - Usa apenas cifras de criptografia fortes
    - Habilita OCSP Stapling para verificar certificado mais rápido
    - Ativa HSTS por 1 ano, forçando o navegador a sempre usar HTTPS
    - Redireciona TODO tráfego HTTP para HTTPS automaticamente.

---

## 🚀 Como escalar horizontalmente (adicionar mais capacidade):
Se seu app crescer e precisar aguentar mais tráfego basta:
1.  No `docker-compose.yml`, aumente o valor de `replicas` do serviço backend para 3, 4, 5, etc...
2.  O Nginx automaticamente detecta as novas instâncias e começa a distribuir a carga entre elas sem nenhuma configuração extra.
3.  Se precisar de múltiplos servidores em máquinas diferentes, basta adicionar mais linhas `server ip_da_maquina:8000;` no bloco `upstream backend_pool`.

---

## 📊 Logs:
Todos os acessos ficam registrados:
- Logs de acesso: `/var/log/nginx/access.log` dentro do container Nginx
- Logs de erro: `/var/log/nginx/error.log`
- Você pode ver os logs em tempo real com:
  ```bash
  docker compose logs -f nginx
  ```

---

## ✅ O que essa configuração protege contra:
✅ Ataques DDoS de flood de requisições (bloqueia no limite de 30r/s)
✅ Ataques de brute force em login (5 tentativas por minuto)
✅ Acesso a arquivos sensíveis (.env, código fonte, banco de dados)
✅ Clickjacking por iframe
✅ Força bruta de conexões
✅ Sobrecarga do backend com muitas conexões simultâneas
✅ Versões antigas de TLS inseguras (quando SSL ativado)
