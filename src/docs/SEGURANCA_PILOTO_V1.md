# Segurança do piloto Smart Parking — Android (sideload) e Web

> PR #64 (draft). **Não** converte a aplicação em serviço pronto para internet.
> Não substitui autorização no FastAPI por HMAC, User-Agent, origem CORS ou attestation.

## 1. Controles efetivos

- **Identidade e papéis:** o FastAPI verifica JWT, sessão, RBAC e escopo por estacionamento em todas as escritas sensíveis. Cliente não possui papel administrativo por configuração local.
- **Android de testes:** APK interno e aparelhos sem Google Play Services continuam suportados. **Play Integrity não está integrado neste PR**: não confiar em headers `X-Client-Type`, HMAC armazenado no bundle nem em alegação de origem do aplicativo.
- **Web:** navegadores comuns têm acesso à vitrine pública. Não há atestado de navegador oficial. Para reservas/administração, o servidor aplica autenticação e autorização independentes do cliente.
- **IoT:** chave individual revogável; eventos por sequência monotônica e escopo do estacionamento. Nenhuma chave de sensor deve ser incorporada ao app público.

## 2. Docker — portas e credenciais

O Compose faz bind de **PostgreSQL somente em 127.0.0.1:5432** e **pgAdmin somente em 127.0.0.1:5050** por padrão. Isso mantém conexão local do operador e impede exposição direta pela interface de rede. O backend segue na porta 8000 do host para permitir testes reais com Android na rede. Nginx pode permanecer na porta 8080.

Em **host Linux**, configure um firewall que permita acesso à API/Nginx **apenas a IPs ou rede de teste aprovados**, bloqueando acesso de redes externas. O bind Docker em 0.0.0.0 do backend é intencional e **não constitui proteção**.

Antes de ativar modo protegido:

1. Faça backup e confirme restauração do PostgreSQL. **Nunca** use `docker compose down -v`.
2. Revise e altere senhas e segredos de demonstração; remova qualquer admin demo já existente **somente após provisionar e testar outro administrador**. Ativar o modo protegido **não apaga nem troca** credenciais antigas.
3. Configure as variáveis de ambiente somente no host ou gestor de segredos, nunca em `EXPO_PUBLIC_*`:
   - `SECRET_KEY`: valor aleatório exclusivo, >=32 bytes;
   - `POSTGRES_PASSWORD`: 12+ caracteres, não `postgres`;
   - `PGADMIN_DEFAULT_PASSWORD`: exclusiva; confirme estado do volume persistente;
   - `SECURITY_PILOT_HARDENED=true`.
4. Para **volume PostgreSQL existente**, alterar `POSTGRES_PASSWORD` no Compose **não altera** a senha gravada no cluster. Alterar a credencial PostgreSQL no banco via procedimento administrado, em conjunto com a variável do serviço, evitando interromper o piloto.
5. Suba com `docker compose -f src/docker-compose.yml config` e confirme portas/endpoints. Nunca publique PostgreSQL/pgAdmin na internet.

## 3. Modo protegido de piloto

`SECURITY_PILOT_HARDENED=true` valida segredos no boot e **impede criar uma conta admin com senha `admin123` automaticamente**. Não exige Play Integrity em celulares que não o suportam e não transforma staging em produção. O acesso administrativo válido continua exigindo MFA conforme implantação dos PRs #60–61.

`ENVIRONMENT=production` **não deve ser usado sem HTTPS, domínio, CORS restrito, certificados e provisionamento seguro**. O middleware HMAC anterior pode permanecer como mecanismo auxiliar anti-replay, mas como o mesmo segredo está acessível no bundle do cliente ele **não é prova de aplicativo oficial**. Em produção sua política deve ser revista antes da liberação pública.

## 4. Checklist de implantação

- [ ] Backup testado, migrações Alembic aplicadas em ordem (#60, #61, #63 e #65)
- [ ] Admin legítimo e MFA provisionado antes de ativar bloqueio obrigatório
- [ ] HTTPS para qualquer acesso fora da LAN controlada
- [ ] PostgreSQL/pgAdmin inacessíveis a partir de outro dispositivo da rede
- [ ] API permitida apenas à rede de teste por firewall; verificada usando Android real
- [ ] Não há credenciais demo ainda válidas no banco
- [ ] Usuários legítimos Android sem Google continuam reservando após autenticação
- [ ] Web pública permanece navegável sem autenticação; ações críticas bloqueadas no servidor
- [ ] CI e testes negativos de RBAC e sensores confirmados

## 5. Pendência Play Integrity e requisitos de produção

A integração de Play Integrity **não foi criada nesta etapa**: exige decisão sobre distribuição, configuração do projeto Google/Play e verificação criptográfica no servidor de nonces e payloads. A V1 em sideload deve continuar com fluxo alternativo e autenticação no backend. Nenhum placeholder de header poderá ser usado para bloquear/simular uma verificação.

Este PR é uma melhoria de **configuração de piloto**, não uma aprovação de produção pública.
