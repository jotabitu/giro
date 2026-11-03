# T-421 · Contrato e modelo dos campos do CRLV-e · arquiteto → backend, frontend, qa

**O que foi feito:** o contrato da `VEI-09` e da leitura no editar, a partir das regras do PR #459 (produto). Mergear o #459 antes deste: as regras citadas estão lá.

1. **Modelo de dados** (item 9): 12 colunas novas no `Veiculo`, todas opcionais: `potencia_cv`, `cilindrada_cc`, `especie` (enum do CTB), `tipo_documento` (o "tipo" do CRLV-e; o nome evita colidir com `tipo_veiculo`), `carroceria`, `lotacao`, `peso_bruto_kg`, `numero_motor`, `observacoes_crlv`, `rastreador_numero`, `rastreador_empresa`, `anotacoes`. Faixas como `CHECK`.
2. **`docs/api/veiculos.md`, seção "Dados do documento, rastreador e anotações":** blocos `documento`, `rastreador` e `anotacoes` no detalhe e nas respostas do `POST` e do `PATCH` (a Frota não traz); `documento.numero_motor` e `documento.observacoes` **ausentes** para vendedor, vistoriador e financeiro; `PATCH` por chave; tabela de formatos com as mensagens; erro com chave pontuada; auditoria no `veiculo.editar`.
3. **Leitura (`POST /api/veiculos/leitura-crlv/`):** `campos` e `lidos` ganham as 9 chaves pontuadas da `VEI-09` (`documento.potencia_cv` etc.); tabela de conversão do texto do CRLV-e para cada campo (potência 0 e "NÃO APLICAVEL" viram `null`, "02P" → 2, "0,29" → 290 kg, tipos do CTB com acento). O CA-247-01 passa a 16 campos.
4. **Leitura no editar (padrão A):** `POST /api/veiculos/{id}/leitura-crlv/`, igual à do cadastro, conferindo placa e chassi com o veículo (422 `crlv_outro_veiculo`, "Este CRLV-e é de outro veículo."); placa e chassi fora da resposta; não grava nem substitui o documento CRLV; o `PATCH` aceita o comprovante `leitura` amarrado ao veículo e à pessoa.

**Combinado com o Backend (03 nov):** a T-415 (branch `t-415-crlv-versoes`) entra primeiro. Ela não mexe em `crlv.py`, só em `veiculos/catalogo.py` e `veiculos/leitura.py`, e acrescenta só `dicas.candidatos` (e `campos.marca` quando todas as versões são da mesma marca). A implementação da T-421 começa da `develop` depois do merge da T-415, e o contrato não muda nada dela.

**Decisões técnicas minhas (não vieram do dono nem do produto):** blocos aninhados na API (`documento`, `rastreador`) e chaves pontuadas na leitura e no multipart; o suporte recebe o motor e as observações como o administrador (não são dado pessoal da `AUD-09`); no editar o comprovante não tem o SHA do arquivo, porque o PDF não vem no `PATCH`; o editar com placa e chassi não lidos recusa como leitura impossível.

## Backend (depois do merge da T-415)

- Migração das 12 colunas com os `CHECK`; seed do QXA-4B21 (linha "Dados do CRLV-e do QXA-4B21").
- Serializers do detalhe, do `POST` (JSON e multipart achatado) e do `PATCH` por chave; tirar as duas chaves pelo perfil.
- `crlv.py`: validadores e rótulos novos em `CAMPOS` (o leiaute do `CrlvDetran` dos testes já tem os rótulos); observações em várias linhas.
- Rota `POST /api/veiculos/{id}/leitura-crlv/` e o comprovante com o `id` do veículo.
- Testes listados no contrato (`test_vei_09_*`, `test_vei_08_*`); o do "9 campos" vira 16. OpenAPI e `api:gerar`.

## Frontend (depois do backend)

- Cadastro, editar e ficha a 1440 e 390: combustível visível; os campos com as unidades e "—" quando `null`; "Passageiro · Motocicleta".
- Motor e observações só quando a chave vem (nada de esconder por perfil na tela).
- Editar: "Preencher pelo documento" chamando a rota do veículo; a 422 `crlv_outro_veiculo` com a mensagem como vem; o comprovante no `PATCH`.

## QA

- Os PDFs fictícios da lista de `docs/qa/criterios/T-421.md`; CA-247-01 passa a 16 campos.
