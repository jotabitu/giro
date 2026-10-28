# Handoff · T-359 · Tabelas de preço (frontend)

- **Agente:** frontend
- **Branch:** `t-359-tabelas-de-preco`
- **Contrato:** `docs/api/veiculos.md` ("Categorias e preços", "Extras"), `docs/api/locacoes.md` ("Planos especiais")
- **Telas de referência:** `docs/telas/html/Precos-Desktop.dc.html`, `Precos-Mobile.dc.html`
- **Regras:** LOC-01, LOC-02, LOC-15, FIL-04

## O que foi entregue

1. **API (`frontend/src/lib/api/precos.ts`, `tipos-precos.ts`):** categorias (listar, criar, alterar, desativar, reativar), preço novo (`POST`), preço agendado (`PUT`), histórico da categoria e da empresa, extras e planos especiais. Tipos vêm do OpenAPI gerado.
2. **Tela `/admin/precos` (`frontend/src/components/precos/TabelaDePrecos.tsx`):**
   - `CategoriasDePreco`: tabela no desktop e cartões no celular, com o filtro "Filial X / Todas as filiais" (`?filial=`), "Editar" e "Mostrar categorias desativadas".
   - `DialogoDaCategoria`: nome, tipo (travado com veículos), os 4 valores, "Vale a partir de" (preço agendado troca por `PUT`), histórico da categoria, desativar e reativar. O aviso do `locacoes_em_andamento_mantidas` vem da API.
   - `HistoricoDePrecos`: `GET /api/precos/historico/`.
   - `ExtrasDeLocacao` e `PlanosEspeciais`: criar, editar, desativar, "Mostrar desativados".
   - O cartão "precos" de Configurações já apontava para `/admin/precos`; a rota agora existe.
3. **Reaproveitar no assistente:** `CategoriasDePreco` recebe `filial`, `criando`, `aoFecharCriacao` e `aoAvisar`, e não depende da página. O botão "Nova categoria" fica fora do painel, de propósito.
4. **Falso (`frontend/src/testes/falsos/falso-precos.ts`):** seed de 07 out (Urbana 4490/29940/109000/30000, Street 5490/32900/119000/30000 com 29940 antes de 01 out, Scooter, Carro compacto), `preco_ja_definido`, `preco_ja_vigente`, `categoria_nome_em_uso`, `categoria_com_veiculos`.

## Pontos para o orquestrador e o produto

- **"Regras de cobrança" ficou de fora.** O painel da referência vem de `ConfiguracaoEmpresa` e não há rota no OpenAPI. Precisa de contrato (arquiteto) antes de entrar.
- **Sem `acoes` nem permissão própria nessas rotas.** A tela usa `eu.pode.administracao`, como as outras de Administração.
- **Extras e planos especiais só têm "desativar"** no contrato. Não há "reativar"; os desativados aparecem só para leitura. Categoria tem os dois.
- Categorias vinculadas ao plano especial (`categorias`) não têm campo no formulário; o plano novo vale para todas, e a edição mantém as que a API já tem.

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 77 arquivos, 718 testes passando antes dos ajustes finais de lint; os arquivos novos (`precos.test.ts`, `TabelaDePrecos.test.tsx`, `api/precos.test.ts`) passam depois deles.
- Os testes rodam em `node`, sem DOM: os diálogos estão cobertos por contrato e pela lógica, não por clique. Vale uma passada manual ou do QA a 1440px e 390px.
- Nenhuma tela de Veículos foi tocada.
