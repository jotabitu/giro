# T-214 · Onboarding-Filial e Desfazer cancelamento · design-system → orquestrador, frontend

**O que foi feito:** branch `t-214-onboarding-filial`, a partir da `origin/main` (T-211 já mesclada). Só telas de referência em `docs/telas/html/`.

- `Onboarding-Filial` (desktop e celular): saiu "Mesmo endereço do CNPJ · Rua Barão do Rio Branco...". Entraram CEP, rua, número, complemento, bairro e cidade (cidade e UF somente leitura), com o exemplo do seed: Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000. Abaixo, a nota "Este endereço também vai na nota fiscal da sua assinatura. Você muda só a nota em Administração › Assinatura." (`PLT-15`). O CEP preenche rua, bairro e cidade.
- `Admin-Assinatura` (desktop e celular): aviso de cancelamento marcado ("Assinatura cancelada. Você tem acesso até 21 nov. Depois disso, a empresa fica sem acesso e nada mais é cobrado.") com o botão "Desfazer cancelamento" (`PLT-06`), no topo, em `warning-soft` com texto `warning-ink`. Nenhum token novo.

**Regras cobertas:** PLT-06, PLT-15.

**Para quem recebe:**
- **Frontend:** o aviso aparece só quando a API devolve o cancelamento marcado (`acoes.desfazer_cancelamento`, T-194); a data de acesso vem da API. Quando o aviso aparece, o link "Cancelar assinatura" não faz sentido e deve sumir.
- **Orquestrador:** a tela de referência continua no estado de teste grátis (fatura de 21 out), então o aviso com "até 21 nov" mostra o estado de cancelamento sobre ela, não um estado completo da assinatura `ativa`. Se quiser a tela inteira no estado `ativa` cancelada (fatura de 22 nov cancelada, forma de pagamento cadastrada), é tarefa nova. O `Admin-Assinatura` também é tocado pela T-200 (#209), em outras linhas; pode haver conflito de merge simples.

**Próximo passo:** o orquestrador abre o PR. Só documentos e telas HTML, sem teste para rodar.
