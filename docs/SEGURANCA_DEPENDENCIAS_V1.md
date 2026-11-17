# V1 — Auditoria de dependências: exceção temporária e rastreável

**Contexto:** PR #69, 17/11/2026, Expo SDK 58. A auditoria original
`npm audit --audit-level=moderate` falha apesar da suíte Python e dos
52 testes E2E aprovados. O alerta raiz é
[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)
(CVE-2026-112366), vulnerabilidade de ReDoS em `picomatch` (até 4.0.7).
Os **39 pacotes** reportados pelo npm representam o encadeamento dessa causa
única via Expo, Metro, React Native, Tailwind e dependências relacionadas.
Não são 39 vulnerabilidades independentes.

## Por que não fazemos npm audit fix --force

Na data da análise, a versão publicada mais recente do `picomatch` é
4.0.7 e o advisory não especifica versão corrigida. O npm propõe downgrades
incompatíveis (por exemplo, `expo@54` para um projeto SDK 58), ou troca
de major do Tailwind. Isso poderia quebrar app, Metro ou estilos sem
corrigir a causa de forma validada. **O problema de segurança permanece
aberto; exceção de CI NÃO é remediação da vulnerabilidade.**

## Controle temporário

Arquivo: `scripts/audit_npm_v1.cjs`.

- O pipeline continua executando `npm audit --json --audit-level=moderate`
  sobre **toda** a árvore, incluindo dependências de desenvolvimento.
- A exceção permite **somente** o identificador
  `GHSA-fc5q-39xc-vjpf`, **somente** no pacote raiz `picomatch`
  e apenas em severidade `high`.
- Para cada pacote listado, o verificador percorre recursivamente as
  dependências vulneráveis. Se qualquer caminho não terminar
  exclusivamente no advisory permitido, o CI **falha**.
- Uma nova vulnerabilidade direta, severidade diferente, falha de rede,
  saída JSON malformada, mudança inesperada nos metadados ou crescimento
  além dos **39 pacotes** resulta em **CI reprovado**.
- Exceção expira em **18/12/2026 00:00 UTC** e volta a bloquear a CI.
- A cada execução, o CI publica um **aviso visível** com o ID GHSA, a
  quantidade de pacotes e a data de expiração.
- `node scripts/audit_npm_v1.cjs --self-test` verifica casos positivos,
  novas vulnerabilidades, expiração, severidade inesperada e raiz ausente.
- Quando uma versão corrigida do `picomatch` for disponibilizada,
  atualizar dependências compatíveis, rodar `npm ci`, `npm audit`,
  `npm run check-deps`, `npm run typecheck`, Expo Doctor e Playwright,
  e **remover esta exceção** em um novo PR.

## Considerações para produção

O risco de ReDoS em globs arbitrários existe nas dependências. Até a
correção upstream, **não** permitir que padrões glob fornecidos pelo
usuário sejam processados por ferramentas CLI/Metro/Expo da aplicação.
A API FastAPI não deve passar entrada de usuário para scripts de build,
caminhos glob ou comandos de shell. Não é uma garantia de ausência de
exploração: a exceção requer revisão de segurança antes de deploy amplo.

Este controle **não altera permissões, lógica de pagamentos, fluxo de
reservas, o `main` nem a branch `develop/v2`**.
