# T-206 · Mensagens da API nas telas de saída e de caixa · frontend → orquestrador, qa

**O que foi feito:**
- **D-02 (VEI-01):** a vistoria só devolve o código curto da pendência (`"km"`), então a mensagem vem do 422 da conclusão. Depois de salvar um km que a API ainda aponta como pendência, a tela chama `POST /api/vistorias/{id}/concluir/` (com o km pendente ela nunca conclui), pega a pendência `VEI-01` e mostra a mensagem no campo do km ("O km informado é menor que o atual…") com o link "Corrigir km". O texto sob o botão deixa de dizer "Informe a quilometragem" quando o km foi informado. Vale para a saída e a chegada (mesmo painel).
- **D-03 (FIN-01):** o Caixa do dia sem caixa aberto diz "O caixa de hoje ainda não foi aberto. Abra o caixa do dia para receber." A tela de receber já mostrava a mensagem do `FIN-07` vinda da API.

**Onde:** `lib/vistorias.ts::avisoDoKmDaApi`, `components/vistorias/{useVistoriaEmEdicao,PartesDaVistoria,VistoriaDeSaida,Devolucao}`, `components/financeiro/CaixaDoDia.tsx`. O falso (`testes/falsos/falso-vistorias.ts`) agora marca `km` como pendência também quando o km é menor, como a API real.
**Testes:** `t_206_a_mensagem_da_api_chega_ao_campo_do_km` e o do caixa fechado em `Financeiro.test.tsx`. `npm test` (463), `tsc` e `eslint` limpos. Não conferi no navegador.
**Sugestão ao backend (opcional):** devolver a mensagem da pendência no `GET` da vistoria evitaria a chamada extra ao `concluir`.
**Próximo passo para quem recebe:** o QA tira o envelope `defeitoConhecido` de D-02 e D-03 em `e2e/suporte/passos.ts`. O orquestrador abre o PR.
