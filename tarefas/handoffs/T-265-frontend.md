# T-265 · Leitura do CRLV-e (tela) · frontend → qa, seguranca, orquestrador

**Branch:** `t-265b-leitura-crlv-tela`, empilhada sobre a `t-265-leitura-crlv` (PR #352, que está sobre o #351 da T-257). Abrir o PR depois deles. `npm run api:gerar` rodado: sem mudança no cliente além do que o backend já comitou.

**O que foi feito** (`Veiculo-Novo`, desktop e celular, o mesmo componente):
- `PreencherPeloCrlv.tsx`: o cartão "Preencher pelo documento" com "Enviar CRLV-e" (só `.pdf`), "Trocar" e "Remover o CRLV-e". Mostra o `rotulo` da API como vem e, quando `dicas.marca_modelo` vem, o texto lido para a pessoa escolher a marca e o modelo.
- Recusas: 422 `VEI-08`, 429 e 503 `leitura_ocupada` com a mensagem da API (`mensagemDoErro`); 400 com o texto do campo `arquivo`. Nenhum limite ou regra de arquivo na tela (o 2 MB e o `%PDF-` são da API).
- `NovoVeiculoForm`: os campos de `lidos` entram no formulário e ficam com a dica "Lido do documento" enquanto o valor é o lido; se a pessoa mudar, volta a dica de sempre (a API calcula `corrigidos`). Nada é salvo antes de "Salvar veículo".
- Com o CRLV lido aparece "Validade do CRLV" (a leitura não traz a validade, `VEI-08`); o erro 400 "Informe a validade do CRLV." cai nesse campo.
- Salvar: `veiculosApi.criar(corpo, crlv?)` vai em `multipart/form-data` com os campos do cadastro, `combustivel` (se foi lido), `crlv_arquivo`, `crlv_validade`, `crlv_exercicio` (se veio) e `leitura`. Sem CRLV segue em JSON.
- Modelo pela lista: `GET /api/veiculos/modelos/` (`tipo`, `marca` e o texto digitado como `busca`) alimenta um `datalist`; "Da lista FIPE" na dica quando o modelo é um da lista. Fora da lista a pessoa digita à mão (CA-247-05). A Marca segue texto livre.
- API falsa (`falso-frota.ts`): `lerCrlv` (arquivo com "crlv" no nome lê os 9 campos; outro PDF dá o 422) e `modelos`.

**Onde:** `frontend/src/components/frota/{PreencherPeloCrlv,NovoVeiculoForm}.tsx`, `src/lib/{veiculos,api/veiculos,api/tipos-frota}.ts`, `src/testes/falsos/falso-frota.ts`.

**Regras cobertas:** VEI-08, VEI-01. Testes: `PreencherPeloCrlv.test.tsx` (mensagens das recusas), `lib/veiculos.test.ts` (`valoresDaLeitura`), `lib/api/veiculos.test.ts` (multipart, leitura 422/503, catálogo), `NovoVeiculo.test.tsx`. typecheck e lint do frontend limpos; testes de `components/frota`, `lib/veiculos` e `lib/api/veiculos` passam.

**Para conferir:**
- O gerador deu ao catálogo o tipo `ListaDeModelos`, o mesmo nome do de contratos (o OpenAPI tem dois schemas com esse nome; o `ModeloResumo` gerado é o do contrato). Por isso `ModeloDoCatalogo` está escrito à mão em `tipos-frota.ts`. Para o backend/arquiteto: dar nome único ao schema do catálogo (ex.: `ModeloDoCatalogo`) e gerar de novo.
- O celular da referência diz "Fotografar o CRLV para preencher"; o contrato só lê PDF (foto dá 400), então os dois tamanhos têm "Enviar CRLV-e".
- Ficou de fora: a verificação no navegador em 1440px e 390px com a API real (não subi o backend aqui), e a calibração com CRLV-e reais (equipe, fora do repositório).
