# Smart Parking V1 — Como chegar aos shoppings reais de Manaus

## Problema constatado

O botão antigo ficava apenas na versão web e abria `https://www.google.com/maps/search/?api=1&query=...`, não a rota. Ele priorizava coordenadas **aproximadas** do `seed_demo.py`, várias incompatíveis com as localizações reais. A versão Android não tinha esse botão na tela do mapa.

## Solução sem custo de API

- Botão "Como chegar" compartilhado entre a tela web e o aplicativo Android/iOS.
- Abre `https://www.google.com/maps/dir/?api=1&destination=...&travelmode=driving&dir_action=navigate`.
- Não define `origin`: o próprio Google Maps utiliza a localização do aparelho **se o usuário permitir**; quando não disponível, solicita origem ao usuário.
- **Google Maps URLs são gratuitos e não precisam de chave de API**. Não confundir com Maps JavaScript API, Directions API, Places API ou mapas embutidos de uso faturável.
- Para os oito shoppings reconhecidos, o destino é sempre o **nome oficial + endereço conferido**, com Place ID somente quando este dado foi efetivamente localizado. As antigas coordenadas do banco nunca prevalecem sobre o destino confirmado.
- Estacionamentos personalizados de administração usam coordenadas válidas em Manaus ou seu próprio endereço cadastrado; não são convertidos automaticamente para um shopping conhecido.
- O Google Maps escolhe a rota e solicita as permissões necessárias. O link aponta ao **empreendimento**, não necessariamente à cancela específica de entrada de veículos (não afirmamos que a portaria do estacionamento foi validada em campo).

## Endereços conferidos

| Registro da V1 | Destino utilizado no Google Maps | Referência consultada |
|---|---|---|
| Amazonas Shopping | Av. Djalma Batista, 482, Parque 10 de Novembro, Manaus-AM | [Site oficial — Como chegar](https://amazonasshopping.com.br/como-chegar/) |
| Manauara Shopping | Av. Mário Ypiranga Monteiro, 1300, Adrianópolis, Manaus-AM | [Site oficial — Como chegar](https://manauarashopping.com.br/como-chegar/) |
| Sumaúma Park Shopping | Av. Noel Nutels, 1762, Cidade Nova, Manaus-AM | [Site oficial — Estacionamento](https://sumaumaparkshopping.com.br/estacionamento/) |
| Ponta Negra Shopping | Av. Coronel Teixeira, 5705, Ponta Negra, Manaus-AM | [Site oficial — Comodidades](https://www.shoppingpontanegra.com.br/comodidades/3/loteria) |
| Millennium Shopping | Av. Djalma Batista, 1661, Chapada, Manaus-AM | [Site oficial](https://www.millenniumshopping.com.br/) |
| Studio 5 Festival Mall | Av. Rodrigo Otávio, 3555, Distrito Industrial, Manaus-AM | [Site oficial — Contato](https://www.studio5.com.br/contato) |
| **Shopping Manaus ViaNorte** | Av. Arquiteto José Henrique Bento Rodrigues, 3541, Santa Etelvina, Manaus-AM | [Site oficial](https://www.shoppingmanausvianorte.com.br/) |
| Shopping Phelippe Daou | Av. Camapuã, 2939, Cidade de Deus, Manaus-AM | [Prefeitura de Manaus](https://www.manaus.am.gov.br/semcom/pautas/prefeitura-campanha-sorteio-galerias/) |

**Correção importante no seed:** a entrada genérica `Shopping Norte` estava associada ao endereço `Av. Camapuã, 1480`, não correspondente ao ViaNorte. Para manter oito **shoppings reais** no ambiente de demonstração, ela foi substituída no seed NOVO pelo empreendimento verificável **Shopping Manaus ViaNorte**; não declaramos que eram o mesmo empreendimento. No frontend, o alias legado `Shopping Norte` permite abrir o destino corrigido mesmo sem alterar imediatamente o banco. Os demais cadastros não são afetados.

Não foram encontrados conjuntos completos e inequívocos de **coordenadas do portão de entrada de veículos** fornecidos por todos os shoppings. Por isso as antigas latitudes/longitudes aproximadas do seed novo foram trocadas por `None` e o Google Maps resolve o lugar a partir de nome/endereço, em vez de fingir precisão GPS.

## Banco de dados antigo: migração opt-in

**O GitHub não altera os dados que já existem no Docker/PostgreSQL.** O novo seed vale para instalação limpa. Para atualizar apenas as oito linhas históricas do seed anterior, o script abaixo tem _dry-run_ por padrão e **só atua em registros cujo nome, endereço e coordenadas combinam com o seed original**. Alterações de administradores, endereços novos e dados de outros shoppings permanecem intocados. Não altera reservas, histórico nem permissões.

1. Faça um backup do banco PRIMEIRO (com o piloto em funcionamento, na raiz do repo):
   ```bash
   docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
     exec -T postgres pg_dump -U smartparking_piloto smartparking_piloto \
     > backup-smartparking-localizacoes.sql
   ```
   Guarde o arquivo apenas localmente, com acesso restrito; pode conter dados pessoais de teste.
2. Execute o teste de alterações, sem gravar:
   ```bash
   docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
     exec backend python piloto_corrigir_localizacoes.py
   ```
3. Confira a relação exibida e aplique explicitamente:
   ```bash
   docker compose --env-file src/.env.piloto -f src/docker-compose.piloto.yml \
     exec backend python piloto_corrigir_localizacoes.py --apply
   ```
4. Reabra o site/app e confira nome, endereço e link Google Maps para cada shopping. Não rode `seed_demo.py --reset`: ele remove dados demonstrativos existentes.

## Testes

- Playwright verifica os oito URLs, `/maps/dir/`, `api=1`, modo `driving`, preservação de nomes/endereços, alias legado e rejeição de coordenadas inválidas.
- Pytest verifica endereços e GPS não inventado no novo seed, dry-run, aplicação idempotente e preservação de um endereço personalizado.
- Após o merge: teste **no Android físico** com rede 4G a abertura do Google Maps, seleção da origem e navegação. Não é possível confirmar em CI o destino visual/porta exata escolhida pelo Maps.

## Fontes técnicas

- [Google Maps URLs — documentação oficial](https://developers.google.com/maps/documentation/urls/get-started)
- [Google Maps URLs — referência rápida](https://developers.google.com/maps/documentation/urls/quick-reference)
