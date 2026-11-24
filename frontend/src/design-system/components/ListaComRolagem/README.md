# ListaComRolagem

Região com altura máxima de 320px (cerca de 5 a 6 linhas no computador, o mesmo teto das listas de escolha da locação) e rolagem própria, para listas que crescem sem limite dentro de um `Panel`: pagamentos, histórico, sessões.

- Só a lista rola. O título do `Panel` e a ação do cabeçalho ficam fora; numa tabela, o `thead` fica preso no topo da rolagem (`position: sticky`).
- Lista curta não ganha espaço vazio: é altura máxima, não altura fixa.
- `rotulo` é obrigatório: vira o nome da região para o leitor de tela. A região recebe foco pelo teclado (Tab) e rola com as setas, com o anel de foco do sistema.
- `overscroll-behavior: auto`: no celular, quando a lista chega ao fim, a rolagem passa para a página.

## Em React

Código em `frontend/src/design-system/components/ListaComRolagem/ListaComRolagem.tsx`; preview em `/design-system/lista-com-rolagem`.

```tsx
<Panel titulo="Histórico">
  <ListaComRolagem rotulo="Histórico da locação">
    <ol>...</ol>
  </ListaComRolagem>
</Panel>
```
