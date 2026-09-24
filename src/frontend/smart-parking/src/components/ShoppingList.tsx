import { Shopping } from "@/data/shoppings";

interface ShoppingListProps {
  shoppings: Shopping[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function ShoppingList({ shoppings, selectedId, onSelect }: ShoppingListProps) {
  return (
    <section id="shoppings" className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
      <div className="mb-8 text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Rede Credenciada</p>
        <h2 className="mt-1 text-2xl font-bold text-slate-900 sm:text-3xl">Shoppings Parceiros</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
          Escolha um shopping para visualizar o mapa de vagas atualizado em tempo real.
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {shoppings.map((s) => {
          const isActive = s.id === selectedId;
          const totalSpots = s.sectors.reduce((acc, sec) => acc + sec.total, 0);
          return (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`flex flex-col rounded-2xl border-2 p-5 text-left transition hover:-translate-y-1 hover:shadow-lg ${
                isActive ? "border-blue-500 bg-blue-50/50 shadow-md" : "border-slate-200 bg-white"
              }`}
            >
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-100 text-xl">
                🏬
              </div>
              <h3 className="font-bold text-slate-900">{s.name}</h3>
              <p className="mt-0.5 text-xs text-slate-500">{s.city}</p>
              <p className="mt-3 text-xs text-slate-400">{s.sectors.length} setores · {totalSpots} vagas</p>
              {isActive && (
                <span className="mt-3 inline-flex w-fit items-center gap-1 rounded-full bg-blue-600 px-3 py-1 text-[11px] font-bold text-white">
                  Selecionado
                </span>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}
