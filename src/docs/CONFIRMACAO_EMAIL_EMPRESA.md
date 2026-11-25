# Smart Parking — Confirmação de e-mail pelo endereço da empresa

## Objetivo

O remetente é uma caixa postal ou domínio legitimamente autorizado da empresa
(ex.: `Smart Parking <naoresponda@seudominio.com.br>`). O e-mail do usuário não
é considerado verificado só porque tem formato válido. A mensagem sai do
**backend FastAPI**, nunca diretamente do Web/Android/iOS.

Fluxo: cadastro -> conta criada pendente -> código numérico de 6 dígitos ->
e-mail por SMTP -> confirmação em /confirmar-email -> login liberado.

## Servidor SMTP e DNS

1. Usar SMTP autenticado do serviço de e-mail da empresa (ou serviço
   transacional com domínio verificado). Para envio com domínio próprio,
   configurar SPF, DKIM e DMARC conforme as instruções do provedor.
2. Armazenar no **src/.env.piloto** privado, sem commits:
   ```dotenv
   SMTP_HOST=smtp.provedor.com
   SMTP_PORT=587
   SMTP_USER=usuario-smtp
   SMTP_PASSWORD=credencial-smtp-privada
   SMTP_SENDER=Smart Parking <naoresponda@seudominio.com.br>
   SMTP_STARTTLS=true
   SECURITY_VERIFIED_EMAIL_REQUIRED=true
   ```
3. Não disponibilizar SMTP_PASSWORD no bundle Expo, EXPO_PUBLIC_*, repositório
   público, PDF, banner, captura, formulário ou console da aplicação.
   Credencial específica de aplicativo/SMTP deve ser diferente da senha
   principal da caixa postal. Verificar domínio e remetente autorizados.
4. No piloto, `src/docker-compose.piloto.yml` injeta as variáveis no **backend**.
   O valor padrão da flag de confirmação continua **false**, até o serviço
   SMTP estar operacional e o banco migrado.

## Banco e deploy

Fazer backup do PostgreSQL antes de aplicar qualquer migração.

Na raiz do repositório:

```bash
docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
  run --rm backend alembic upgrade head

docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
  up -d --build backend
```

A migração `f067b001a1c0` adiciona contagem de tentativas aos desafios
e marca `email_confirmacao_obrigatoria` apenas nos novos cadastros. Contas
antigas não são bloqueadas retroativamente, porque a feira depende de contas
legadas e de demonstração. Nunca editar `email_verificado_em` manualmente
para contas reais.

## Segurança e experiência

- Código de 6 dígitos por CSPRNG; só o HMAC fica no banco.
- Prazo de 10 min, 5 erros no máximo por desafio, consumo único.
- Solicitação/reenvio limitado pelo IP e por intervalo de 60 segundos
  entre desafios ativos do mesmo usuário.
- Código novo invalida desafios anteriores depois do envio bem-sucedido.
- Respostas públicas de solicitação não revelam a existência de um e-mail.
- Se SMTP não estiver configurado e a flag estiver ligada, novo cadastro
  retorna 503 sem criar conta inutilizável.
- Se SMTP falhar após a criação, a conta fica pendente e o usuário pode
  reenviar sem tentar cadastrar novamente.
- Reciclagem/renovação de refresh token não permite contornar a verificação.
- Recuperação de senha conserva token forte de uso único e prazo de 15 min.
- Confirmação de e-mail **não** comprova identidade civil, nem valida CPF,
  credencial PCD/idoso ou titularidade de veículo.
- Uma solicitação SMTP bem-sucedida comprova o envio ao servidor SMTP, não
  garante chegada à caixa de entrada. Fazer teste real de entrega e spam.

## Validação antes da feira

1. Cadastrar e-mail real controlado pela equipe.
2. Conferir remetente, SPF/DKIM, caixa de entrada e spam.
3. Tentar login antes da confirmação: deve falhar.
4. Inserir código errado 5 vezes, confirmar o bloqueio do desafio.
5. Solicitar novo código depois de 60 s, validar prazo de 10 min e uso único.
6. Confirmar o e-mail e autenticar em Web/Android/iOS.
7. Verificar que contas antigas e os dados do piloto continuam funcionais.

Para tests automáticos, o envio é simulado com monkeypatch no pytest, sem
acesso externo ao provedor. Os testes não substituem homologação SMTP real.
