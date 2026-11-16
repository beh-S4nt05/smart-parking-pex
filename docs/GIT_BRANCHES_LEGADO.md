# Auditoria e plano de limpeza das branches — Smart Parking

Data da auditoria: 16/11/2026. Repositório: `beh-S4nt05/smart-parking-pex`.

## Política de branches

- `main`: versão V1 funcional e correções revisadas; protegida conceitualmente.
- `develop/v2`: desenvolvimento da V2; criada diretamente a partir da `main` commit `707a1137c424bb8ca020133ef8acfb43e1db344f`.
- Demais refs de branch: candidatas à remoção **após arquivamento** das versões divergentes e verificação de HEADs.

## Resultado da auditoria

- **35 branches** remotas identificadas: `main` + 34 antigas, antes de criar `develop/v2`.
- **22 branches** com `ahead_by=0`, ancestrais já contidos na `main`; não precisam de merge.
- **12 branches** divergentes com commits únicos, algumas com diferenças de código; **não realizar merge indiscriminado** porque podem substituir comportamento da V1 estabilizada.
- Nenhum PR aberto na verificação do endpoint `GET /pulls?state=open`.
- PRs **#66 e #68 já mesclados** na `main`, incluindo correção do HTTP 500 de data/timezone no simulador.
- Os commits divergentes devem ser preservados por **tags imutáveis de arquivamento** antes da remoção das branches, mesmo quando o diff final de código é nulo.

## Inventário congelado da auditoria

