# T-374 · Catálogo completo de modelos (é a T-339) · segurança → orquestrador, qa

A segurança fez esta tarefa no lugar do Backend, pelo "Pronto quando" da T-339 e pela ADR 0031 (fonte provisória da Parallelum).

**O que foi feito:**
- **`backend/scripts/baixar_catalogo_parallelum.py`:** fora do Django, só com a biblioteca padrão e sem dependência nova.
  - Lê `brands` e `brands/{code}/models` de `cars` (carro) e `motorcycles` (moto), sem `trucks`, com um pedido por segundo.
  - No 429, para com a mensagem e não grava meia lista.
  - Recusa URL fora da `BASE` em https.
  - Acrescentei 3 novas tentativas para a conexão que cai no meio, com 5 s e depois 10 s de espera, mas não para o 429. A primeira carga de verdade caiu por `RemoteDisconnected` depois de vários pedidos.
- **`atualizar_catalogo_modelos <arquivo> [<arquivo> ...]`:** continua compatível com um arquivo só.
  - Junta tudo, e o último arquivo vence, tanto na duplicata (pela chave e o tipo) quanto na grafia da marca.
  - Grafia da marca: a da lista própria (último arquivo); senão, a dos carros ("Honda"); senão, a que vier ("YAMAHA").
  - O modelo fica como vem.
- **Lista própria:** `dados/catalogo_modelos_proprios.csv`, com os 29 modelos de hoje.
- **Catálogo:** `dados/catalogo_modelos.csv` regravado com a carga de 28 out 2026.
  - 9.424 da Parallelum mais a lista própria: 9.441 modelos, cerca de 400 KB.
  - O comando foi `atualizar_catalogo_modelos <parallelum.csv> apps/veiculos/dados/catalogo_modelos_proprios.csv`.
- **Fonte citada:** em `dados/README.md` (com o roteiro de atualização trimestral) e na docstring de `catalogo.py`.
- **Chave calculada uma vez:** `Modelo.chave` e `Modelo.marca_normalizada` são calculadas na criação do `Modelo`, na leitura do CSV. `listar`, `achar_modelo` e a ordenação não normalizam mais a cada pedido.
- A rota, o formato do CSV e o texto "Da lista FIPE" não mudam.

**Testes:**
- `tests/test_t374_catalogo_parallelum.py`, sem rede: `test_vei_08_parallelum_tipos_e_csv`, `_para_no_429_sem_gravar`, `_tenta_de_novo_so_na_falha_de_rede` e `_fora_do_django` (só biblioteca padrão, e nenhum app importa o script).
- `tests/aceitacao/test_t374_catalogo_completo.py`:
  - O catálogo completo, com a lista própria inteira e uma grafia por marca.
  - A chave calculada na leitura.
  - `test_vei_08_catalogo_crlv_detran_moto_acha_um_modelo`: o PDF no leiaute do Detran dá "Honda / Pop 110i ES".
  - `test_vei_08_catalogo_crlv_detran_carro_com_versoes_vai_para_a_dica`: "FIAT/MOBI LIKE" começa duas versões da FIPE e vai para `dicas.marca_modelo` (CA-247-05).
  - O comando com dois arquivos.
- **T-257:** os testes que contam modelos (único, ambíguos, a lista do Pop) passam a rodar sobre a lista própria, pela fixture `lista_propria`. Com a FIPE, "HONDA/POP" e a lista do Pop têm mais versões, e o que eles conferem é a regra de achar, não o tamanho da lista.
- O `test_vei_08_le_os_9_campos` da T-265 continua achando "Pop 110i ES" no catálogo completo, porque a lista própria vence a duplicata.
- ruff, ruff format e mypy sem erro. Regressão nos 39 arquivos de teste de veículos, catálogo e CRLV: 788 passed, 5 xfailed.

**Para o qa:** conferir os 2 CRLV-e reais da T-331 na máquina do dono com o catálogo novo. Pelo padrão da FIPE, a moto deve achar o modelo, e o carro tende a ir para a dica.

**Para o PR:** a FIPE de referência é a de outubro de 2026, pela carga de 28 out 2026. O orquestrador confere antes de pôr na descrição.

**Próximo passo:** o orquestrador revisa e abre o PR.
