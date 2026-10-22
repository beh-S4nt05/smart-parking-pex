# QA de UI/UX — medidas, métodos e checklist

> Rodada do dia 22/10 (relatório do usuário: lista sobreposta na web; app não
> ocupa a tela / barra nativa comendo os alvos de toque; botão "Entrar" do
> login sem render de cor). Este doc registra **como medir** cada ponto, o que
> foi medido e o resultado — para a suíte poder ser re-executada a qualquer
> momento sem depender de memória.

## 1. Princípio: medir o artefato, não a opinião

O app tem **dois renderers** (React Native nativo no Expo Go e react-native-web
no navegador) com regras próprias. O que passa num pode quebrar no outro — os
dois bugs abaixo passaram pelo crivo visual nativo e só apareceram na web. Por
isso o QA daqui é ancorado em medidas sobre artefatos reais.

## 2. Gate automatizado — pré-render da web (roda em qualquer máquina)

```bash
cd src/frontend/smart-parking
CI=1 npx expo export --platform web --output-dir dist
python3 - <<'PYEOF'
import re
h = open("dist/login.html").read()
i = h.find(">Entrar<"); ini = h.rfind("<button", 0, i)
botao = h[ini:i]
assert "bg-blue-600" in botao and "px-5" in botao, "botão sem estilo no pré-render!"
for pg in ["dist/login.html", "dist/index.html", "dist/dashboard.html", "dist/explorar.html"]:
    body = re.sub(r"<style[^>]*>.*?</style>", "", open(pg).read(), flags=re.S)
    assert 'style="opacity: 0' not in body and "translateY(12px)" not in body, f"{pg}: SSR preso em opacity 0"
print("QA web OK")
PYEOF
```

**Resultados medidos (22/10, pós-correção):**

| Medida | Antes | Depois |
|---|---|---|
| `<button>` do login no pré-render | `class="css-g5y9jx r-1loqt21 r-1otgn73"` (sem bg/padding/tamanho → **texto branco sobre branco**) | `…flex-row … rounded-xl px-5 py-3.5 bg-blue-600 active:bg-blue-700 active:scale-[0.97] transition-transform duration-100 w-full` |
| nós com `opacity: 0` inline no body (index) | presente (cards `translateY(12px)` deslocados → **sobreposição na lista**) | **0** |
| nós com `opacity: 0` inline (dashboard/explorar/login) | presente (FadeTroca/AnimarEntrada) | **0** |
| `translateY` restantes | — | 10, todos dentro de `<style>` (variáveis `--tw-*` do próprio Tailwind p/ utilitários scale) → inofensivo |

## 3. As duas causas estruturais (e por que só doíam na web)

