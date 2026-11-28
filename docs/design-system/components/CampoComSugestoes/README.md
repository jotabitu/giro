# CampoComSugestoes

Campo de texto com uma lista de sugestões própria (combobox), no lugar do `datalist` do navegador, que muda de aparência em cada sistema e some no celular. A lista abre logo abaixo do campo, na mesma peça do menu do `SeletorDeFilial` (`wl-menu`), com os tokens de `surface`, `ink-muted` e `shadow-pop`, no claro e no escuro.

Cada opção tem o texto principal (o que vai para o campo) e, se houver, uma linha de apoio em texto menor: no modelo do veículo, o modelo e a marca. A opção escolhida leva a marca de conferido.

Digitar livre continua valendo: o texto do campo é o que se grava, escolhido da lista ou não. A lista é só ajuda.

## Em React

Código em `frontend/src/design-system/components/CampoComSugestoes/CampoComSugestoes.tsx`; preview em `/design-system/campo-com-sugestoes`.

```tsx
import { CampoComSugestoes } from "@/design-system";

<CampoComSugestoes
  cheio
  rotulo="Modelo"
  dica="Escolha da lista ou digite"
  opcoes={modelos.map((m) => ({ valor: m.modelo, apoio: m.marca, chave: `${m.marca}|${m.modelo}` }))}
  escolhida={`${v.marca}|${v.modelo}`}
  aoEscolher={(o) => setValue("modelo", o.valor)}
  {...register("modelo")}
/>
```

- `opcoes` vêm prontas de quem usa (a API busca e filtra); a peça não filtra. Lista vazia: o campo é um campo de texto comum.
- `aoEscolher` recebe a opção escolhida; quem usa grava o valor no formulário. `escolhida` marca a opção pela `chave` (ou pelo `valor`).
- Aceita `rotulo`, `dica`, `erro`, `mono`, `cheio` como o `TextField`, o `ref` e os atributos de `<input>` (funciona com `register` do React Hook Form).
- `abertoNoInicio` é só para o catálogo e as capturas.

## Teclado e leitor de tela

Focar ou digitar abre a lista, sem opção em foco. Seta para baixo e para cima abrem e movem (não dão a volta), Home e End vão às pontas, Enter escolhe a opção em foco (sem opção em foco, o Enter segue para o formulário), Escape fecha sem fechar a gaveta ou o diálogo em volta, Tab e clique fora fecham. O campo é `role="combobox"` com `aria-expanded`, `aria-controls` e `aria-activedescendant`; a lista é `role="listbox"` com `role="option"` e `aria-selected`. Toque e clique escolhem sem tirar o foco do campo. A lógica do teclado fica em `logica.ts`, testada sem DOM.

Componente de cliente.
