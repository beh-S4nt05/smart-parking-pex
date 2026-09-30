export interface Sector {
  id: string;
  name: string;
  icon: string;
  total: number;
}

export interface Shopping {
  id: string;
  name: string;
  city: string;
  address: string;
  sectors: Sector[];
  avgStayMinutes: number;
}

export const shoppings: Shopping[] = [
  {
    id: "vista-verde",
    name: "Shopping Vista Verde",
    city: "São Paulo, SP",
    address: "Av. das Nações, 1200 - Centro",
    avgStayMinutes: 100,
    sectors: [
      { id: "entrada", name: "Entrada Principal", icon: "🚗", total: 40 },
      { id: "cinema", name: "Setor Cinema", icon: "🎬", total: 30 },
      { id: "alimentacao", name: "Praça de Alimentação", icon: "🍔", total: 25 },
      { id: "sul", name: "Torre Sul", icon: "🏢", total: 20 },
    ],
  },
  {
    id: "praia-mar",
    name: "Praia Mar Shopping",
    city: "Rio de Janeiro, RJ",
    address: "Av. Atlântica, 850 - Copacabana",
    avgStayMinutes: 85,
    sectors: [
      { id: "entrada", name: "Entrada Principal", icon: "🚗", total: 35 },
      { id: "cinema", name: "Setor Cinema", icon: "🎬", total: 22 },
      { id: "alimentacao", name: "Praça de Alimentação", icon: "🍔", total: 18 },
    ],
  },
  {
    id: "parque-das-arvores",
    name: "Parque das Árvores Mall",
    city: "Curitiba, PR",
    address: "Rua das Araucárias, 500 - Batel",
    avgStayMinutes: 120,
    sectors: [
      { id: "entrada", name: "Entrada Principal", icon: "🚗", total: 45 },
      { id: "cinema", name: "Setor Cinema", icon: "🎬", total: 28 },
      { id: "alimentacao", name: "Praça de Alimentação", icon: "🍔", total: 20 },
      { id: "leste", name: "Ala Leste", icon: "🏢", total: 15 },
    ],
  },
  {
    id: "horizonte-sul",
    name: "Horizonte Sul Shopping",
    city: "Porto Alegre, RS",
    address: "Av. Ipiranga, 3200 - Centro",
    avgStayMinutes: 95,
    sectors: [
      { id: "entrada", name: "Entrada Principal", icon: "🚗", total: 38 },
      { id: "cinema", name: "Setor Cinema", icon: "🎬", total: 24 },
      { id: "alimentacao", name: "Praça de Alimentação", icon: "🍔", total: 22 },
    ],
  },
];
