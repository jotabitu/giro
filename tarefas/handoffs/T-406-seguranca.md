# T-406 · Marcas do CRLV-e real no catálogo · segurança → orquestrador, qa

Achado do E2E da T-375 (item 5), sobre a T-374.

**O que foi feito:**
- `veiculos/catalogo.py`: `APELIDOS_DO_DETRAN` liga a marca como o Detran escreve às marcas do catálogo, e `achar_modelo` procura também com elas:
  - RE → Royal Enfield;
  - CHEVROLET → GM - Chevrolet;
  - GM → GM - Chevrolet e Chevrolet;
  - VW → VW - VolksWagen e Volkswagen;
  - VOLKSWAGEN → VW - VolksWagen;
  - M.BENZ → Mercedes-Benz;
  - MMC → Mitsubishi;
  - KIA → Kia Motors;
  - H.DAVIDSON → Harley-Davidson;
  - CHERY → Caoa Chery.
- O "I/" do importado sai antes da marca. Só a marca, mesmo pelo apelido, continua não bastando.
- Lista própria: entrou "Royal Enfield, Classic 350". O catálogo foi regravado pelo comando e mudou só essa linha (9.442 modelos).

**Resultado com os textos dos 2 CRLV-e reais:**
- **Moto:** "RE/CLASSIC 350" preenche Royal Enfield / Classic 350.
- **Carro:** "CHEVROLET/CRUZE LT NB" continua na dica, pela CA-247-05. A marca agora vale, mas o "Cruze LT" tem as versões 1.4 e 1.8 na FIPE, e o "NB" do Detran não as separa. Para preencher, seria preciso um "Cruze LT" genérico na lista própria, e isso é decisão de produto, não desta tarefa.

**Testes:** `tests/aceitacao/test_t406_marcas_crlv.py`, com PDFs fictícios no leiaute do Detran e sem os reais:
- `test_vei_08_marca_do_detran_pelo_apelido`;
- `test_vei_08_carro_com_versoes_continua_na_dica`;
- `test_vei_08_crlv_detran_moto_re_classic_350`;
- `test_vei_08_crlv_detran_carro_chevrolet_cruze_lt_nb`.

Com as suítes da T-257, T-374, T-265, T-331 e T-328, foram 72 passed. ruff e mypy sem erro.

**Fica para depois:** o catálogo tem "Chevrolet" (lista própria) e "GM - Chevrolet" (FIPE) como marcas diferentes, e o mesmo vale para "Volkswagen" e "VW - VolksWagen". Na leitura, os apelidos resolvem. No filtro `?marca=` da lista de modelos, as duas grafias continuam separadas. Uma tarefa futura pode juntá-las no comando.

**Próximo passo:** o orquestrador revisa e abre o PR. O qa confere de novo os 2 reais.
