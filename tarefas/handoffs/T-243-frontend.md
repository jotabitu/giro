# T-243 · Editar veículo · frontend → qa, design-system

**O que foi feito:** a rota `/veiculos/{id}/editar` (`EditarVeiculo.tsx`) abre o formulário do `Veiculo-Novo` com os dados da ficha da API e grava com `PATCH /api/veiculos/{id}/` (já existia no backend, administrador e gerente; sem rota nova). Salvar volta à ficha. O botão "Editar" da ficha (desktop) deixou de ser desativado e abre a edição.

**Campos:** editáveis os que o contrato aceita: marca, modelo, anos, cor, Renavam, tanque, categoria, data e valor da compra. **Só leitura:** placa e chassi (o contrato não os muda no PATCH; corrigir erro de digitação é ação do administrador em `corrigir-identificacao`, sem tela ainda), km (`VEI-02`, o km sobe por leitura ou vistoria e nunca diminui) e filial (só por transferência, `VEI-04`). Opcional apagado vai como `null` e limpa o campo.

**Erros:** a mensagem da API volta no campo (ex.: "O Renavam tem 11 dígitos."); erro de campo sem lugar na tela vai no aviso do topo. O envio trava contra duplo clique. Quem não tem `acoes.editar` vê o aviso, sem formulário.

**Como conferi:** Next do worktree (porta 3100) com a API real, `rodrigo`, veículo de teste TST2B34: abre preenchido, Renavam curto dá 400 no campo, salvar com dados válidos volta à ficha com a cor nova. `tsc`, `eslint` e 508 testes passam. Testes novos em `EditarVeiculo.test.tsx` (formulário, campos só para leitura, perfil sem edição, PATCH no falso, corpo do PATCH, cliente HTTP real) e ajuste em `FichaVeiculo.test.tsx`.

**O que ficou de fora:**
- Corrigir placa ou chassi (`POST /api/veiculos/{id}/corrigir-identificacao/`, administrador): o pedido citava placa e chassi únicos com a mensagem da API no campo, mas o PATCH não os aceita. Falta tela; vira tarefa nova se o dono quiser, com `VEI-01`.
- Entrada da edição no celular: a referência da ficha no celular não tem botão Editar (o "Mais ações" segue desativado); a página de edição já funciona em 390px, só falta o atalho. Pedido ao design-system.
- Sem referência própria da edição: reaproveitei o `Veiculo-Novo` sem "Importar planilha", "Preencher pelo documento", "Salvar e cadastrar outro" e sem a nota de documentos; revisão visual do design-system pendente.
- Auditoria da edição e o valor de compra só para administrador e gerente são do backend (já existentes).

**Ambiente:** o teste no navegador alterou a cor e o Renavam do veículo TST2B34 (id 90) na Moto Rápida; o `make seed` limpa. Nada de migração.

**Próximo passo:** design-system revisa a edição; produto decide se entra a tela de "Corrigir identificação".
