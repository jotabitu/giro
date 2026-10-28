# T-367 · Lembrete de devolução · backend → orquestrador, qa

**O que foi feito:**
- `locacoes.services.lembrar_devolucoes(agora=None)` (`AUT-01`):
  - lembra a locação `ativa` com o fim previsto hoje, no fuso da filial;
  - o texto é o do modelo 11 de `docs/qa/criterios/whatsapp.md` (`texto_do_lembrete`), com o primeiro nome, a marca da locadora, o código, o horário do fim previsto e o endereço da filial (`endereco_da_devolucao`: logradouro, número, complemento quando tem, bairro e cidade);
  - o canal é o WhatsApp quando o cliente tem celular. Sem celular, o mesmo texto vai pelo e-mail, com o assunto "{marca}: lembrete de devolução" e o remetente com a marca (queda para o e-mail, "Mensagens pelo WhatsApp"). Sem os dois, nada sai;
  - sai uma vez por locação. A locação é travada, e o evento `locacao.lembrar_devolucao` (categoria operação, `depois` com o `canal`: `whatsapp`, `email` ou vazio) marca a lembrada. Rodar de novo no dia não manda outro, e a renovação que muda o fim também não. Não precisou de campo novo nem de migração.
- Tarefa `aut_01_lembrete_de_devolucao` (por empresa, com o módulo `locacoes_vistoria`, PLT-12) e `aut_01_lembrete_de_devolucao_de_todas`, no Beat às 08:00.
- `financeiro.services._remetente` virou `remetente`, para o e-mail do lembrete usar o mesmo remetente com a marca.

**Onde:** `backend/apps/locacoes/services.py`, `tasks.py` e `README.md`; `backend/config/settings/base.py` (Beat); `backend/apps/financeiro/services.py`.

**Contrato:** sem rota nova; o OpenAPI não muda.

**Regras cobertas:** AUT-01. Testes em `tests/aceitacao/test_t367_lembrete_devolucao.py`:
- `test_aut_01_lembrete_de_devolucao`: a LOC-2836 em 14 out às 08:00, com o texto exato do exemplo do modelo 11, uma vez só;
- `test_aut_01_so_no_dia_da_devolucao` (07 e 13 out, nada sai), `test_aut_01_renovada_nao_lembra_de_novo`, `test_aut_01_so_a_locacao_ativa`;
- `test_aut_01_sem_celular_vai_pelo_email`, `test_aut_01_sem_celular_e_sem_email_nada_sai`.

**O que ficou de fora:**
- O aceite do WhatsApp (`CLI-12`) ainda não existe no cadastro do cliente. Quando existir, o WhatsApp do lembrete passa a pedir celular e aceite, e o e-mail cobre quem não aceitou (CA-WPP-05). A troca é só a condição do canal em `lembrar_devolucoes`.
- A queda para o e-mail depois da falha da Meta (CA-WPP-06) entra com o provedor real de WhatsApp; o falso não falha.

**Próximo passo para quem recebe:**
- QA: incluir o `AUT-01` na cobertura de regras e, com o aceite (`CLI-12`), o caso do lembrete no CA-WPP-05.
