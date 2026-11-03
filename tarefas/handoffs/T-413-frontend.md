# T-413 · Documentos do veículo · frontend → orquestrador

**O que foi feito:**
- Editar veículo: `DocumentosDoVeiculo.tsx`, painel abaixo do formulário (fora dele, para o Enter não salvar a edição). Para CRLV, IPVA, seguro e rastreador: nova validade, arquivo (PDF, JPG ou PNG, até 10 MB, conferido antes de enviar), "Substituir"/"Enviar" e, no CRLV, o ano do licenciamento. O erro da API aparece no campo `validade` ou em texto; sucesso diz que o anterior ficou no histórico. A página já só abre para quem tem `acoes.editar` (administrador e gerente).
- Ficha: cada documento ganha "Abrir" (URL assinada de 15 min, aba nova, `noopener`) ou "Sem arquivo", e "Ver o histórico" (carrega `GET /api/veiculos/{id}/documentos/historico/` só ao abrir; renovados aparecem como "Substituído"). Vale para desktop e celular.
- Cliente `veiculosApi.enviarDocumento` (multipart) e `historicoDeDocumentos`; o falso troca o ativo por tipo e guarda o substituído.
- `DocumentosDoVeiculo.test.tsx`: seção, substituição com histórico, erro de validade, 403 do vendedor, Abrir e as duas rotas reais. Suíte inteira (822), lint e typecheck passam.

**O que ficou de fora:** não conferi a 1440 e a 390 px no navegador. IPVA e rastreador ainda não estão como tipos no contrato `veiculos.md` (só CRLV e seguro); o envio segue o `POST` genérico e vale confirmar com o backend se ele aceita os dois. A tela não confere o tipo do arquivo além do `accept` do campo; a API decide.

**Próximo passo para quem recebe:** abrir o PR da branch `t-413-documentos-do-veiculo` para a `develop`, preencher o número no `tarefas/feito.md` e perguntar ao backend sobre os tipos `ipva` e `rastreador`.
