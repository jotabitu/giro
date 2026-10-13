# T-136 · Permissões por perfil na API e menu do perfil · backend → frontend, seguranca, qa

**O que foi feito (parte da API):**

- **Menu (`USR-05`, item "Inclui" da T-141):** `menu_completo` por perfil em `GET /api/auth/eu/`, como em `docs/api/contas.md`.
  - Variante `vistoriador`: `menu_completo` igual ao `menu_inicio` (Vistorias de hoje, Consultar veículo, Avarias abertas), sem `inicio` e sem `locacoes`.
  - `locacoes` só com `locacoes_criar`; `inicio` só para quem vê painel (todos menos o vistoriador).
  - O rótulo de `inicio` no menu completo é o do início do perfil: Visão geral (administrador), Visão da filial (gerente), Início (vendedor e financeiro).
  - `barra_celular` tem `veiculos` também quando o menu tem `consultar_veiculo`. João: `["inicio", "veiculos", "mais"]`.
- **Clientes (`USR-09`, D-26, D-28, D-29):**
  - O vistoriador recebe 403 `{ "codigo": "permissao", "mensagem": "Seu perfil não tem acesso a esta ação." }` em `GET /api/clientes/` e em `GET /api/clientes/{id}/`.
  - O financeiro recebe na ficha a variante nova "ficha do financeiro" (`ClienteDoFinanceiroSerializer`): a resumida mais `email` e `bloqueio` (o mesmo bloco da completa, com motivo e descrição).
  - Nessa variante, `acao_principal` só vem quando é `cobrar` (`CLI-07`); nos outros casos vem `null`. Não traz documento, CNH, endereço, referência, documentos, pendências nem análise.
  - A lista do financeiro continua resumida. Editar, bloquear, desbloquear, inativar, reativar e análise continuam 403 para ele.
- **Veículos (D-25):** o vistoriador recebe a frota, a ficha e `GET /api/categorias/` sem nenhum campo `_centavos` e sem `preco_vigente`, `proximo_preco`, `indicadores_financeiros` e `data_compra`. As chaves vêm ausentes, não `null`.
  - `GET /api/categorias/{id}/precos/` e `GET /api/extras/` respondem 403 a ele.
  - Os outros perfis não mudam.
- **Vistoria (`USR-09`, `CLI-02`, `CLI-03`):** o bloco `cliente` da vistoria passa a ser `{ nome, celular, cnh, retirada_liberada }`.
  - `retirada_liberada` vem na saída: `true` quando nada do cliente impede a retirada (cadastro, CNH, bloqueio, inativo). Na devolução vem `null`.
  - É tudo o que o vistoriador vê do cliente.
- **Locações (D-27):** nada mudou no código, que já cumpria a regra. O teste novo confirma que a Lúcia lê a ficha inteira (parcelas, preços, contrato, histórico) e que as `acoes` dela são só `receber` (e `imprimir_contrato`, que é leitura).
  - Renovar, cancelar, simular cancelamento, reenviar contrato, vistoria, devolução, troca e editar respondem 403 a ela.
  - A lista com `?cliente=` continua aberta ao financeiro, porque a ficha do cliente usa essa lista.

- **Contadores do menu:** seguem o menu (`painel.md`), então João passa a receber só `agenda` e `avarias`, sem `locacoes` (antes 42, o total de todas) e sem `veiculos`. `test_usr_05_contadores_seguem_o_menu` foi ajustado.
- **Frontend:** só `src/testes/falsos/falso-vistorias.ts`, com `celular` e `retirada_liberada` no bloco `cliente`, para o typecheck passar com o OpenAPI novo. `api:gerar`, `typecheck`, `lint` e a suíte do frontend (303 testes) passam.

**Onde:**

- `backend/apps/contas/navegacao.py`
- `backend/apps/clientes/selectors.py`, `backend/apps/clientes/api/views.py`, `backend/apps/clientes/api/serializers.py`
- `backend/apps/veiculos/selectors.py`, `backend/apps/veiculos/api/views.py`, `backend/apps/veiculos/api/serializers.py`
- `backend/apps/vistorias/selectors.py`, `backend/apps/vistorias/api/serializers.py`
- Os READMEs dos apps.

**Contrato:** `docs/api/clientes.md` (quem pode, ficha do financeiro, GETs), `docs/api/veiculos.md` (vistoriador sem valores, 403 em preços e extras), `docs/api/vistorias.md` (bloco `cliente`) e `docs/api/openapi.yaml` regenerado. O `contas.md` já descrevia o menu (T-141) e não mudou.

