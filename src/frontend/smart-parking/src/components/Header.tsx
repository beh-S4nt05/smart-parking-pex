interface HeaderProps {
  activeSection: string;
  onNavigate: (id: string) => void;
}

const NAV_ITEMS = [
  { id: "inicio", label: "Início" },
  { id: "shoppings", label: "Shoppings" },
  { id: "mapa", label: "Mapa" },
  { id: "contato", label: "Contato" },
];

export default function Header({ activeSection, onNavigate }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 shadow-md shadow-blue-200">
            <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11" />
              <path d="M3 16v-3.5A1.5 1.5 0 0 1 4.5 11h15A1.5 1.5 0 0 1 21 12.5V16" />
              <path d="M5 16v2M19 16v2" />
              <circle cx="7" cy="16" r="1.4" fill="currentColor" />
              <circle cx="17" cy="16" r="1.4" fill="currentColor" />
            </svg>
          </div>
          <div className="leading-tight">
            <p className="text-base font-bold text-slate-900">Smart Parking</p>
            <p className="text-[11px] font-medium text-slate-500">Shoppings</p>
          </div>
        </div>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                activeSection === item.id
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button className="hidden rounded-full px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50 sm:block">
            Suporte
          </button>
          <button className="rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700">
            Entrar
          </button>
        </div>
      </div>

      <nav className="flex items-center gap-1 overflow-x-auto border-t border-slate-100 px-4 py-2 md:hidden">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
              activeSection === item.id
                ? "bg-blue-50 text-blue-700"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
