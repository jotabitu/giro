# ListaComRolagem

Região com altura máxima de 320px (cerca de 5 a 6 linhas no computador, o mesmo teto das listas de escolha da locação) e rolagem própria, para listas que crescem sem limite dentro de um `Panel`: pagamentos e histórico da locação, sessões abertas do usuário.

- Só a lista rola. O título do `Panel` e a ação do cabeçalho ficam fora; numa tabela, o `thead` fica preso no topo da rolagem (`position: sticky`, fundo `surface-sunken`).
- Lista curta não ganha espaço vazio: é altura máxima, não altura fixa. Lista que cabe nos 320px não rola.
- `rotulo` é obrigatório: vira o nome da região para o leitor de tela. A região recebe foco pelo teclado (Tab) e rola com as setas, com o anel de foco do sistema (`--focus`).
- `overscroll-behavior: auto`: no celular, quando a lista chega ao fim, a rolagem passa para a página.
- Não há tela de referência própria: a rolagem não muda layout, texto nem ordem. Vale para qualquer lista longa de painel; ações fora da lista (como "Redefinir 2 etapas") ficam fora da região.

Código em `frontend/src/design-system/components/ListaComRolagem/` (T-510), preview em `/design-system/lista-com-rolagem`. Classe `.wl-rolagem` em `components/bundle.css`.
