# BarraDeAcoes

Barra flutuante de ações no pé de toda tela de página inteira que cria ou edita: cartão `surface` com `shadow-pop`, fixo ao rolar, "Cancelar" quieto e o botão principal sólido à direita. No celular fica acima da barra de navegação de baixo (`bottom-[88px]`); no desktop, a 16px da borda. Fica no fim do conteúdo, então o fim da página nunca some atrás dela.

```tsx
<form id="novo-veiculo" onSubmit={enviar}>...</form>
<BarraDeAcoes cancelar={{ href: "/veiculos" }} principal={{ rotulo: "Cadastrar veículo", form: "novo-veiculo", ocupado: enviando }} />
```

- `cancelar`: `{ href }` (link) ou `{ aoClicar, disabled? }` (botão, para quem desfaz alterações). `rotulo` é "Cancelar" por padrão.
- `principal`: `rotulo` é o texto que a tela já usa. `ocupado` troca o texto por "Salvando…" (ou `textoOcupado`) e desabilita. `form="id"` envia o form quando a barra fica fora dele; o Enter num campo continua salvando pelo próprio form. Com `aoClicar`, vira botão comum, para a tela que não é um `<form>`.
- `aEsquerda` (opcional): texto ou ação secundária à esquerda, como "Alterações não salvas" ou "Salvar e cadastrar outro". No celular ocupa a linha de cima, e os botões ficam na de baixo.

Não use em diálogos e painéis laterais (têm os botões no rodapé), no assistente de implantação (tem a navegação de passos) nem em tela só de leitura. Se a tela já tinha botões no fim do formulário, eles passam para a barra: não duplique.
