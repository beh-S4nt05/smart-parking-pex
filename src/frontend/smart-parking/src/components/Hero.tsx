import { Shopping } from "../data/shoppings";

interface HeroProps {
  shoppings: Shopping[];
  selectedId: string;
  onSelect: (id: string) => void;
  onSearch: () => void;
}

export default function Hero({ shoppings, selectedId, onSelect, onSearch }: HeroProps) {
  return (
    <section id="inicio" className="relative overflow-hidden bg-gradient-to-b from-blue-50 via-blue-50/60 to-white">
      <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-blue-200/40 blur-3xl" />
      <div className="pointer-events-none absolute top-10 -right-16 h-72 w-72 rounded-full bg-indigo-200/40 blur-3xl" />

      <div className="relative mx-auto max-w-4xl px-4 py-16 text-center sm:px-6 sm:py-24 lg:px-8">
        <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-blue-700 shadow-sm ring-1 ring-blue-100">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          Monitoramento em tempo real
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Encontre Vagas de Estacionamento!
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-slate-600 sm:text-lg">
          Saiba onde estacionar nos principais shoppings em tempo real, com atualização automática por setor.
        </p>

        <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 rounded-2xl bg-white p-3 shadow-xl shadow-blue-100 ring-1 ring-slate-100 sm:flex-row sm:items-center">
          <div className="flex flex-1 items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-left">
            <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-blue-500" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 21s-7-6.14-7-11a7 7 0 0 1 14 0c0 4.86-7 11-7 11z" />
              <circle cx="12" cy="10" r="2.5" />
            </svg>
            <select
              value={selectedId}
              onChange={(e) => onSelect(e.target.value)}
              className="w-full bg-transparent text-sm font-medium text-slate-800 outline-none"
            >
              <option value="" disabled>
                Selecione o Shopping
              </option>
              {shoppings.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} — {s.city}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={onSearch}
            className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-blue-200 transition hover:bg-blue-700 active:scale-[0.98]"
          >
            Ver Vagas Disponíveis
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm bg-emerald-500" /> Vaga livre
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm bg-red-500" /> Vaga ocupada
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm bg-amber-400" /> Poucas vagas
          </div>
        </div>
      </div>
    </section>
  );
}
