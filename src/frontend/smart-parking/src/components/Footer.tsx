export default function Footer() {
  return (
    <footer id="contato" className="bg-slate-900 text-slate-300">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-700">
                <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11" />
                  <path d="M3 16v-3.5A1.5 1.5 0 0 1 4.5 11h15A1.5 1.5 0 0 1 21 12.5V16" />
                  <circle cx="7" cy="16" r="1.4" fill="currentColor" />
                  <circle cx="17" cy="16" r="1.4" fill="currentColor" />
                </svg>
              </div>
              <span className="font-bold text-white">Smart Parking</span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              Monitoramento inteligente de vagas em estacionamentos de shoppings, em tempo real e por setor.
            </p>
          </div>

          <div>
            <h4 className="text-sm font-bold uppercase tracking-wide text-white">Integração</h4>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li className="hover:text-white">Painel Administrativo</li>
              <li className="hover:text-white">Documentação Técnica</li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-bold uppercase tracking-wide text-white">Contato</h4>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li className="flex items-center gap-2">📞 (92) 98123-0258</li>
              <li className="flex items-center gap-2">✉️ behsolutionsandautomations@gmail.com</li>
              <li className="flex items-center gap-2">📍 Manaus, AM</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-800 pt-6 text-xs text-slate-500 sm:flex-row">
          <p>© {new Date().getFullYear()} Smart Parking Shoppings. Todos os direitos reservados.</p>
          <p>Feito com 💙 para facilitar sua ida ao shopping.</p>
        </div>
      </div>
    </footer>
  );
}