**Regras cobertas:** `USR-05`, `USR-09`, `AUD-04`, `CLI-02`, `CLI-03`. Testes:

- `test_usr_05_menu_completo_do_vistoriador` e `test_usr_05_usr_08_navegacao_por_perfil` (ajustado: rótulos do início e João com um menu só).
- `test_usr_09_vistoriador_nao_abre_lista_nem_ficha_do_cliente` e `test_usr_09_financeiro_ficha_do_cliente_com_contato_e_financeiro` (`test_t014_clientes.py`).
- `test_usr_09_vistoriador_ve_veiculo_sem_valores` (`test_t013_veiculos.py`).
- `test_usr_09_financeiro_ficha_da_locacao_so_para_leitura` (`test_t015_locacoes.py`).
- `test_usr_09_vistoria_traz_do_cliente_nome_celular_e_retirada` (`test_t016_vistorias.py`).
- Testes antigos ajustados à regra nova: CA-014-07 e CA-014-08 (João fora da lista e da ficha), CA-013-03 e CA-013-21 (João sem valor de compra e sem preço nas categorias).

**O que mudou no contrato para o frontend (T-136, parte do frontend):**

1. `GET /api/clientes/` e `GET /api/clientes/{id}/` dão 403 ao vistoriador. A rota `/clientes` e a ficha mostram "Seu perfil não tem acesso" para ele.
2. A ficha do cliente para o financeiro (`perfil === "financeiro"` no `eu`) traz `email` e `bloqueio`, e não traz `documento`, `cnh`, `endereco`, `documentos`, `pendencias` nem `analise`. Ela mostra:
   - contato (celular e e-mail) e a situação com o motivo do bloqueio (`bloqueio.descricao`);
   - as locações (`GET /api/locacoes/?cliente=`);
   - o financeiro do cliente (`financeiro` da ficha e `GET /api/financeiro/contas-receber/?cliente=`): total pago, em aberto, parcelas atrasadas com `dias_atraso` e pagamentos;
   - Cobrar como única ação, quando `acao_principal.codigo === "cobrar"`.

   No OpenAPI, a resposta de `GET /api/clientes/{id}/` continua declarada como `ClienteDetalhe`, que já tem `email` e `bloqueio`. Como hoje, o tipo do frontend precisa tratar os campos da completa como opcionais conforme o perfil.
3. Veículos para o vistoriador: `preco_vigente`, `valor_venda_centavos`, `referencia_fipe_centavos`, `valor_compra_centavos`, `data_compra` e `indicadores_financeiros` ficam opcionais no OpenAPI (ausentes para ele); `preco_vigente` e `proximo_preco` das categorias também. A Frota e a ficha do João escondem a coluna "Diária" e os valores quando a chave não vem. Preços e extras dão 403 para ele.
4. Vistoria: `cliente.celular` (obrigatório) e `cliente.retirada_liberada` (`boolean | null`). A tela de vistoria pode mostrar "Retirada liberada" ou o impedimento (o motivo continua em `pendencias`).
5. Menu: o frontend já desenha o que vem em `navegacao`. A parte de `gruposDaRota` em `frontend/src/lib/menu.ts` (usar o `menu_inicio` nas rotas que os itens dele abrem) e o teste com `usr_05` continuam com o frontend, como no "Inclui" da T-136.
6. Rotas que o menu do perfil não mostra: a API responde 403 onde o contrato não dá acesso (vistoriador em clientes, preços e extras; financeiro em vistorias e nas ações da locação). Veículos e a lista de locações continuam abertos ao financeiro, pelo contrato: "Ver frota e ficha" é de todos, e a ficha do cliente usa a lista de locações com `?cliente=`. O guarda de rota do frontend (D-26) segue o menu.

**Verificação:** `ruff check`, `ruff format --check`, `mypy` e a suíte inteira do backend (726 testes) passam; o OpenAPI foi gerado com `--validate`.

**O que ficou de fora:**

- O frontend inteiro da T-136. A T-136 continua no backlog até ele.
- O vistoriador ainda lança despesa de manutenção com valor (tabela de perfis: "Lançar despesa: sim (manutenção)"). Isso não mudou.

**Próximo passo para quem recebe:**

- **frontend:** os itens 1 a 6 acima. Rode `npm run api:gerar` depois do merge (o `schema.d.ts` não vai para o git).
- **seguranca:** revisar o 403 por perfil (clientes, preços, extras) e o recorte de valores do vistoriador.
- **qa:** conferir no compose com João e Lúcia os itens D-25 a D-29 da conferência.