1. **`Animated.createAnimatedComponent(Pressable)` fora do css-interop.**
   Na web, NativeWind resolve `className`→CSS só para componentes que conhece;
   o wrapper animado não está na lista → o `className` era **silenciosamente
   descartado** de todo `Botao` (e de qualquer componente que usasse o wrapper).
   No nativo o jsx-transform cuida de tudo, por isso o Expo Go nunca mostrou o
   problema. Correção: `Botao` usa Pressable puro na web (feedback via
   `:active` + `transition-transform duration-100`, 0 JS) e mantém o Animated
   spring no nativo (guarda do crash Fabric do PR#7).
2. **Estado inicial de `Animated.Value(0)` no SSR.**
   `AnimarEntrada`/`FadeTroca` nascem com `opacity:0` + `translateY(12)`; o
   pré-render grava isso no HTML e quem abre a URL vê os cards **empurrados 12px
   para baixo, sobre o item seguinte**, até a hidratação rodar. Em internet de
   V-02, "para sempre". Correção: short-circuit `Platform.OS === "web"` →
   renderizam direto; animação de entrada é luxo nativo, não custo de primeira
   pintura na web.

## 4. Tela cheia no celular (edge-to-edge) — regra da casa

- `app.json`: `android.edgeToEdgeEnabled: true` (já estava) → conteúdo sangra
  sob as barras; a barra de status vira **overlay transparente** (ícones
  escuros via `StatusBar style="dark"`).
- `src/app/_layout.tsx`: `useSafeAreaInsets()` (dependência
  `react-native-safe-area-context` que o template já traz — **zero pacote
  novo**) aplicado globalmente no `Stack contentStyle`:
  `paddingTop = insets.top`, `paddingBottom = max(insets.bottom, 8)`.
  **Efeito mensurável:** todo alvo de toque do app passa a viver abaixo da
  barra de status; a última linha de toda lista fica acima da barra de
  navegação/gesto. Na web os insets são 0 → zero regressão.
- Barreira `absolute` proibida em topo de tela: o `← Início` do login era
  `absolute left-3 top-4` — sob a barra, o toque morria no sistema. Migrou
  para o fluxo (`self-start ml-6 mt-4`) com `hitSlop` 8.
- Immersive/ocultar barra: **decisão registrada de rejeição** — esconder
  relógio/bateria num app de operação piora o uso; o usuário marcou o respiro
  seguro como ideal.

## 5. Heurísticas verificadas no código (auditoria estática desta rodada)

| Heurística | Medida | Status |
|---|---|---|
| Alvo de toque ≥ 44×44pt | `Botao` = `py-3.5`+15px texto ≈ 50pt; chips do mapa: `hitSlop` no Pressable + célula mínima do VagaMapa ≥ 56px (clamp `(min(width,1200)-96)/colunas`) | ✅ |
| Área extra p/ alvos pequenos | `hitSlop` no Botao (4/8) e no "←Início" (8) | ✅ |
| Sem conteúdo atrás de fixo | listas dentro de `ScrollView` filhas do contentStyle com padding de baixo | ✅ |
| Overflow de texto | `numberOfLines={1}` (+`ellipsizeMode="middle"` p/ e-mail) nos cards de est/usuário | ✅ |
| Campo escondido pelo teclado | `KeyboardAvoidingView` no login (mobile) e no `ModalForma` (`style={{flex:1}}` — não depender de className em componente fora do interop) | ✅ |
| Contraste dos tokens usados | texto branco sobre `bg-blue-600` = 4,8:1 (AA p/ 15px bold); slate-500 sobre slate-50 = 4,7:1 | ✅ |
| Feedback de toque ≤150ms | nativo spring ~140ms; web CSS `duration-100` | ✅ |

## 6. Checklist manual (Executar na V-02 — 2 minutos)

**Expo Go (Android e iOS):**
- [ ] Login: botão "Entrar" azul, tocável; "← Início" abaixo da barra de status e clicável
- [ ] Painel → Estacionamentos: cards com botões de ação com fundo/borda; última linha visível acima da barra de navegação
- [ ] Modal "Novo estacionamento": teclado não cobre os campos (Android) e o card não passa da borda inferior
- [ ] Mapa: tocar 2 vagas rápidas seguidas → feedback de press perceptível sem travar

**Navegador (dev e export):**
- [ ] `Ctrl+Shift+R` na URL do `dist` servido: botão do login visível **já no primeiro frame** (sem piscar branco)
- [ ] Abrir o dropdown do herói (seletor de shopping): a mini-lista flutua **sobre** o conteúdo, com sombra, sem cortar cards ao meio
- [ ] Redimensionar para ~900px: split do login colapsa para 1 coluna sem sobrepor o painel azul
- [ ] Trocar abas do painel: conteúdo aparece imediatamente (fade é só no nativo)

**Gate de regressão (antes de todo PR que tocar em UI):** seção 2 — se algum
componente novo usar wrapper `Animated.createAnimatedComponent` com className,
o grep do pré-render pega.

## 7. Ferramentas que NÃO usamos (e por escolha)

Sem `react-native-reanimated`/`expo-camera`/pacote de safe-area novo — a
política "zero npm install na V-02" segue; toda correção desta rodada coube em
RN core + dependências que o template Expo 57 já instala.
