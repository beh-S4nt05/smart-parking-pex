import { useState } from "react";

export default function Reserve() {
  const [reserved, setReserved] = useState(false);
  const [method, setMethod] = useState<"pix" | "card">("pix");

  return (
    <section className="bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-8 rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-100 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Reserva Antecipada</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-900 sm:text-3xl">Reserve sua Vaga Antecipadamente</h2>
            <p className="mt-3 text-slate-600">
              Garanta sua vaga preferida agora mesmo e evite perder tempo procurando estacionamento no shopping.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={() => setMethod("card")}
                className={`flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-semibold transition ${
                  method === "card" ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-500"
                }`}
              >
                💳 Cartão de Crédito
              </button>
              <button
                onClick={() => setMethod("pix")}
                className={`flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-semibold transition ${
                  method === "pix" ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-500"
                }`}
              >
                ⚡ Pix
              </button>
            </div>

            <button
              onClick={() => setReserved(true)}
              className="mt-6 w-full rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-bold text-white shadow-md shadow-blue-200 transition hover:bg-blue-700 sm:w-auto"
            >
              {reserved ? "✓ Vaga Reservada!" : "Reservar Vaga"}
            </button>
            {reserved && (
              <p className="mt-3 text-sm font-medium text-emerald-600">
                Reserva confirmada! Enviamos os detalhes para o seu e-mail.
              </p>
            )}
            <p className="mt-3 text-xs text-slate-400">
              Pagamento facilitado com PIX e Cartão de Crédito. Cancelamento gratuito até 1h antes.
            </p>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 p-6 text-white shadow-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-blue-100">Resumo da Reserva</span>
              <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-bold">Setor Cinema</span>
            </div>
            <div className="mt-6 space-y-3 text-sm">
              <div className="flex items-center justify-between border-b border-white/20 pb-3">
                <span className="text-blue-100">Vaga</span>
                <span className="font-semibold">C-014</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/20 pb-3">
                <span className="text-blue-100">Data</span>
                <span className="font-semibold">Hoje</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/20 pb-3">
                <span className="text-blue-100">Duração</span>
                <span className="font-semibold">Até 3 horas</span>
              </div>
              <div className="flex items-center justify-between pt-1">
                <span className="text-blue-100">Valor</span>
                <span className="text-lg font-extrabold">R$ 12,00</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
