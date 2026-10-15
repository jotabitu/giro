# T-247 · Leitura do CRLV-e e da CNH-e por PDF (parte do produto) · produto → orquestrador, arquiteto, seguranca, design-system, qa

**O que foi feito:** escrevi a parte de produto da T-247. Branch `t-247-regras-leitura-pdf`, a partir da `origin/main` com o #239.

- `docs/regras-de-negocio.md`:
  - **`VEI-08` (nova), preencher pelo CRLV-e:**
    - o que se lê (9 campos): placa, chassi, Renavam, marca, modelo, ano de fabricação, ano do modelo, cor, combustível; marca e modelo pela lista do cadastro (FIPE), com o texto lido como dica quando não acha;
    - o que não se lê: a validade do CRLV (o documento traz o exercício, não a data); km, categoria, filial, valores, seguro; e nada do proprietário;
    - a pessoa confere antes de salvar: nada grava na leitura, os campos ficam marcados e editáveis, salvar passa pela `VEI-01`, e o PDF fica anexado como CRLV;
    - a leitura que falha não muda nenhum campo; só PDF, não foto.
  - **`CLI-11` (nova), preencher pela CNH-e:** 7 campos (nome, CPF, nascimento, registro, categoria, validade, 1ª habilitação); filiação, RG, naturalidade, foto e assinatura não se leem; mesma conferência; o CPF já cadastrado oferece abrir o cadastro; CPF e número da CNH fora do log e do evento.
  - **"Pontos em aberto"**, duas perguntas fechadas para o dono, com padrão:
    - fase: B, o CRLV-e no MVP e a CNH-e na fase 2;
    - o PDF da CNH-e vale pelas fotos da CNH no cadastro completo (`CLI-03`): A, vale.
  - Notas de mudança em Veículos e Clientes. O código `CLI-10` está no PR #241 (T-248); por isso a regra nova aqui é a `CLI-11`.
- `docs/qa/criterios/T-247.md`: CA-247-01 a 07 (veículo), 08 a 12 (cliente), com os arquivos de teste que o qa cria (CRLV-e do TBC-5H21 da tela e do QXA-4B21 do seed, CNH-e do Lucas Ferreira).
- `tarefas/backlog.md`: estado da T-247 e uma `[divergência]` para o design-system.

**Regras cobertas:** VEI-08, CLI-11, VEI-01, VEI-03, CLI-01, CLI-02, CLI-03, AUD-04, AUD-05.

**O que ficou de fora:** a técnica (ADR) e a revisão da segurança, abaixo; a fase e o PDF no lugar das fotos esperam o dono; o tamanho máximo do arquivo fica com o contrato.

**Para o arquiteto (ADR), o que a regra precisa que você responda:**
1. **Como ler:** pelo texto do PDF, pelo QR code do documento ou pelos dois. A regra pede os 9 e os 7 campos; diga quais o método garante e o que acontece com o resto (leitura parcial é aceita, `VEI-08`).
2. **Assinatura digital:** se a leitura confere a assinatura do Detran/Senatran. Se conferir, o documento com assinatura inválida cai em "Não conseguimos ler" (a regra já prevê). Se não conferir, diga o motivo; a conferência da pessoa continua obrigatória nos dois casos.
3. **Biblioteca nova** (dependência, motivo no PR) e **onde roda:** na requisição ou no Celery; a tela precisa da resposta enquanto a pessoa está no formulário.
4. **Limite de tamanho** e de páginas, e o tempo máximo da leitura.
5. **Nenhuma consulta externa** (Detran, Senatran, FIPE online) sem nova decisão: a regra só pede a leitura do arquivo; a lista FIPE é a do cadastro.
6. **O arquivo entre a leitura e o salvar:** onde fica (temporário ou já no armazenamento privado, `AUD-05`), por quanto tempo, e o que acontece se a pessoa desiste sem salvar (a regra pede que nada fique gravado como dado do veículo ou do cliente).
7. **Contrato:** rota de leitura que devolve os campos, quais foram lidos e o número de campos (a tela não conta), e o anexo do PDF ao salvar; o exercício do CRLV no documento do veículo.

**Para a segurança (revisão depois da ADR):**
1. CNH-e e CPF são dados pessoais: confirme que só os 7 campos saem da leitura, e que filiação, RG, naturalidade, foto e assinatura são descartados (nem log, nem Sentry, nem arquivo temporário além do necessário).
2. O CRLV-e traz nome e CPF ou CNPJ do proprietário: confirme que não são lidos nem guardados.
3. Upload de PDF: tipo real do arquivo, tamanho, PDF com script ou anexo embutido, PDF que trava o leitor; isolamento da biblioteca.
4. O suporte Giro (`PLT-07`, `AUD-09`): pode usar a leitura? A regra sugere que não use a da CNH-e, porque mostraria o CPF completo; decida e diga.
5. Limite de requisições na rota de leitura.
6. Se o PDF da CNH-e passa a valer pelas fotos (ponto em aberto), o anexo segue a `AUD-05` (link de 15 minutos).

**Para o design-system:** a `[divergência]` do backlog (`Veiculo-Novo-Mobile` fala em fotografar; a regra lê só o PDF) e as telas `Cliente` sem a leitura, quando o dono decidir a fase.

**Para o qa:** os arquivos de teste da lista do topo dos critérios.

**Próximo passo:** o dono responde os dois pontos em aberto; o arquiteto escreve a ADR; a segurança revisa; o orquestrador numera backend e frontend.
