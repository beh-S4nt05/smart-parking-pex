/**
 * Receitas ATÔMICAS: cada constante é a string final e completa de classes.
 *
 * Regra deliberada: NÃO existe `cn()` nem composição de receita com sufixo.
 * Motivo (medido em auditoria anterior): `cn(tituloCard, "text-2xl")`
 * produzia `text-base ... text-2xl` na mesma string; o Tailwind resolvia
 * pelo critério de desempate do CSS gerado e o título encolhia de 24px
 * para 16px no celular. Compor utilidades conflitantes é regressão
 * silenciosa — por isso cada variação tem sua própria string completa.
 *
 * O scanner do Tailwind lê `./src/**\/*.{js,jsx,ts,tsx}`, então as classes
 * literais deste arquivo são geradas normalmente no CSS do bundle.
 *
 * Lei de Jakob / semelhança / Occam: um nome por padrão, uma linha por
 * padrão, nenhuma lógica de merge espalhada pelos componentes.
 */
export const pagina = "sp-page flex-1 bg-slate-50";
export const cartao = "sp-card rounded-2xl border border-slate-200 bg-white";
export const tituloCard = "text-base font-bold text-slate-900";
export const tituloSecao = "text-balance text-center text-2xl font-extrabold text-slate-900 sm:text-3xl 3xl:text-4xl";
export const tituloExplorar = "text-balance text-xl font-extrabold text-slate-900 sm:text-3xl 3xl:text-4xl";
export const tituloSecaoStatus = "text-[15px] font-extrabold text-slate-900";
export const tituloCardShopping = "text-[15px] font-bold text-slate-900";
export const textoApoio = "mt-1 text-sm text-slate-600";
export const textoAuxiliar = "text-[12px] text-slate-600";
export const textoApoioCentro = "text-center text-sm text-slate-600";
export const subtituloHero = "mt-4 max-w-xl text-center text-sm leading-5 text-slate-600 sm:mt-5 sm:text-base sm:leading-6 3xl:max-w-2xl 3xl:text-lg";
export const descricaoLogin = "mt-1.5 text-sm text-slate-600";
export const meta = "mt-0.5 text-[13px] text-slate-600";
export const rodapeCopyright = "text-xs text-slate-400";
export const linkNav = "min-h-11 min-w-0 flex-row items-center content-center rounded-lg px-2 text-slate-100 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 web:motion-reduce:transition-none sm:px-3";
export const rotulo = "text-[13px] font-semibold text-slate-700";
export const campo = "sp-field min-w-0 flex-row items-center rounded-xl border-2 bg-slate-50 px-3.5";
export const botao = "sp-btn relative min-h-11 flex-row select-none items-center justify-center gap-2 rounded-xl px-5 py-3.5";
export const secao = "sp-secao";
export const minW0Flex1 = "min-w-0 flex-1";
export const linhaAcoes = "flex-row flex-wrap gap-2";
