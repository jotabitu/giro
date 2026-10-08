# T-044 · Contrato da API de importação por planilha · arquiteto → backend, frontend, seguranca, orquestrador

**O que foi feito:**
- `docs/api/importacao.md`: planilha modelo por tipo; envio com validação em segundo plano; lista de linhas com erro e mensagem pronta; "Corrigir aqui" revalidando a linha na hora; ignorar linha; importar as prontas pelos serviços de `veiculos` e `clientes`, uma linha por savepoint; limite do plano com `acima_do_limite` e aviso `IMP-03`; reimportar só o que faltou (seed: 83 + 3 = 86); passo da implantação e funil (`IMP-05`); auditoria por cadastro e um resumo por importação.
- ADR 0017: app novo `importacao` no nível 13 da ordem da ADR 0011, porque precisa chamar `veiculos` e `clientes`, e `empresas` (dono do assistente) fica acima deles.
- Modelo de dados: `Importacao` e `LinhaImportacao`, temporários (apagados em 30 dias), com as linhas de clientes cifradas.
- Também nesta branch: correção da ADR 0014 pedida pela segurança e pelo backend na T-033 (só AES-256-GCM com dado associado `empresa_id|tabela|campo|id_cifra`, e `id_cifra` único). Os commits `3d97997` e `407cac3` não estavam no PR da T-043 e chegam à `main` com o PR desta branch.

**Onde:** `docs/api/importacao.md`, `docs/decisoes/0017-app-importacao.md`, `docs/decisoes/0014-sessoes-e-dados-sensiveis.md`, `docs/decisoes/modelo-de-dados.md`, `docs/decisoes/README.md`.

**Regras cobertas:** IMP-02, IMP-03, IMP-05, PLT-03, VEI-01, CLI-01, CLI-03, AUD-09.

**O que ficou de fora:** importar locações em andamento (a tela manda cadastrar pela Nova locação, para gerar as parcelas certas); atualizar cadastros existentes pela planilha (linha repetida é erro).

**Próximo passo para quem recebe:**
- Backend (T-027): criar o app `importacao`; expor `validar_novo` em `veiculos.services` e `clientes.services` para a tela e a importação usarem a mesma validação; dependência nova `openpyxl` (registrar no PR).
- Segurança: conferir a leitura da planilha (sem fórmulas, limite de descompactação) e a guarda temporária com CPF cifrado.
- Frontend: passo "Importar dados" do assistente com dados falsos do contrato.
