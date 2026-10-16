# T-251 · Telas das decisões de 15 out · frontend → orquestrador, segurança (T-252), qa

**O que foi feito:**
- **Clientes (CLI-10):** filtro "Filial" na lista, com "Todas as filiais" como padrão e as opções de `GET /api/filiais/minhas/`; vai na URL (`?filial=`) e para a API como `filial`; não segue o seletor do topo.
- **Aprovar (APR-09):** o detalhe da despesa lê `pode_decidir` do pedido (`GET /api/aprovacoes/`, pendentes) e não olha mais perfil nem quem lançou; a administradora vê Aprovar e Recusar no próprio pedido. A lista de Aprovações já usava `pode_decidir`.
- **Convite (USR-01):** no painel da pessoa com convite pendente, "Copiar link do convite" (`POST /api/usuarios/{id}/link-convite/`), mostrado por `acoes.copiar_link_convite` (Reenviar e Cancelar também por `acoes`). O link vai direto para a área de transferência dentro da mutação e não fica em estado nem em cache; a confirmação mostra o `aviso` da API ("O link anterior deixa de valer."), com a mesma frase como legenda sob o botão.
**Onde:** components/clientes/ListaClientes.tsx, components/financeiro/DetalheDaDespesa.tsx, components/admin/PainelDoUsuario.tsx, lib/api/{clientes,usuarios,tipos-clientes,tipos-usuarios}.ts, falsos de clientes, usuários e financeiro.
**Regras cobertas:** CLI-10, APR-09, USR-01 (CA-248-01, 06, 07 na tela; 08 e 10 pelo botão; 12 a 15 pelo botão e pelo aviso). Testes: ListaClientes.test.tsx, Despesas.test.tsx, Usuarios.test.tsx.
**O que ficou de fora:** os números de Aprovadas e tempo médio do CA-248-08 (T-202, backend); testes são de marcação estática, então o clique de copiar e a mensagem de falha da área de transferência não têm teste de interação; sem a escolha de filial para o convite expirado a tela só segue a API (410/429 aparecem como erro). A divergência CA-248-12 (404 x 410) é do backend.
**Próximo passo para quem recebe:** orquestrador abre o PR depois do #272; segurança confere que o link não fica em cache; qa repete CA-248-01 a 16 no navegador.
