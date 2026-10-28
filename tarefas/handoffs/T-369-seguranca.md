# T-369 · Pedido do titular pela equipe (M-03 da T-355) · segurança → orquestrador, produto

Feita pela segurança no lugar do Backend, que está com a fila cheia.

**O que foi feito:** a equipe Giro atende o pedido do titular (`AUD-06`) sem SQL direto, até a tela da fase 2. O serviço está em `apps/clientes/titular.py`, e os comandos em `apps/clientes/management/commands/`.

```sh
python manage.py exportar_titular <schema> <cliente_id> --dono <email> --motivo "Chamado 4521" --saida lucas.zip
python manage.py anonimizar_titular <schema> <cliente_id> --dono <email> --motivo "Chamado 4521" --confirmacao "<nome do cliente>"
```

- **Quem pode:** só o Dono ativo da plataforma (`--dono`, conferido no `public`), sempre com motivo. Suporte e financeiro da equipe são recusados, porque a exportação traz CPF e CNH completos, que o suporte nunca vê (`AUD-09`).
- **Auditoria:** cada pedido grava um evento na auditoria da empresa, com o ator "Equipe Giro: <nome>" (tipo `suporte`), o motivo e a regra `AUD-06`, que a empresa vê (`AUD-03`). Grava também `empresa.exportar_titular` ou `empresa.anonimizar_titular` na auditoria da plataforma, só com o id do cliente. A anonimização registra o antes e o depois com a máscara de sempre: nada do nome nem do CPF fica no evento.
- **Exportar:**
  - O comando gera um ZIP com `dados.json` (o cadastro com CPF, CNH e CPF do responsável decifrados, mais as locações, os contratos, as contas a receber e os reembolsos do cliente), os documentos (inclusive os substituídos e o `cnh_digital`, B-05 da T-247) e os PDFs dos contratos.
  - O arquivo nasce com permissão 0600 e nunca sobrescreve outro. A equipe entrega ao administrador da empresa e apaga.
- **Anonimizar:**
  - Segue o `clientes.md` ("LGPD do titular"):
    - Os cifrados são apagados e os hashes trocados por valores aleatórios, então o CPF fica livre para um cadastro novo.
    - O nome vira "Cliente anonimizado", e contato, endereço, nascimento e referência são apagados.
    - O momento fica gravado em `anonimizado_em`.
  - Os documentos ficam inativos e sem arquivo. O arquivo é apagado do armazenamento depois do commit.
  - O cadastro volta a `incompleto` (`CLI-03`).
  - Recusas:
    - 422 `cliente_com_pendencia`, com locação, venda ou valor em aberto, pelos mesmos contadores do inativar.
    - Cliente já anonimizado.
    - Confirmação diferente do nome.
- **Recusas comuns:** empresa já apagada (`AUD-08`) e cliente que não é daquela empresa.

**Testes:**
- `tests/test_t369_titular.py`, 5 passed:
  - `test_aud_06_exportar_titular_entrega_os_dados_completos_e_audita`
  - `test_aud_06_anonimizar_titular_apaga_dados_e_arquivos_e_audita`
  - `test_aud_06_titular_so_pelo_dono_com_motivo_e_confirmacao`
  - `test_aud_06_anonimizar_recusa_cliente_com_pendencia`
  - `test_aud_06_titular_recusa_empresa_apagada_e_cliente_de_outra`
- Regressão de `tests/*.py`, `test_t014_clientes.py`, `apps/clientes` e `comum`: 322 passed.
- ruff, ruff format e mypy: sem erro.

**Pontos para quem revisa:**
- O texto final e os PDFs dos contratos continuam com o nome e o CPF. Registrei a dúvida em `tarefas/backlog.md` como `[decisão]` para o produto, com o padrão (ficam, porque o PDF assinado é a prova no prazo legal) e a alternativa.
- O módulo lê `locacoes`, `contratos` e `financeiro` por `apps.get_model`, sem importar os apps, porque é uma ferramenta da equipe e não uma regra de negócio. A tela da fase 2 pode trocar isso pelos fornecedores da ADR 0015.
- Os comandos rodam na conexão que o servidor tiver. Em produção, devem rodar no contêiner da aplicação (`giro_app`), nunca com a conexão de migração.

**Próximo passo:** o orquestrador revisa e abre o PR; o produto responde a `[decisão]` dos contratos.
