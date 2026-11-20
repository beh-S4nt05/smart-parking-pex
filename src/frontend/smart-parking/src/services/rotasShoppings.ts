/**
 * Destinos reais de shoppings de Manaus para "Como chegar" (V1).
 *
 * Endereços conferidos em sites oficiais dos shoppings e Prefeitura de Manaus;
 * URLs Maps Directions são GRATUITAS e NÃO exigem Maps JavaScript/Places API.
 * Não usar as coordenadas aproximadas do seed de 2026 como fonte da rota.
 *
 * Fontes e histórico de correção: src/docs/ROTAS_GOOGLE_MAPS_MANAUS.md
 */
import type { Estacionamento } from "../types/api";

type Local = Pick<Estacionamento, "nome" | "endereco" | "latitude" | "longitude">;

type DestinoConferido = {
  endereco: string;
  nomeGoogle: string;
  placeId?: string;
};

const DESTINOS_CONFERIDOS: Record<string, DestinoConferido> = {
  "Amazonas Shopping": {
    nomeGoogle: "Amazonas Shopping",
    endereco: "Av. Djalma Batista, 482 - Parque 10 de Novembro, Manaus - AM, Brasil",
  },
  "Manauara Shopping": {
    nomeGoogle: "Manauara Shopping",
    endereco: "Av. Mário Ypiranga Monteiro, 1300 - Adrianópolis, Manaus - AM, Brasil",
  },
  "Sumaúma Park Shopping": {
    nomeGoogle: "Sumaúma Park Shopping",
    endereco: "Av. Noel Nutels, 1762 - Cidade Nova, Manaus - AM, Brasil",
  },
  "Ponta Negra Shopping": {
    nomeGoogle: "Shopping Ponta Negra",
    endereco: "Av. Coronel Teixeira, 5705 - Ponta Negra, Manaus - AM, Brasil",
  },
  "Millennium Shopping": {
    nomeGoogle: "Millennium Shopping",
    endereco: "Av. Djalma Batista, 1661 - Chapada, Manaus - AM, Brasil",
  },
  "Studio 5 Festival Mall": {
    nomeGoogle: "Studio 5 Shopping e Convenções",
    endereco: "Av. Rodrigo Otávio, 3555 - Distrito Industrial, Manaus - AM, Brasil",
  },
  "Shopping Manaus ViaNorte": {
    nomeGoogle: "Shopping Manaus ViaNorte",
    endereco: "Av. Arquiteto José Henrique Bento Rodrigues, 3541 - Santa Etelvina, Manaus - AM, Brasil",
    placeId: "ChIJU52AdrUZbJIR185TfEOjAHQ",
  },
  "Shopping Phelippe Daou": {
    nomeGoogle: "Shopping Phelippe Daou",
    endereco: "Av. Camapuã, 2939 - Cidade de Deus, Manaus - AM, Brasil",
    placeId: "ChIJoeLmfRgbbJIRbKks8mB_OCs",
  },
};

// Cadastro demo antigo tinha o nome genérico "Shopping Norte" e coordenadas
// incompatíveis com o ViaNorte. Substituição explícita APENAS para esse seed
// legado; o script de migração apresenta dry-run e não reescreve outros shoppings.
const ALIASES_SEED_LEGADO: Record<string, string> = {
  "Shopping Norte": "Shopping Manaus ViaNorte",
};

export function destinoConferidoManaus(nome: string): DestinoConferido | null {
  const chave = ALIASES_SEED_LEGADO[nome.trim()] ?? nome.trim();
  return DESTINOS_CONFERIDOS[chave] ?? null;
}

function coordenadasValidas(latitude?: number | null, longitude?: number | null): boolean {
  // Recorte geográfico amplo de Manaus; rejeita NaN/0/coordenadas de outra cidade.
  return (
    typeof latitude === "number" &&
    typeof longitude === "number" &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -3.4 &&
    latitude <= -2.6 &&
    longitude >= -60.5 &&
    longitude <= -59.5
  );
}

/**
 * Abre a tela de ROTAS do Google Maps, deixando o ponto de partida a cargo
 * do Google Maps/permissão de localização do usuário. Sem custo de API.
 *
 * Para os 8 shoppings conhecidos sempre prevalece o endereço VERIFICADO;
 * coordenadas aproximadas e endereços antigos do banco não entram no link.
 * Para estabelecimentos cadastrados pelo administrador fora desse conjunto,
 * usa coordenadas fornecidas por ele se forem válidas, ou nome + endereço.
 */
export function urlComoChegar(shopping: Local | null | undefined): string | null {
  if (!shopping) return null;
  const conhecido = destinoConferidoManaus(shopping.nome || "");
  let destino: string;
  let placeId: string | undefined;
  if (conhecido) {
    destino = `${conhecido.nomeGoogle}, ${conhecido.endereco}`;
    placeId = conhecido.placeId;
  } else if (coordenadasValidas(shopping.latitude, shopping.longitude)) {
    destino = `${shopping.latitude},${shopping.longitude}`;
  } else if (shopping.endereco?.trim()) {
    destino = `${shopping.nome?.trim() || "Estacionamento"}, ${shopping.endereco.trim()}, Brasil`;
  } else {
    return null;
  }

  let url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destino)}&travelmode=driving&dir_action=navigate`;
  if (placeId) url += `&destination_place_id=${encodeURIComponent(placeId)}`;
  return url;
}