| Branch antiga | SHA de referência | Ahead main | Behind main | Classificação |
|---|---|---:|---:|---|
| `arena/acf78b1a-smart-parking-pex` | [`c453ba63d465`](https://github.com/beh-S4nt05/smart-parking-pex/commit/c453ba63d46561f324d12c08853f17c725ace76c) | 0 | 216 | já ancestral da main |
| `arena/db7d0055-smart-parking-pex` | [`07329c5618be`](https://github.com/beh-S4nt05/smart-parking-pex/commit/07329c5618be3b8ab32eda1c543ec3d9a98bdb71) | 0 | 177 | já ancestral da main |
| `arena/e79f62a3-smart-parking-pex` | [`cd390cb7b223`](https://github.com/beh-S4nt05/smart-parking-pex/commit/cd390cb7b22353e3e387daa6b26675895be34b1a) | 0 | 211 | já ancestral da main |
| `arena/e120c38b-smart-parking-pex` | [`c6308825ca7d`](https://github.com/beh-S4nt05/smart-parking-pex/commit/c6308825ca7df23653abb5430f1dd6f77eaa214b) | 0 | 175 | já ancestral da main |
| `arena/fab11479-smart-parking-pex` | [`bc30b755f180`](https://github.com/beh-S4nt05/smart-parking-pex/commit/bc30b755f180e9af7b4891abda279a6e1336381e) | 0 | 183 | já ancestral da main |
| `arena/1d7ed9f2-smart-parking-pex` | [`7848ed93a984`](https://github.com/beh-S4nt05/smart-parking-pex/commit/7848ed93a9841958e66173860f281d362c12905a) | 0 | 185 | já ancestral da main |
| `arena/11a57e13-smart-parking-pex` | [`e93a1b615901`](https://github.com/beh-S4nt05/smart-parking-pex/commit/e93a1b6159015cb04b1bcf18c345b6229251eda1) | 0 | 214 | já ancestral da main |
| `arena/83cd58bc-smart-parking-pex` | [`fbe0f879e828`](https://github.com/beh-S4nt05/smart-parking-pex/commit/fbe0f879e828652588cad337897c7521dfd4be8d) | 0 | 219 | já ancestral da main |
| `arena/992f9160-smart-parking-pex` | [`2c04f016ba82`](https://github.com/beh-S4nt05/smart-parking-pex/commit/2c04f016ba82cc0a87edd3cf9869767b28aa5610) | 0 | 181 | já ancestral da main |
| `arena/03867a8c-smart-parking-pex` | [`cd72220a7345`](https://github.com/beh-S4nt05/smart-parking-pex/commit/cd72220a7345932f544ad8cb8d25a7e885d3998e) | 0 | 179 | já ancestral da main |
| `arena/71109ddc-smart-parking-pex` | [`9b050dc889ac`](https://github.com/beh-S4nt05/smart-parking-pex/commit/9b050dc889ac95736e142f32f5640c73e4802453) | 0 | 226 | já ancestral da main |
| `automation/expo-sdk-update` | [`d090db39cd98`](https://github.com/beh-S4nt05/smart-parking-pex/commit/d090db39cd9821df3a7161f6b0dcaf595a801e5d) | 1 | 4 | divergente / arquivar tag |
| `codex/center-panel-link` | [`c5a8b759b1f8`](https://github.com/beh-S4nt05/smart-parking-pex/commit/c5a8b759b1f82a53b38e397fdf62a8668bbe6970) | 2 | 176 | divergente / arquivar tag |
| `codex/frontend-responsive-layout` | [`c34162aa1719`](https://github.com/beh-S4nt05/smart-parking-pex/commit/c34162aa1719666b3b4513e5fae1b6f92210a6f9) | 0 | 190 | já ancestral da main |
| `codex/restore-parking-access-and-register-exit` | [`9bef533e0a36`](https://github.com/beh-S4nt05/smart-parking-pex/commit/9bef533e0a363e82d62bbbbad1514e434eb62c14) | 8 | 173 | divergente / arquivar tag |
| `codex/role-matrix-shopping-finance-driver` | [`21056a306292`](https://github.com/beh-S4nt05/smart-parking-pex/commit/21056a306292092edae155374c1945756e4dcacf) | 7 | 172 | divergente / arquivar tag |
| `codex/ux-flow-rebuild` | [`0dd8ade96b77`](https://github.com/beh-S4nt05/smart-parking-pex/commit/0dd8ade96b777b3e250289ed59a7c50896a8c0fa) | 13 | 186 | divergente / arquivar tag |
| `docs/scope-driver-vehicle-eligibility` | [`5e90d25eb057`](https://github.com/beh-S4nt05/smart-parking-pex/commit/5e90d25eb057e1b9f4f954074c05dc30929fd569) | 0 | 121 | já ancestral da main |
| `feat/mobile-premium-presentation` | [`c468efa9ae64`](https://github.com/beh-S4nt05/smart-parking-pex/commit/c468efa9ae64cf79caf42a2a335f9ddd484202dc) | 0 | 146 | já ancestral da main |
| `feat/v1-multi-vehicle-management` | [`21e373ef8dc3`](https://github.com/beh-S4nt05/smart-parking-pex/commit/21e373ef8dc327ffae7a9c79eb650031f106e1ce) | 0 | 56 | já ancestral da main |
| `feat/v1-registration-vehicle-benefits` | [`cfd2a494882a`](https://github.com/beh-S4nt05/smart-parking-pex/commit/cfd2a494882a76b8b4b58bc124797f8c32edebbd) | 13 | 73 | divergente / arquivar tag |
| `feat/v1-vehicles-credentials-db` | [`b2421cac6999`](https://github.com/beh-S4nt05/smart-parking-pex/commit/b2421cac6999ba27272720302552dcc80d585c58) | 0 | 55 | já ancestral da main |
| `fix/mobile-auth-web-hero-layout` | [`cc042e187008`](https://github.com/beh-S4nt05/smart-parking-pex/commit/cc042e187008bae52b7ea357c03e5fa1cde55894) | 0 | 126 | já ancestral da main |
| `fix/mobile-consistency-web-hero` | [`59001b7f0b05`](https://github.com/beh-S4nt05/smart-parking-pex/commit/59001b7f0b0504a757bd678d25f194a8d0c01387) | 0 | 132 | já ancestral da main |
| `fix/mobile-scroll-reserva-bordas` | [`0889fd3a9e8f`](https://github.com/beh-S4nt05/smart-parking-pex/commit/0889fd3a9e8f67ff2ec67de83bd807aa5f54f760) | 2 | 156 | divergente / arquivar tag |
| `fix/simulador-lote-timezone-500` | [`106bb1e2d3c3`](https://github.com/beh-S4nt05/smart-parking-pex/commit/106bb1e2d3c30d04cac4e64da0c2a674e58e9951) | 0 | 29 | já ancestral da main |
| `fix/simulador-qr-http-500` | [`106bb1e2d3c3`](https://github.com/beh-S4nt05/smart-parking-pex/commit/106bb1e2d3c30d04cac4e64da0c2a674e58e9951) | 0 | 29 | já ancestral da main |
| `fix/v1-login-registered-users-shared-phone` | [`19ba4c796edd`](https://github.com/beh-S4nt05/smart-parking-pex/commit/19ba4c796edd1fd35304bae672af0c2a7f64f41f) | 0 | 51 | já ancestral da main |
| `security/v1-60-identity-mfa` | [`8d87d996985d`](https://github.com/beh-S4nt05/smart-parking-pex/commit/8d87d996985d61656b64049c63af2913eb8da500) | 1 | 24 | divergente / arquivar tag |
| `security/v1-61-sessions` | [`eef50348a162`](https://github.com/beh-S4nt05/smart-parking-pex/commit/eef50348a1629101ca70834219cb0d3a862a0fe3) | 1 | 20 | divergente / arquivar tag |
| `security/v1-62-rbac-scope` | [`d0b47837aa56`](https://github.com/beh-S4nt05/smart-parking-pex/commit/d0b47837aa5671b6b044db7d13b0e869d24b0a39) | 0 | 10 | já ancestral da main |
| `security/v1-63-sensor-integrity` | [`d60f6b05c57f`](https://github.com/beh-S4nt05/smart-parking-pex/commit/d60f6b05c57f5298915bce964b05b5c2533cd2fc) | 8 | 13 | divergente / arquivar tag |
| `security/v1-64-pilot-hardening` | [`67e81e3c6621`](https://github.com/beh-S4nt05/smart-parking-pex/commit/67e81e3c6621d5bde92a573448e6251375db3d13) | 17 | 15 | divergente / arquivar tag |
| `security/v1-65-audit-incidents` | [`0bd68eab1c42`](https://github.com/beh-S4nt05/smart-parking-pex/commit/0bd68eab1c42dd04de94c98bcb5c7a3ab092fa9b) | 14 | 15 | divergente / arquivar tag |

## Mudanças exclusivas que merecem referência para a V2

- `automation/expo-sdk-update`: alteração de `package.json` para Expo (avaliar versões antes de reutilizar).
- `codex/center-panel-link`: mudanças no `Header.tsx`.
- `codex/restore-parking-access-and-register-exit` e `codex/role-matrix-shopping-finance-driver`: controle de acesso, cadastro, dashboards e testes; **revisar contra a V1 atual antes de portar**.
- `codex/ux-flow-rebuild`, `fix/mobile-scroll-reserva-bordas`: fluxos e layout anteriores; a UI V1 atual foi aprovada, então não substituir sem revisão.
- `feat/v1-registration-vehicle-benefits`: cadastro, elegibilidade, reserva e credenciais; comparar funcionalidades da V1, pois a branch divergiu.
- `security/v1-60-identity-mfa` e `security/v1-61-sessions`: commits exclusivos, mas **sem diferença líquida de arquivos** na comparação com main.
- `security/v1-63-sensor-integrity`, `security/v1-64-pilot-hardening` e `security/v1-65-audit-incidents`: itens de segurança/auditoria que devem ser reavaliados por função antes de aplicar à V2.

## Execução segura da limpeza

O script `scripts/limpar-branches-legadas.sh` começa em modo simulação. Em modo `--apply`, verifica `gh auth`, PRs abertos, nomes de branches e SHAs congeladas, cria tags `archive/2026-11-16/<nome-antigo>` para as 12 divergentes e **só depois** exclui as 34 antigas. Para cada ref, verifica novamente SHA antes da exclusão. Abortará se houver divergência, PR aberto ou permissão insuficiente.

**A criação deste documento não implica que as exclusões tenham sido executadas.**
