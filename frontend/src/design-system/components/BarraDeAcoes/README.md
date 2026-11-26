# BarraDeAcoes

Barra flutuante de ações no pé de toda tela de página inteira que cria ou edita: cartão `surface` com `shadow-pop`, fixo ao rolar, "Cancelar" quieto e o botão principal sólido à direita. No celular fica acima da barra de navegação de baixo (`bottom-[88px]`); no desktop, a 16px da borda. Fica no fim do conteúdo, então o fim da página nunca some atrás dela.

Na tela que tem o bloco fixo de botões, passe `blocos` (T-519): a barra só aparece quando o bloco sai da tela. Sem `blocos`, aparece sempre.

```tsx
<form id="novo-veiculo" onSubmit={enviar}>...</form>
<BarraDeAcoes cancelar={{ href: "/veiculos" }} principal={{ rotulo: "Cadastrar veículo", form: "novo-veiculo", ocupado: enviando }} />
```

- `cancelar`: `{ href }` (link) ou `{ aoClicar, disabled? }` (botão, para quem desfaz alterações). `rotulo` é "Cancelar" por padrão.
- `principal`: `rotulo` é o texto que a tela já usa. `ocupado` troca o texto por "Salvando…" (ou `textoOcupado`) e desabilita. `form="id"` envia o form quando a barra fica fora dele; o Enter num campo continua salvando pelo próprio form. Com `aoClicar`, vira botão comum, para a tela que não é um `<form>`.
- `blocos` (T-519, opcional): o retorno de `useBlocoVisivel()`, para a tela que tem o bloco fixo de botões (no painel lateral, no cabeçalho ou no fim do formulário). A barra fica escondida enquanto o bloco aparece e surge quando ele sai da tela, com transição suave. Escondida, ela continua ocupando o lugar (o layout não pula) e fica inerte e fora da leitura (`inert`, `aria-hidden`). Sem `blocos`, ela aparece sempre.
- `aEsquerda` (opcional): texto ou ação secundária à esquerda, como "Alterações não salvas" ou "Salvar e cadastrar outro". No celular ocupa a linha de cima, e os botões ficam na de baixo.

## Bloco fixo de botões e barra (T-519)

Nas telas de criar e editar, os botões ficam no bloco de sempre (aside, cabeçalho ou fim do formulário) e a barra repete só **Cancelar** e o botão principal, sem `aEsquerda`. Os dois enviam o mesmo form e têm o mesmo estado ocupado e desligado.

```tsx
const blocos = useBlocoVisivel();
<form id="novo-veiculo" onSubmit={enviar}>
  ...
  <aside>
    <section ref={blocos.ref()}>{/* Salvar, Salvar e cadastrar outro, Cancelar */}</section>
  </aside>
  <BarraDeAcoes blocos={blocos} cancelar={{ href: "/veiculos" }} principal={{ rotulo: "Salvar veículo" }} />
</form>
```

- `useBlocoVisivel()` devolve `{ ref, visivel }`. `ref()` marca o bloco; se o bloco existe em dois lugares (cabeçalho no desktop e pé no celular), use uma chave para cada: `ref("cabecalho")`, `ref("pe")`. Basta um aparecer para a barra ficar escondida.
- `visivel` começa `true`: a barra nasce escondida e não pisca. Sem bloco registrado, ou sem `IntersectionObserver`, a barra aparece. Bloco com `display: none` (como o do cabeçalho no celular) conta como fora da tela, e a barra fica à mostra.
- No celular, com o aside embaixo do formulário, vale o mesmo: a barra aparece enquanto o bloco não está na tela.

Não use em diálogos e painéis laterais (têm os botões no rodapé), no assistente de implantação (tem a navegação de passos) nem em tela só de leitura. Na tela com bloco fixo de botões, o bloco continua e a barra o repete só com Cancelar e o principal, sempre com `blocos`; sem `blocos`, a barra apareceria junto do bloco e duplicaria os botões.
