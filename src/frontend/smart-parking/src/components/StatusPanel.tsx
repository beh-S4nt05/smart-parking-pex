interface StatusPanelProps {
  total: number;
  free: number;
  occupancy: number;
  avgStayMinutes: number;
}

function formatMinutes(min: number) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m}min`;
  return `${h}h ${m}min`;
}

export default function StatusPanel({ total, free, occupancy, avgStayMinutes }: StatusPanelProps) {
  const cards = [
    {
      label: "Vagas Disponíveis",
      value: free,
      accent: "text-emerald-600",
      bg: "bg-emerald-50",
      icon: "🅿️",
    },
    {
      label: "Ocupação Atual",
      value: `${occupancy}%`,
      accent: "text-blue-600",
      bg: "bg-blue-50",
      icon: "📊",
    },
    {
      label: "Tempo Médio",
      value: formatMinutes(avgStayMinutes),
      accent: "text-indigo-600",
      bg: "bg-indigo-50",
      icon: "⏱️",
    },
    {
      label: "Total de Vagas",
      value: total,
      accent: "text-slate-700",
      bg: "bg-slate-100",
      icon: "🏬",
    },
  ];

  return (
    <section className="mx-auto -mt-2 max-w-6xl px-4 pb-4 sm:px-6 lg:px-8">
      <div className="rounded-3xl bg-white p-6 shadow-lg shadow-slate-200/60 ring-1 ring-slate-100">
        <div className="mb-5 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">Status do Estacionamento</h3>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className={`rounded-2xl ${c.bg} p-4 text-center transition hover:scale-[1.02]`}>
              <div className="mb-1 text-xl">{c.icon}</div>
              <p className={`text-2xl font-extrabold ${c.accent}`}>{c.value}</p>
              <p className="mt-1 text-xs font-medium text-slate-500">{c.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
