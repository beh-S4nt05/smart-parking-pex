# Smart Parking — HTTP/2 do Nginx: correção, diagnóstico e limites

## Qual servidor realmente suporta HTTP/2?

| Camada | Origem da configuração | Protocolo |
|---|---|---|
| Desenvolvimento local `localhost:8080` | `src/nginx/default.conf` / `src/docker-compose.yml` | HTTP/1.1, claro; **sem TLS/HTTP2** |
| Nginx → FastAPI | `proxy_pass http://backend_smartparking` | HTTP/1.1 na rede interna |
| Piloto gratuito (até 14 dias) | `src/docker-compose.piloto.yml` | **Sem Nginx**; FastAPI em `127.0.0.1:18000` |
| Piloto pela internet | Tailscale Funnel → FastAPI | HTTPS/TLS no Funnel; HTTP/2 sujeito à negociação ALPN do edge |
| Aplicação web | Cloudflare Pages | HTTPS/HTTP/2/3 disponibilizado pela plataforma |

**Não configure TLS/HTTP2 na porta 80 do container local**, não aponte
`proxy_pass https://backend:8000` para um FastAPI HTTP simples e não
abra a porta do PostgreSQL para tentar corrigir erros de protocolo.

## Diferencie o problema pela mensagem

**`nginx: [warn] the "listen ... http2" directive is deprecated`:**
desde Nginx 1.25.1, substitua:
```nginx
# configuração antiga (apenas ilustração):
# listen 443 ssl http2;

listen 443 ssl;
http2 on;
```
Apenas em um **server com TLS, certificado e chave válidos**. O warning
sozinho não prova falha de requisição nem crash.

**`ERR_HTTP2_PROTOCOL_ERROR` no navegador:** é um sintoma, não um
diagnóstico. Teste o mesmo hostname por HTTP/1.1 e por HTTP/2 e confira
a camada que negociou TLS. Proxy/CDN, headers inválidos, truncamento,
configuração remota e certificados podem causar erros semelhantes.
Não presuma que o processo Nginx do projeto é o responsável.

**`nginx -t` falha:** confira as linhas exatas do erro. Se o log citar
`unknown directive "http2"`, confirme a versão compilada (`nginx -v` e
`nginx -V`): `http2 on;` existe desde 1.25.1 e requer suporte ao módulo.
Se citar `cannot load certificate`, configure cert/key antes de ativar
a seção HTTPS. Se `host not found in upstream "backend"`, execute
no Docker network em que o nome `backend` é resolvido.

## Diagnóstico seguro no Linux (não altera containers)

Na raiz do repositório:
```bash
bash scripts/diagnosticar_nginx_http2.sh

# Opcional: hostname público REAL, sem https:// nem /rotas
bash scripts/diagnosticar_nginx_http2.sh nome-real.tailnet.ts.net
```
O script verifica o Nginx local via Compose, executa `nginx -t`,
confere HTTP/1.1 do backend local e, caso tenha sido informado um
hostname, verifica o HTTPS com `curl --http2`. Não executa `restart`,
`down`, `up` ou `reload`; não imprime `.env`.

Caso o problema esteja num **Nginx instalado no host**, fora do Docker:
```bash
sudo nginx -t
nginx -v
sudo systemctl status nginx --no-pager
```
Esses comandos são somente leitura. Não aplique mudanças no serviço
do host sem confirmar qual configuração ativa possui a diretiva.

## HTTP/2 direto no Nginx — opt-in, fora do piloto Tailscale

Existe `src/nginx/https.conf.example`: template **não carregado** pelo
Dockerfile. Ele demonstra `listen 443 ssl;`, `http2 on;`, TLS 1.2/1.3
e proxy HTTP/1.1 para FastAPI. Para utilizá-lo no futuro, é preciso:

- apontar `server_name` para o domínio real, com DNS e certificado válido;
- montar `https.conf.example` como um arquivo **.conf** em `conf.d`;
- montar `fullchain.pem` e `privkey.pem` como somente leitura;
- expor a porta TLS desejada **somente quando apropriado**, com firewall e
  revisão das regras de segurança;
- validar `nginx -t` antes de qualquer reload.

Nunca inclua certificados privados ou chaves TLS no GitHub.

## Como o CI impede regressão?

O job `Nginx HTTP origin e HTTPS HTTP2 (ALPN)` constrói a imagem real,
sobe um backend **fictício e efêmero**, valida `nginx -t`, confirma
que a porta 80 responde HTTP/1.1 e gera um certificado autoassinado
temporário para testar a negociação HTTP/2 via ALPN na porta 443
**somente no runner descartável do GitHub**. Não expõe a produção,
não conecta ao banco e não substitui o teste no Tailscale real.

## Referências técnicas

- https://nginx.org/en/docs/http/ngx_http_v2_module.html
- https://mailman.nginx.org/pipermail/nginx-announce/2023/BYSVLPUZESCZHJMTDD25QD7ZKZYADAR2.html
- https://tailscale.com/docs/features/tailscale-funnel
