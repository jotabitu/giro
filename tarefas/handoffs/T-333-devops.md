# T-333 · libharfbuzz-subset0 e imagem com WeasyPrint 70 · devops

**O que foi feito:** a `giro-backend:latest` foi reconstruída a partir de `origin/t-333-weasyprint-70` (alvo `dev`): WeasyPrint 70.0, e um PDF de teste gera sem o aviso do fontTools. Acrescentei `libharfbuzz-subset0` em `infra/docker/backend.Dockerfile` (camada `base`, vale para `dev` e `producao`) e no passo "Dependências do sistema (WeasyPrint)" do `.github/workflows/ci.yml`. Na imagem entra a 6.0.0 do Debian bookworm.

**Por quê:** a WeasyPrint 70 passou a preferir o HarfBuzz-Subset (4.1.0 ou mais novo) ao fontTools para reduzir as fontes embutidas no PDF, e avisa no log "Using fontTools instead of HarfBuzz-Subset" quando não o encontra. Funcionava sem ele; a biblioteca tira o aviso e usa o caminho que a 70 prefere. A versão 6.0.0 atende o mínimo de 4.1.0.

**ADR:** não pede. A regra do CLAUDE.md é "dependência de infraestrutura nova pede ADR", e infraestrutura aqui é peça como banco, fila e nuvem (`devops.md`). A `libharfbuzz-subset0` é uma biblioteca de sistema do mesmo pacote-fonte (harfbuzz) da `libharfbuzz0b` que a imagem já instala, para o mesmo uso (PDF). Não troca nem acrescenta peça de arquitetura.

**Testes:** `dpkg -l` na imagem mostra o pacote; `HTML(...).write_pdf()` roda na 70.0. O alvo `producao` também foi construído com sucesso e a imagem de teste foi removida. O CI não foi executado (só passo de apt).

**Não mexi:** pilha `giro`, `giro-backend-pg`.

**Próximo passo para quem recebe:** (orquestrador) integrar com o PR da T-333; a pilha `giro` precisa de rebuild do backend depois do merge.
