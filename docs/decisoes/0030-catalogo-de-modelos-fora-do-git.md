# Catálogo de modelos fora do git, no armazenamento privado

**Status:** proposta · 20 out 2026 · T-338 · passa a aceita se o contrato com a FIPE proibir publicar a lista; se o contrato permitir, fica descartada e o CSV continua no repositório (T-257) · detalha a 0026 (item 7) e a 0009

## Contexto

O catálogo de marcas e modelos (`VEI-08`, ADR 0026, item 7) é o arquivo versionado `backend/apps/veiculos/dados/catalogo_modelos.csv`, lido uma vez por processo por `veiculos.catalogo.modelos()` e regravado por `atualizar_catalogo_modelos` (T-257). Hoje tem 29 modelos escolhidos à mão.

O dono escolheu a lista completa da FIPE licenciada (T-337, opção B). A FIPE diz no site oficial que todos os direitos são reservados e que não oferece download nem API. Então a lista só chega por contrato, e o repositório do Giro é público. Se o contrato proibir publicar a lista, ela não pode ir para o git, nem num commit que depois seja apagado, porque o histórico de um repositório público é copiado.

## Decisão

### 1. Onde a lista fica

- A lista completa fica no armazenamento privado da ADR 0009, no caminho fixo `public/catalogo/catalogo_modelos.csv`. Ela é igual para todas as empresas. O prefixo `public/` nunca é o schema de uma empresa, então o apagamento pelo prefixo `<schema>/` (ADR 0025) não chega nele.
- O formato é o mesmo de hoje: CSV em UTF-8 com `marca,modelo,tipo`, sem duplicatas e em ordem de marca e modelo, escrito por `catalogo.gravar_csv`.
- O CSV versionado continua no repositório, com a lista curta escolhida pela equipe (os modelos do seed e os dos testes, sem copiar a lista da FIPE). É ele que o desenvolvimento, os testes e a CI usam.

### 2. Qual lista o processo lê

- Uma configuração nova, `GIRO_CATALOGO_MODELOS`, com dois valores. `local` é o padrão e lê o CSV versionado. `armazenamento` lê o caminho do item 1 pelo `comum.arquivos.provedor()`.
- `catalogo.modelos()` continua lendo a lista uma vez por processo e guardando em memória. A chave normalizada é calculada nessa leitura, como pede a T-339.
- Se o `armazenamento` falhar ou o arquivo não existir, o processo usa a lista versionada e manda o erro ao Sentry sem o conteúdo. A rota e a leitura do CRLV-e continuam funcionando. Um modelo que falte na lista curta só faz a leitura mandar a dica (CA-247-05). Ficar sem catálogo nunca derruba o cadastro.
- Em produção, se o contrato estiver assinado, `prod.py` exige `GIRO_CATALOGO_MODELOS=armazenamento`, do mesmo jeito que já exige `GIRO_ARMAZENAMENTO=s3`. Homologação usa o mesmo bucket de produção para o catálogo, só leitura, ou uma cópia, como o devops preferir. A lista não vai para a imagem Docker, porque a imagem também é um artefato distribuível.

### 3. Como se atualiza

- `atualizar_catalogo_modelos <arquivo> --destino armazenamento` faz o que faz hoje (lê, filtra, tira duplicatas, ordena), mas grava no caminho do item 1 em vez do arquivo do repositório. Sem `--destino`, o comportamento atual continua, para a lista curta.
- Quem roda é a equipe (devops ou dono), dentro do contêiner do backend em produção, com o arquivo entregue pela FIPE. O arquivo vem pelo canal do contrato e nunca passa pelo repositório, por issue, por PR nem pelo chat dos agentes.
- A lista nova vale para cada processo quando ele reinicia. O comando avisa isso ao terminar, e o devops reinicia o backend e o worker. Com a atualização trimestral (T-337), não compensa recarregar a quente.
- A auditoria da plataforma registra `catalogo.atualizar` com a quantidade de modelos e o mês de referência da FIPE, sem a lista.

### 4. Proteção contra commit por engano

- `.gitignore` ganha `backend/apps/veiculos/dados/*fipe*` e `*.fipe.csv`, os nomes que a equipe usa para o arquivo entregue.
- Um teste confere que o CSV versionado tem no máximo 200 linhas. A lista completa tem milhares, então um commit por engano quebra a CI antes do merge.

## Consequências

- O repositório continua público, sem a lista licenciada.
- Produção depende do bucket também para o catálogo. Se o bucket falhar, a queda é suave: lista curta e mais dicas na leitura.
- Desenvolvimento e testes não veem a lista completa. A conferência com os CRLV-e reais (T-331) roda na máquina do dono, com o arquivo da FIPE e `GIRO_CATALOGO_MODELOS=armazenamento` no armazenamento falso.
- O preço de referência da `VEN-01`, se vier no mesmo contrato, segue a mesma regra: mora no banco ou no armazenamento privado e nunca no git. O desenho dele fica para o contrato de Vendas.
- Alternativa descartada: uma tabela no schema `public` carregada pelo comando. Pediria um app compartilhado novo (o `veiculos` é app de empresa, ADR 0011) e uma migração, para uma lista que só muda a cada trimestre. O arquivo no armazenamento mantém o `catalogo.py` como está.
