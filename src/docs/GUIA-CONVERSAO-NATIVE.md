# Correção do crash nativo — tags HTML/SVG em componentes React Native

## 1. O erro

```
Invariant Violation: View config getter callback for component `path` must be a function (received `undefined`).
  at Header (src/components/Header.tsx:20:15)
```

## 2. Causa raiz (verificada, não suposição)

O `Header.tsx` foi escrito com **tags HTML e SVG inline**: `<header>`, `<div>`, `<nav>`,
`<button>`, `<p>`, `<svg>`, `<path>`, `<circle>`.

Isso funciona **somente no web**, porque o `react-dom` resolve essas strings como elementos
DOM reais. No Android/iOS o React Native precisa de um *view config* nativo registrado para
cada componente; ele procura um chamado `path` (ou `div`, `button`…), não encontra e lança
o `Invariant Violation`.

**O `path` da linha 20 foi apenas o primeiro a falhar.** Todas as outras tags do arquivo
quebram do mesmo jeito.

### Verificação: o preset `nativewind/babel` NÃO converte tags HTML

Rodei o Babel do projeto sobre o seu `Header.tsx` (babel.config.js real, com
`nativewind/babel`) e o resultado foi:

```
tag "header"   -> _jsx("header", {...})     ← continua string
tag "div"      -> _jsx("div", {...})        ← continua string
tag "nav"      -> _jsx("nav", {...})        ← continua string
tag "button"   -> _jsx("button", {...})     ← continua string
tag "p"        -> _jsx("p", {...})          ← continua string
tag "svg"      -> _jsx("svg", {...})        ← continua string
tag "path"     -> _jsx("path", {...})       ← continua string
tag "circle"   -> _jsx("circle", {...})     ← continua string
```

Confirmação no código-fonte do NativeWind v4
(`node_modules/react-native-css-interop/dist/runtime/components.js`): ele registra para
interop **apenas componentes do React Native** — `View`, `Text`, `Pressable`, `Image`,
`TextInput`, `ScrollView`, `FlatList`, `Switch`, `TouchableOpacity`, `ActivityIndicator`,
`StatusBar`, `VirtualizedList`, `SafeAreaView`, etc. **Nenhuma tag HTML é registrada.**
O `wrap-jsx.js` faz `interopComponents.get(type) ?? type`, ou seja, o que não é
conhecido passa adiante como string.

> **Conclusão:** NativeWind v4 não é um "tradutor de HTML para React Native". Ele só injeta
> `className` em componentes RN. Escrever `<div>` com `className` continua sendo um
> componente web puro e vai crashar no nativo.

## 3. Como achar todos os arquivos afetados no seu projeto

Rode na raiz do projeto:

```bash
grep -rlE "<(div|span|p|h[1-6]|header|footer|nav|main|section|article|aside|button|ul|li|img|svg|path|circle|rect|input|label|a|table|tr|td|form|select|option|figure|strong|em|br|hr)[ />]" src app --include="*.tsx"
```

Também procure por APIs web-only, que igualmente quebram no nativo:

```bash
grep -rnE "window\.|document\.|localStorage|sessionStorage|localStorage|navigator\.|\.innerHTML|addEventListener\(|onClick=|onChange=\{[^}]*=>[^}]*event|useEffect\(\(\) => \{[^}]*scroll" src app --include="*.tsx" --include="*.ts"
```

## 4. Tabela de conversão (HTML → React Native)

