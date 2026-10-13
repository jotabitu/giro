# app `clientes`

**Schema:** empresa
**Escopo:** Clientes PF/PJ, CNH, documentos, contatos, bloqueio, consentimento LGPD.
**Regras:** CLI, AUD-04, AUD-05, AUD-06, AUD-09, APR-05 (ver `docs/regras-de-negocio.md`)
**Telas:** Clientes, Cliente (ver `docs/telas/README.md`)

## Estrutura esperada

```
clientes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/clientes.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-014)

- `models.py`:
  - `Cliente`, uma máquina de estados (`incompleto`, `ativo`, `bloqueado`, `inativo`; `REGRA_TRANSICAO = "transicao_cliente"`). CPF ou CNPJ, CNH e CPF do responsável ficam em `CampoCifrado`, com `CampoHashBusca` (o do documento é único, `CLI-01`). `CHECK` no banco: bloqueado sempre com `bloqueio_motivo`, e só ele;
  - `CAMPOS_AUDITORIA`: nome (iniciais), nascimento (ano), contatos, endereço e referência mascarados; cifrados e hashes omitidos;
  - `DocumentoCliente`, um ativo por tipo, com o arquivo no armazenamento privado (`comum.arquivos`).
- `services.py`:
  - `cadastrar` e `editar` (`CLI-01`, `CLI-03`): só tipo, nome, documento e celular são obrigatórios. `acertar_cadastro` leva entre `incompleto` e `ativo` conforme as pendências; bloqueado e inativo não mudam por ali;
  - `enviar_documento`: confere o conteúdo (`arquivos.validar`), reprocessa a foto sem metadados (`arquivos.sem_metadados`) e deixa o anterior inativo;
  - `bloquear` e `desbloquear` (gerente e administrador, `CLI-05`); `pedir_desbloqueio` abre o `APR-05` pela porta `comum.aprovacoes` (vendedor); `aplicar_desbloqueio_aprovado` é a volta;
  - `bloquear_por_atraso` e `desbloquear_por_quitacao`, chamados pelos assinantes de `financeiro.parcela_atrasou` e `financeiro.parcela_paga`;
  - `inativar` e `reativar` (`CLI-09`).
- `selectors.py`:
  - `pendencias`, `situacao_da_cnh`, `analise` e `analise_de_dados` (`CLI-02`, `CLI-04`);
  - a interface para os outros apps: `impedimentos_para_retirada`, `impedimentos_para_nova_locacao` e `impedimentos_para_venda`;
  - `resumida`, `do_financeiro` (`USR-09`: a resumida com e-mail e bloqueio, e só Cobrar) e `completa` (`AUD-04`); `PERFIS_QUE_VEEM` deixa o vistoriador fora da lista e da ficha (403, `USR-09`); `pode_ver_completo` nega o completo ao suporte em qualquer modo (`AUD-09`). Cada URL de documento gerada grava `documento_cliente.ver` (`AUD-05`);
  - a lista: `filtrar`, `buscar` (CPF ou CNPJ só pelo hash), `contagens` e `indicadores`.
- `eventos.py`: assinantes de `aprovacoes.pedido_decidido` (`APR-05`), `financeiro.parcela_atrasou` e `financeiro.parcela_paga`.

## O que os outros apps registram aqui (ADR 0015, alvo `clientes.Cliente`)

| Registro | Quem | Uso |
| --- | --- | --- |
| blocos `locacao_atual`, `ultima_locacao` | `locacoes` | lista e detalhe; `alerta: "Cancelando"` dá a situação `cancelando` |
| bloco `financeiro` (`total_pago_centavos`, `em_aberto_centavos`, `a_devolver_centavos`, `conta_mais_antiga_id`) | `financeiro` | situação `parcela_atrasada` e ação `cobrar` |
| bloco `historico` (`situacao`, `rotulo`) | `financeiro` | item `historico` da análise |
| bloco `venda_aberta` | `vendas` | ação `ver_proposta` |
| filtros `com_locacao` e `em_aberto` | `locacoes`, `financeiro` | abas e contagens; sem o filtro, a contagem é `null` |
| contador `contas_atrasadas_15_dias` | `financeiro` | desbloqueio automático só quando chega a 0 |
| contadores `locacao_aberta`, `em_aberto_centavos`, `venda_aberta` | `locacoes`, `financeiro`, `vendas` | recusa de inativar (`cliente_com_pendencia`) |
| evento `financeiro.parcela_atrasou(cliente_id, dias_atraso, vencimento?)` | `financeiro` | bloqueio com 15 dias |
| evento `financeiro.parcela_paga(cliente_id, ...)` | `financeiro` | desbloqueio ao quitar |

Testes: `tests/aceitacao/test_t014_clientes.py`.
