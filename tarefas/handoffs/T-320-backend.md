# T-320 · OpenAPI das Movimentações sem nomes repetidos · backend → frontend, qa, orquestrador

**O que foi feito** (os três pontos do handoff da T-289):
1. **Nomes únicos:** os serializers das movimentações ganharam `ref_name`: `VeiculoDaMovimentacao` (com `modelo` e `status`), `LinhaDaMovimentacao`, e também `RefDaMovimentacao`, `FotoDaMovimentacao`, `AcoesDaMovimentacao` e `FotoEntradaDaMovimentacao`, que colidiam com os de financeiro, vistorias e plataforma. O `spectacular --validate` não acusa mais nenhum componente repetido.
2. **`Quadro.colunas[].itens`** aponta para `LinhaDaMovimentacao`; a `Linha` da importação ficou só dela.
3. **O quadro aceita e declara `?levando=eu` e `?busca=`** (código ou placa), pelo mesmo filtro da lista (`selectors._levando_e_busca`). Contrato atualizado em `docs/api/movimentacoes.md`.
- Enums com nome fixo em `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]`: `MovimentacaoStatusEnum` (o nome que o frontend usa; com a troca dos componentes, ele virava um hash), `FotoPosicaoEnum` (vistorias, o nome que já saía) e `PosicaoDaChegadaEnum` (movimentações). Sobra só o aviso do `TipoA50Enum`, que já existia na `main`.
- **Frontend:** `npm run api:gerar`; em `lib/api/tipos-movimentacoes.ts`, `VeiculoDaMovimentacao`, `LinhaDaMovimentacao`, `AcoesDaMovimentacao` e `FotoDaChegada` vêm agora do gerado. O falso das movimentações perdeu `id` e `tirada_em` nas fotos da chegada, que a API não manda (vinham do `Foto` da vistoria, que o gerador misturava).

**Onde:** `backend/apps/movimentacoes/api/serializers.py`, `api/views.py`, `selectors.py`, `backend/config/settings/base.py`, `docs/api/openapi.yaml`, `docs/api/movimentacoes.md`, `frontend/src/lib/api/schema.d.ts`, `frontend/src/lib/api/tipos-movimentacoes.ts`, `frontend/src/testes/falsos/falso-movimentacoes.ts`.
**Contrato:** `GET /api/movimentacoes/quadro/` com `levando` e `busca`; componentes renomeados (ver acima).
**Regras cobertas:** MOV-01: `test_mov_01_openapi_com_nomes_proprios`, `test_mov_01_quadro_com_busca_e_levando`. t320, t288 e t288b: 34 passam; ruff e mypy limpos. Frontend: typecheck e lint limpos, `src/components/movimentacoes`: 25 passam.
**O que ficou de fora:** a tela do quadro ainda filtra a busca no que já veio (T-289); passar a mandar `?busca=` à API é do frontend.
**Próximo passo para quem recebe:**
- frontend: conferir os tipos gerados e, se quiser, trocar a busca local do quadro pela da API.