| Web (quebra no nativo) | React Native (funciona nas 3 plataformas) |
|---|---|
| `<div>`, `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, `<aside>`, `<article>` | `<View>` |
| `<p>`, `<span>`, `<h1>`…`<h6>`, `<strong>`, `<em>`, `<label>` | `<Text>` |
| `<button>`, `<a>` | `<Pressable>` (com `<Text>` dentro) ou `<Link>` do expo-router |
| `<img>` | `<Image>` do `react-native` (ou `expo-image`) |
| `<input>` | `<TextInput>` |
| `<ul>`/`<li>` | `<FlatList>` (lista longa) ou `<View>` + `.map()` (lista curta) |
| `<svg>`/`<path>`/`<circle>`/`<rect>` | `react-native-svg` **ou** `@expo/vector-icons` |
| scroll de página (`overflow-y-auto` no body) | `<ScrollView>` ou `<FlatList>` |
| `onClick={fn}` | `onPress={fn}` |
| `onChange={e => e.target.value}` | `onChangeText={texto => …}` |
| `<table>`, `<tr>`, `<td>` | `<View>` com `flex-row` (não existe tabela nativa) |
| `<br>` | `\n` dentro do `<Text>` |

### Classes Tailwind que NÃO existem no nativo

`sticky`, `fixed`, `z-50`, `backdrop-blur-*`, `shadow-*`, `overflow-x-auto` (em `<View>`),
`grid`, `col-*`, media queries (`md:`, `lg:`), `hover:`, `whitespace-nowrap` (parcial),
`cursor-pointer`. Substitua por:

| Web | Nativo equivalente |
|---|---|
| `sticky top-0 z-50` | coloque o `<Header>` fora do `<ScrollView>`, como filho direto de um `<View className="flex-1">` |
| `backdrop-blur-xl bg-white/90` | `bg-white` (blur nativo exige `expo-blur`, que não está no seu package.json) |
| `shadow-md` | use `border-b border-slate-200` ou a prop `style={{ elevation: 3 }}` (Android) |
| `overflow-x-auto` + `whitespace-nowrap` | `<ScrollView horizontal showsHorizontalScrollIndicator={false}>` |
| `md:flex hidden` | `Platform.OS === "web"` |
| `hover:bg-slate-100` | remova (não há hover no toque) ou use `android_ripple` / estados do `Pressable` |
| `bg-gradient-to-r from-blue-600` | `expo-linear-gradient` (dep extra) ou cor sólida |

### Regra de ouro

**Todo texto precisa estar dentro de um `<Text>`.** No nativo, `<View>` não aceita filhos
de texto — `<View>Smart Parking</View>` lança "Text strings must be rendered within a
`<Text>` component".

## 5. Os arquivos corrigidos

- `Header.tsx` — reescrito 100% com componentes RN, mantendo o mesmo visual (marca +
  navegação + ações) e o `className` do NativeWind.
- `CarIcon.tsx` — o desenho original do seu `<svg>` convertido para `react-native-svg`,
  funciona no Android, iOS e web.

### Ícone: duas opções, escolha uma

**Opção A — `react-native-svg` (desenho idêntico ao seu SVG original).** Já validada e
instalada na versão correta do SDK 57 (`15.15.4`), `0 vulnerabilidades`, doctor 21/21.
É o que está em `CarIcon.tsx`.

**Opção B — `@expo/vector-icons` (zero dependência nova, já está no seu package.json).**
Troque o `<CarIcon size={20} color="#ffffff" />` por:

```tsx
import { Ionicons } from "@expo/vector-icons";

<Ionicons name="car" size={20} color="#fff" />
```

Ícones de carro disponíveis (glyphmaps reais do pacote):
- **Ionicons**: `car`, `car-outline`, `car-sport`, `car-sport-outline`
- **MaterialCommunityIcons**: `car`, `car-outline`, `car-back`, `car-side`, `car-brake-parking`

Se você não usa `<Svg>` em nenhum outro lugar do app, a **Opção B** é a mais econômica e
você nem precisa instalar o `react-native-svg`.

### Observações sobre o design

1. **O gradiente azul** (`bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700`) não
   existe no nativo. No `Header.tsx` corrigido usei `bg-blue-600` sólido, que visualmente
   é muito próximo. Se quiser o gradiente exato: `npx expo install expo-linear-gradient`.
2. **O `Header` de `src/components/Header.tsx` parece ser o header de uma landing page**
   (navegação Início / Shoppings / Mapa / Contato + botão "Entrar"), não o header do app
   autenticado — o `app/index.tsx` do kit tem `HomeHeader` com nome de shopping, botão de
   notificações e avatar. Vale conferir se o `app/index.tsx` não deveria importar o
   `HomeHeader`, e se este `Header` não pertence a uma rota pública (`app/(public)/index.tsx`,
   por exemplo).
3. **O stack do erro mostra `src/app/index.tsx`.** No kit que enviei, as rotas ficam em
   `app/` na raiz (padrão Expo Router) e `src/` guarda `components/`, `services/`,
   `contexts/`. Se o seu projeto usa `src/app/`, tudo bem — o expo-router aceita os dois —
   mas então mantenha o `tsconfig.json` com o alias `@/*` apontando para `./src/*` e as
   rotas em `src/app`. Só não misture os dois layouts.
4. A navegação `onNavigate(id)` com scroll para seção é um padrão **web**. No nativo o
   equivalente seria `<Link href="/shoppings">` do expo-router. No arquivo corrigido
   mantive a prop `onNavigate` para não mudar seu contrato, mas considere migrar para
   rotas quando adaptar a página inteira.

## 6. Validação executada (SDK 57 + RN 0.86.3 + NativeWind 4.2.7)

| Teste | Resultado |
|---|---|
| `tsc --noEmit` (TypeScript 6.0.3) | exit 0, sem erros |
| `expo export --platform android` | **exit 0** — 1695 módulos, 39,1 s |
| Tags HTML no bundle Android (`header`, `nav`, `button`, `svg`, `path`, `circle`) | **todas ausentes** ✅ |
| `expo export --platform web` | exit 0 — 814 módulos, 3 rotas estáticas |
| "Smart Parking" renderizado no HTML (SSG web) | SIM ✅ |
| `npm audit` com `react-native-svg` adicionado | **0 vulnerabilidades** |
| `npx expo install --check` | Dependencies are up to date |
| `npx expo-doctor` | **21/21 checks passed** |

O bundle Android é a prova definitiva: antes ele nem era gerado (crash no runtime do
device); agora compila e não contém nenhuma string de tag HTML.

## 7. Dependências

- **Opção A (usada na validação):** `react-native-svg` — adicione com
  `npx expo install react-native-svg` (resolve para `15.15.4`, a versão do SDK 57).
- **Opção B:** nenhuma. `@expo/vector-icons@^15.0.2` já está no seu `package.json`.
