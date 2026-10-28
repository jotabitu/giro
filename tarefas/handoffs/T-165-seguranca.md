# T-165 · Fotos da vistoria em PNG com paleta perdem as cores · segurança → orquestrador

A segurança fez esta tarefa no lugar do Backend. Foi ela quem levantou o problema, na T-153.

**O que foi feito:**
- O problema estava em `comum.arquivos.sem_metadados`: ele criava a imagem nova no mesmo modo e colava os pixels.
  - Num PNG em modo `P`, a imagem nova saía sem a paleta, e as cores viravam os índices em tons de cinza ou preto. Um pixel `(220, 30, 40)` saía `(0, 0, 0)`.
- Agora, antes de criar a imagem limpa:
  - a imagem em `P` ou `PA` é convertida para `RGB`;
  - a que tem `tRNS` (também em `L` ou `RGB`) vai para `RGBA`, e a transparência passa para o canal alfa.
- A imagem gravada continua sem metadados: nem texto, nem EXIF, nem `tRNS` solto.
- JPG e PDF não mudam.

**Testes:**
- `test_vis_02_png_com_paleta_mantem_as_cores` (2 casos: paleta sem e com `tRNS`), em `comum/tests/test_arquivos.py`.
  - Compara os pixels em RGBA da imagem enviada com os da imagem limpa.
  - Confere a cor de um pixel, o índice transparente com alfa 0 e a saída do comentário com GPS.
  - O código antigo dava `(0, 0, 0)` no pixel conferido.
- ruff, ruff format e mypy sem erro.
- Regressão nos 16 arquivos de teste com fotos, notas e PNG (vistorias, movimentações, despesas, logo, clientes, titular): 506 passed.

**Quadro:** a T-165 saiu do backlog e entrou uma linha no `feito.md`.

**Próximo passo:** o orquestrador revisa e abre o PR.
