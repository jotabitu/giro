# SelectField

Campo de escolha entre opções fixas, com o visual do `TextField` (`wl-field` + `wl-input`, 48px). Padrão do assistente de implantação (`Onboarding-Importar`: "Filial dos veículos" e "Categoria de cada modelo", IMP-08) e de qualquer lista de linhas em que cada linha pede uma escolha.

```tsx
import { LinhaDeLista, ListaDeLinhas, SelectField } from "@/design-system";

<SelectField rotulo="Filial dos veículos" vazio="Escolha a filial" opcoes={filiais} value={filial} onChange={...} erro={erro} />

<ListaDeLinhas rotulo="Categoria de cada modelo">
  <LinhaDeLista
    titulo="Honda CG 160 Fan"
    apoio="20 veículos"
    acao={<SelectField rotulo="Categoria de Honda CG 160 Fan" rotuloOculto vazio="Escolha a categoria" opcoes={categorias} />}
  />
</ListaDeLinhas>
```

- **Opções:** `opcoes` com `valor` e `rotulo`. `vazio` põe a opção em branco ("Escolha a categoria"); use quando a regra proíbe escolha por padrão (IMP-08: filial e categoria começam sem marcação quando há mais de uma).
- **Dica e erro:** como no `TextField`. O erro diz o que fazer ("Escolha a filial dos veículos.") e pinta a borda de `critical`; `aria-invalid` e `aria-describedby` já saem ligados.
- **Dentro de linha de lista:** `rotuloOculto` esconde o rótulo da vista e o mantém para o leitor de tela; diga nele o item ("Categoria de Honda CG 160 Fan"), não só "Categoria". O campo tem 220px na linha e passa para baixo do título, em largura total, abaixo de 720px.
- **Largura:** 280px padrão; `cheio` ocupa o contêiner; abaixo de 720px é sempre largura total.
- **Acessibilidade:** `<select>` nativo, então teclado, leitor de tela e lista do celular funcionam sem código extra. O rótulo é sempre um `<label>` ligado ao campo.
- Quando a lista tiver muitas opções com busca, ou for escolha entre 2 a 4 itens sempre visíveis, use o `SegmentedControl`, não este campo.
- Sem token novo: usa `line`, `surface`, `ink`, `critical` e `radius-md`, nos dois temas.
