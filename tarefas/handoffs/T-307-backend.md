# T-307 · Pix do boleto no Asaas e no falso · backend → qa, devops, arquiteto, orquestrador

**O que foi feito:**
- `Asaas._completar`, no boleto: depois da `identificationField`, `_pix_do_boleto` chama `GET /payments/{id}/pixQrCode` e põe o `payload` em `pix_copia_e_cola`. 400 do parceiro (`ParceiroRecusou`, a conta sem chave Pix): o boleto sai sem o Pix, com aviso no log ("Boleto {id} sem o Pix"), sem cancelar. Parceiro fora do ar: cancela o boleto e sobe, como já era.
- Falso: o boleto ganha `pix_copia_e_cola` (continua sem `qr_code_url`); `pagamentos.sem_pix_no_boleto()` simula "Pix não disponível" até o `limpar()`.
- `CobrancaExterna` e `FaturaAssinatura` já gravavam o `pix_copia_e_cola` que a cobrança devolve, de qualquer tipo; nada mudou nelas. A régua `AUT-03` já só escrevia o Pix quando havia código.
- O e-mail do boleto da assinatura (`plataforma/tasks.py`) só escreve "Pix copia e cola:" quando o código existe.
- Gravações em `tests/integracoes/gravacoes/asaas.json`: `boleto_rafael` com o `pixQrCode`, `boleto_sem_pix` (400) e `boleto_pix_fora_do_ar` (503 e o DELETE). Dados fictícios, montados pela documentação.
- `test_fin_04_sandbox_boleto_com_o_pix` em `test_t029_asaas_sandbox.py` (pontos 1 e 2 da T-305).

**Onde:** `backend/integracoes/pagamentos/asaas.py`, `falso.py`, `backend/apps/plataforma/tasks.py`.
**Contrato:** o de `docs/api/financeiro.md` da T-305; OpenAPI sem mudança.
**Regras cobertas:** FIN-04, PLT-02, PLT-13: `test_fin_04_boleto_traz_o_pix` (com e sem Pix, pela API de contas a receber), `test_fin_04_boleto_sem_pix_disponivel_nao_cancela` e `test_fin_04_boleto_com_o_pix_fora_do_ar_cancela` (Asaas pelas gravações), `test_plt_02_email_do_boleto_sem_linha_pix_vazia` (com e sem Pix), `test_plt_13_pagar_devolve_o_boleto_com_pix`. Rodei t307, t029 (aceitação e contrato), t148, t185b, t186b, t297 e t017: 146 passam; ruff e mypy limpos.
**O que ficou de fora:**
- **Sandbox não rodado:** não há `GIRO_ASAAS_SANDBOX_CHAVE` nesta máquina. Pontos 1 e 2 da T-305 seguem a conferir por quem tem a chave de sandbox (`GIRO_ASAAS_SANDBOX_CHAVE=... pytest tests/integracoes/test_t029_asaas_sandbox.py -k boleto_com_o_pix`). O teste pula, com o aviso, se a conta não tiver chave Pix.
- **Ponto 3 (boleto pago pelo Pix: `billingType` no `GET` e no webhook):** não dá para automatizar no sandbox; a baixa segue gravando a forma que o parceiro devolve. Fica para o arquiteto conferir à mão no sandbox.
- O texto "da {nome}" do e-mail do boleto segue como estava (a T-303 não o tocou).
**Próximo passo para quem recebe:**
- devops: chave Pix na conta principal do sandbox e rodar o caso do sandbox.
- qa: CA-ASS-10 e CA-ASS-63 podem conferir o Pix no e-mail do boleto.
- Conflito previsto com a branch t-303-regua-assinatura em `plataforma/tasks.py` (o boleto passou a usar `enviar_a_cada_um` lá): na junção, ficam os dois.
