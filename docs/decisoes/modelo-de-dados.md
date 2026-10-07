# Modelo de dados

**Dono:** arquiteto · **Atualizado em:** 07 out 2026 (T-006) · **Base:** seção "Entidades e relações" de `docs/regras-de-negocio.md` e ADRs 0001 a 0012.

Este documento diz, para cada uma das 25 entidades das regras, o app dono, o schema, os campos, os índices e as restrições. As entidades de apoio (que não estão na lista das regras mas são necessárias) vêm no fim de cada app. Mudança aqui passa pelo arquiteto; o backend implementa a partir daqui e do contrato do módulo em `docs/api/`.

## Convenções deste documento

- Todo model herda de `comum.ModeloBase` (`id` bigint, `criado_em`, `atualizado_em`, ADR 0009). Esses campos não são repetidos nas tabelas.
- **Tipos:** `texto(n)` = `CharField(max_length=n)`; `texto` = `TextField`; `centavos` = `CentavosField` (≥ 0); `centavos±` = `CentavosComSinalField`; `pct` = `PercentualField` (`Decimal(5,2)`); `data` = `DateField`; `momento` = `DateTimeField` em UTC; `enum` = `TextChoices` com os valores das regras; `json` = `JSONField`; `arquivo` = `FileField` no storage privado (`AUD-05`); `FK →` = `ForeignKey(..., on_delete=PROTECT)` salvo indicação.
- **Ativável** = herda `ModeloAtivavel` (`ativo`). **Código** = herda `ModeloComCodigo` (`numero`, `codigo` único). **Máquina** = herda `MaquinaDeEstados`; as transições permitidas são as das regras.
- **Origem genérica** = `origem_tipo` (enum), `origem_id` (bigint), `origem_codigo` (texto(20)), com índice `(origem_tipo, origem_id)` (ADR 0011).
- Os nomes de tabela são os padrão do Django (`<app>_<model>`).
- Os status das entidades sem seção própria nas regras seguem a tabela "Estados das entidades sem seção própria" de `docs/regras-de-negocio.md` (T-031).

## Visão geral

| # | Entidade (regras) | Model | App | Schema |
| --- | --- | --- | --- | --- |
| 1 | Plano | `Plano` | `plataforma` | public |
| 2 | Empresa (tenant) | `Empresa` | `plataforma` | public |
| 3 | Fatura da assinatura | `FaturaAssinatura` | `plataforma` | public |
| 4 | Usuário da plataforma | `Usuario` (linhas do `public`) | `contas` | public |
| 5 | Acesso de suporte | `AcessoSuporte` | `plataforma` | public |
| 6 | Filial | `Filial` | `filiais` | empresa |
| 7 | Usuário | `Usuario` (linhas da empresa) | `contas` | empresa |
| 8 | Categoria de veículo | `Categoria` | `veiculos` | empresa |
| 9 | Veículo | `Veiculo` | `veiculos` | empresa |
| 10 | Documento do veículo | `DocumentoVeiculo` | `veiculos` | empresa |
| 11 | Cliente | `Cliente` | `clientes` | empresa |
| 12 | Plano de locação especial | `PlanoEspecial` | `locacoes` | empresa |
| 13 | Locação | `Locacao` | `locacoes` | empresa |
| 14 | Vistoria | `Vistoria` | `vistorias` | empresa |
| 15 | Contrato | `Contrato` | `contratos` | empresa |
| 16 | Modelo de contrato | `ModeloContrato` | `contratos` | empresa |
| 17 | Venda | `Venda` | `vendas` | empresa |
| 18 | Conta a receber (parcela) | `ContaReceber` | `financeiro` | empresa |
| 19 | Despesa (conta a pagar) | `Despesa` | `financeiro` | empresa |
| 20 | Ordem de serviço | `OrdemServico` | `manutencao` | empresa |
| 21 | Caixa do dia | `Caixa` | `financeiro` | empresa |
| 22 | Movimento de caixa | `MovimentoCaixa` | `financeiro` | empresa |
| 23 | Lançamento bancário | `LancamentoBancario` | `financeiro` | empresa |
| 24 | Comissão | `Comissao` | `financeiro` | empresa |
| 25 | Evento de auditoria | `EventoAuditoria` | `auditoria` | public **e** empresa |

Apoio em `comum` (os dois schemas): `Sequencia` (contadores dos códigos, ADR 0009) e `WebhookRecebido` (`provedor`, `evento_id` único, `recebido_em`, `corpo` json, `processado_em`, `resultado`; S-14).

---

## Schema public

### 1. Plano · `plataforma.Plano` · ativável

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(40), único | Essencial, Profissional, Completo |
| `preco_mensal_centavos` | centavos | 19900, 44900, 89900 |
| `meses_cobrados_no_anual` | int | 10 (anual = 10 mensalidades) |
| `limite_veiculos` | int, nulo | nulo = sem limite (Completo) |
| `limite_filiais` | int, nulo | |
| `limite_usuarios` | int, nulo | |
| `recursos` | json (lista de enum) | módulos liberados |
| `ordem` | int | ordem na tela `Compra-Planos` |

- `PLT-05`: preço novo vale só para assinaturas novas. Por isso a `Empresa` guarda o preço contratado; o `Plano` guarda o preço de tabela.
- Apoio: `PrecoAdicional` (`codigo` enum `filial`, `pacote_10_veiculos`, `assinatura_digital`; `preco_centavos`). Fase 2.

### 2. Empresa · `plataforma.Empresa(TenantMixin)` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `schema_name` | texto(63), único | do django-tenants; igual ao subdomínio com `_` no lugar de `-` |
| `razao_social` | texto(150) | |
| `nome_exibicao` | texto(80) | cópia do nome para o painel da plataforma |
| `cidade`, `uf` | texto(80), texto(2) | lista de empresas |
| `responsavel_nome`, `responsavel_email`, `responsavel_telefone` | texto | contato do administrador na compra |
| `cnpj` | texto(14), único | só dígitos, validado (`CLI-01` vale para CNPJ) |
| `subdominio` | texto(63), único | `motorapida` |
| `plano` | FK → `Plano` | |
| `ciclo` | enum `mensal`, `anual` | |
| `preco_contratado_centavos` | centavos | `PLT-05` |
| `plano_proximo` | FK → `Plano`, nulo | downgrade agendado (`PLT-04`) |
| `status` | enum `em_teste`, `ativa`, `inadimplente`, `suspensa`, `pausada`, `cancelada` | transições da seção "Plataforma e assinatura" |
| `teste_inicio`, `teste_fim` | data | `PLT-01` (Moto Rápida: 07 a 21 out) |
| `pausada_ate` | data, nulo | máximo 3 meses |
| `cancelada_em` | momento, nulo | |
| `acesso_ate` | data, nulo | fim do período pago após cancelar |
| `apagar_em` | data, nulo | `cancelada_em` + 90 dias (`AUD-08`) |
| `motivo_cancelamento` | texto, nulo | `PLT-06` |
| `suporte_bloqueado` | bool | administrador bloqueou o suporte (`PLT-07`) |
| `etapa_implantacao` | enum `conta`, `marca`, `filial`, `precos`, `dados`, `primeira_locacao`, `concluida` | funil `IMP-05` |
| `etapa_implantacao_desde` | momento | "precisam de ajuda" com 3 dias |

- `auto_create_schema = True`; criação só por `plataforma.services.criar_empresa` (`Compra-Pronto`, ou Django Admin no MVP).
- Índices: `status`; `(etapa_implantacao, etapa_implantacao_desde)`.
- O tenant `public` também é uma linha de `Empresa` (exigência do django-tenants); o `id` entra na claim `empresa_id` dos tokens (ADR 0013).
- Apoio: `UsoEmpresa` (1:1 com `Empresa`): `veiculos`, `filiais`, `usuarios` (int), `locacoes_total` (int), `ultimo_acesso_em` (momento, nulo), `passos_implantacao` (json `{passo: data}`), `aviso_90_enviado` (json `{item: mes}`). Resumo no `public` para a lista da plataforma e para `PLT-03`, mantido por `plataforma.services.atualizar_uso` e corrigido por tarefa noturna (contrato da plataforma).
- Apoio: `Dominio(DomainMixin)`: `domain` único (`motorapida.girolocadoras.com.br`), `tenant` FK, `is_primary`. O tenant `public` tem `admin.girolocadoras.com.br` e `girolocadoras.com.br`.

### 3. Fatura da assinatura · `plataforma.FaturaAssinatura` · código `FAT` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `empresa` | FK → `Empresa` | |
| `competencia` | data (dia 1 do mês) | |
| `valor_centavos` | centavos | |
| `vencimento` | data | |
| `status` | enum `aberta`, `paga`, `atrasada`, `cancelada` | regras, "Estados das entidades sem seção própria" |
| `forma` | enum `pix`, `boleto`, `cartao`, nulo | |
| `pago_em` | momento, nulo | |
| `cobranca_externa_id` | texto(60), nulo, único | id da cobrança no Asaas (conta principal) |
| `tentativas_cartao` | int | `PLT-02` (nova tentativa no dia seguinte) |

- Restrição: única por `(empresa, competencia)` quando `status <> cancelada`.
- Índices: `(status, vencimento)` para a régua `AUT-13`.

### 4. Usuário da plataforma · `contas.Usuario` no schema public

O mesmo model do item 7 (ADR 0008). No `public`: `funcao_plataforma` enum `dono`, `suporte`, `financeiro`, `sucesso` (`PLT-09`) obrigatório, `perfil` nulo, 2FA sempre obrigatório (`PLT-08`).

### 5. Acesso de suporte · `plataforma.AcessoSuporte` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `usuario` | FK → `contas.Usuario` (public) | quem entrou |
| `empresa` | FK → `Empresa` | |
| `motivo` | texto | obrigatório |
| `chamado` | FK → `Chamado`, nulo | |
| `permissao` | enum `ver`, `ver_editar` | |
| `inicio`, `fim` | momento | `fim - inicio` ∈ {15 min, 30 min, 1 h} |
| `encerrado_em` | momento, nulo | |
| `status` | enum `ativo`, `encerrado`, `revogado` | `encerrado` = prazo acabou ou o suporte saiu; `revogado` = administrador bloqueou |

- Restrição: `CHECK (fim > inicio)`. Índices: `(status, fim)` para `AUT-15` (a cada minuto); `(empresa, inicio DESC)`.

### Apoio do public

| Model | App | Campos principais |
| --- | --- | --- |
| `ContaPagamento` | plataforma | `empresa` (1:1), `provedor` enum `asaas`, `conta_externa_id` único, `chave_api_cifrada` (`CampoCifrado` com `GIRO_CHAVE_SEGREDOS`, decifrada só em `integracoes/pagamentos/`, ADR 0014), `webhook_token_hash` único, `status` enum `pendente`, `aprovada`, `recusada`. O webhook chega no `public`, acha a empresa pelo token e só então entra no schema dela (ADR 0007). |
| `Chamado` | plataforma | `numero` (#1042), `empresa` FK, `assunto`, `status`, `responsavel` FK usuário. Fase 2. |
| `Convite` | contas | ver item 7 (serve aos dois schemas). |

---

## Schema da empresa

### 6. Filial · `filiais.Filial` · ativável

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(80), único | Filial Centro |
| `cnpj` | texto(14), nulo | |
| `inscricao_estadual`, `inscricao_municipal` | texto(20), nulo | |
| `telefone`, `whatsapp`, `email` | texto(13), texto(13), email; nulos | contato da filial |
| `preco_litro_centavos` | centavos, nulo | preço da bomba usado no acerto (`DEV-01`); seed Filial Centro = 550 |
| `endereco` | campos `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `uf` | |
| `matriz` | bool | |
| `horario` | json: `{seg..dom: [{abre, fecha}]}`, até 2 intervalos por dia | `LOC-11`; formato em `docs/api/filiais.md` |
| `fuso` | texto, fixo `America/Sao_Paulo` | |

- `nome` único com `Lower(nome)`. Sem status de rascunho, sem gerente como campo, vagas, centro de custo, tabela de preço ou conta de recebimento (`FIL-01`, `FIL-02`, `FIL-04`).
- Restrições: no máximo uma matriz (`UniqueConstraint(fields=["matriz"], condition=Q(matriz=True))`); a última filial ativa não pode ser desativada (serviço). `PLT-03` checado no serviço de criação.
- Apoio: `FeriadoFilial` (ativável): `filial` FK, `data`, `nome` texto(80), `origem` enum `nacional`, `local`. Único `(filial, data)` quando ativo (`FIL-03`, `LOC-11`).
- Apoio: `UsuarioFilial` (`usuario` FK → `contas.Usuario` CASCADE, `filial` FK) único por `(usuario, filial)` (`USR-07`, ADR 0008).

### 7. Usuário · `contas.Usuario(AbstractBaseUser)` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(120) | |
| `email` | email, único no schema (`Lower(email)`) | login (`USERNAME_FIELD`) |
| `celular` | texto(13), nulo | |
| `perfil` | enum `administrador`, `gerente`, `vendedor`, `vistoriador`, `financeiro`, nulo | só no schema da empresa |
| `funcao_plataforma` | enum `dono`, `suporte`, `financeiro`, `sucesso`, nulo | só no `public` |
| `permissoes_extras` | `ArrayField(enum)` `aprovar_desconto`, `cancelar_contrato`, `relatorios_todas_filiais` | `USR-03` |
| `status` | enum `convite_pendente`, `ativo`, `desativado` | `USR-01`, `USR-04`; convite vencido continua `convite_pendente` e conta no limite |
| `is_active` | propriedade = `status == ativo` | |
| `is_staff` | bool | acesso ao Django Admin |
| `exige_2fa` | **propriedade**, não é coluna | derivada do schema, do perfil, de `exige_2fa_todos` e de dispositivo ativo (ADR 0013) |
| `tentativas_erradas`, `bloqueado_ate` | int, momento nulo | `USR-06`, `PLT-08` |
| `ultimo_acesso` | momento, nulo | |

- `CHECK ((perfil IS NULL) <> (funcao_plataforma IS NULL))`.
- 2FA: dispositivos do `django_otp` (TOTP e códigos de recuperação).
- Contam no limite do plano: `status IN (convite_pendente, ativo)` (`USR-01`, `USR-04`).
- Apoio `Sessao` (ADR 0014): `usuario` FK, `tipo` enum `desktop`, `celular`, `aparelho`, `ip`, `ultimo_uso`, `expira_em`, `revogada_em` nulo, `revogada_por` FK nulo, `motivo_revogacao`. Índice `(usuario, revogada_em)`. Claim `sid` nos tokens.
- Apoio `Convite`: `usuario` FK CASCADE, `token_hash` único, `enviado_whatsapp` bool (sempre sai por e-mail; WhatsApp quando há celular), `expira_em` (+7 dias), `aceito_em` nulo, `enviado_por` FK.

### 8. Categoria de veículo · `veiculos.Categoria` · ativável

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(60) | Urbana 110–125 |
| `tipo_veiculo` | enum `moto`, `carro` | define a CNH exigida (`CLI-02`) |
| `filial` | FK → `Filial`, nulo | nulo = vale para a empresa toda; preenchido = preço da filial |

- Único: `(nome, filial)` (com `nulls_distinct=False`).
- Preço com histórico (`LOC-15`), apoio **`PrecoCategoria`**: `categoria` FK, `vigente_desde` data, `diaria_centavos`, `semanal_centavos`, `mensal_centavos`, `caucao_centavos`, `alterado_por` FK. Único `(categoria, vigente_desde)`. O preço vigente numa data é o de maior `vigente_desde <= data` (Moto Rápida: Street semanal 29940 até 30 set, 32900 a partir de 01 out).
- Apoio `Extra`: `nome` (capacete extra, baú), `valor_centavos`, `cobranca` enum `por_periodo`, `unica`, ativável (`LOC-02`).

### 9. Veículo · `veiculos.Veiculo` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `placa` | texto(7), único | maiúscula, sem hífen; `VEI-01` |
| `chassi` | texto(17), único | `CHECK (char_length(chassi) = 17)`; único em qualquer estado (`VEI-01`) |
| `renavam` | texto(11), nulo | |
| `marca`, `modelo` | texto(40), texto(60) | Honda, CG 160 Fan |
| `ano_fabricacao`, `ano_modelo` | int | |
| `cor` | texto(30) | |
| `km_atual` | int ≥ 0 | só sobe (`VEI-01`); muda por serviço |
| `capacidade_tanque_litros` | `Decimal(5,1)`, nulo | base do combustível no acerto (`DEV-01`); seed PNB7C04 = 16.0 |
| `categoria` | FK → `Categoria` | |
| `filial` | FK → `Filial` | |
| `status` | enum `disponivel`, `reservado`, `alugado`, `em_manutencao`, `indisponivel`, `a_venda`, `vendido`, `baixado` | transições da seção "Veículos" (`REGRA_TRANSICAO` = `VEI`) |
| `motivo_status` | texto, nulo | bloqueio, baixa |
| `valor_compra_centavos` | centavos, nulo | valor contábil (`FIN-13`) |
| `data_compra` | data, nulo | ficha do veículo |
| `valor_venda_centavos` | centavos, nulo | `VEN-01` |
| `referencia_fipe_centavos` | centavos, nulo | só exibição |
| `entrou_na_frota_em` | data | base de `VEI-06` |
| `km_ultima_manutencao`, `data_ultima_manutencao` | int, data, nulo | `MAN-05` |

- Índices: `(filial, status)`, `categoria`.
- Transições extras de T-031: `vendido` → `a_venda` (venda cancelada, `VEN-07`) e `vendido` → `indisponivel` (recompra numa troca: o serviço acha o veículo pelo chassi e reaproveita o cadastro, `VEI-07`).
- Apoio `HistoricoStatusVeiculo`: `veiculo` FK, `de`, `para`, `em` momento, `origem` genérica, `por` FK nulo. Base de `VEI-06` (ocupação). Índice `(veiculo, em)`.
- Apoio `LeituraKm`: `veiculo`, `km`, `lido_em`, `origem` genérica (vistoria, OS, correção), `motivo` (correção para baixo, `APR-06`).
- Apoio `TransferenciaVeiculo`: `veiculo`, `filial_origem`, `filial_destino`, `em`, `por` (`VEI-04`).

### 10. Documento do veículo · `veiculos.DocumentoVeiculo` · ativável

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | FK → `Veiculo` | |
| `tipo` | enum `crlv`, `ipva`, `seguro`, `rastreador` | |
| `validade` | data | |
| `arquivo` | arquivo, nulo | |
| `alerta_enviado_em` | momento, nulo | idempotência de `AUT-06` |

- Índice `(validade)` filtrado por `ativo`. Renovar = novo documento e o antigo `ativo=False`. Único `(veiculo, tipo)` quando `ativo`.

### 11. Cliente · `clientes.Cliente` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `tipo` | enum `pf`, `pj` | |
| `nome` | texto(150) | nome ou razão social |
| `documento` | `CampoCifrado` | CPF ou CNPJ, só dígitos (ADR 0014) |
| `documento_hash` | `CampoHashBusca`, **único** | HMAC do documento normalizado; unicidade e busca exata (`CLI-01`) |
| `nascimento` | data, nulo | PF |
| `celular`, `email` | texto(13), email | |
| `profissao` | texto(80), nulo | |
| `cnh_numero` (`CampoCifrado`) + `cnh_hash` (índice), `cnh_categoria`, `cnh_validade`, `cnh_primeira_habilitacao` | cifrado, hash, texto(3), data, data | do PF ou do condutor responsável na PJ (`CLI-02`) |
| `responsavel_nome`, `responsavel_cpf` (`CampoCifrado`) + `responsavel_cpf_hash` (índice) | texto, cifrado, hash; nulos | PJ |
| endereço | `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `uf` | |
| `referencia_nome`, `referencia_parentesco`, `referencia_telefone` | texto | |
| `status` | enum `incompleto`, `ativo`, `bloqueado`, `inativo` | |
| `bloqueio_motivo` | enum `atraso`, `manual`, nulo | `CLI-05`: só `atraso` desbloqueia sozinho |
| `consentimento_em` | momento, nulo | LGPD |
| `anonimizado_em` | momento, nulo | `AUD-06` |
| `cliente_desde` | data | `CLI-06` |

- Índices: `status`; `Lower(nome)` com `gin_trgm_ops` para a busca por nome; `cnh_validade`. Busca por CPF/CNPJ é exata, pelo hash.
- `CAMPOS_AUDITORIA`: cifrados omitidos; nome, nascimento, contatos, endereço e referência mascarados (ADR 0014).
- `total_pago` e `valor_em_aberto` (`CLI-06`) são calculados por selector a partir do financeiro, não guardados.
- Apoio `DocumentoCliente`: `cliente`, `tipo` enum `cnh_frente`, `cnh_verso`, `selfie_documento`, `comprovante_residencia`, `arquivo`, ativável. O cliente sai de `incompleto` quando tem os 4 ativos (`CLI-03`).

### 12. Plano de locação especial · `locacoes.PlanoEspecial` · ativável

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(60), único | Entregador, Mensal fidelidade |
| `periodicidade` | enum `diaria`, `semanal`, `mensal` | |
| `regra` | enum `preco_fixo`, `desconto` | `LOC-01` |
| `preco_centavos` | centavos, nulo | Entregador 27900 |
| `desconto_pct` | pct, nulo | Fidelidade 10.00 |
| `a_partir_do_periodo` | int | Fidelidade: 3 |
| `categorias` | M2M → `Categoria` | vazio = todas |
| `condicoes` | texto | km livre, troca de óleo inclusa |

- `CHECK` de que só o campo da `regra` escolhida está preenchido.

### 13. Locação · `locacoes.Locacao` · código `LOC` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `filial` | FK → `Filial` | |
| `cliente` | FK → `Cliente` | |
| `veiculo` | FK → `Veiculo` | veículo atual (ver `TrechoLocacao`) |
| `periodicidade` | enum `diaria`, `semanal`, `mensal` | |
| `plano_especial` | FK → `PlanoEspecial`, nulo | |
| `inicio` | momento | |
| `fim_previsto` | momento | |
| `devolvida_em` | momento, nulo | |
| `valor_periodo_centavos` | centavos | preço congelado na assinatura (`LOC-15`) |
| `diaria_centavos` | centavos | diária da categoria congelada; base de `LOC-10` e da multa `LOC-12` |
| `caucao_centavos` | centavos | `LOC-04` |
| `desconto_pct` | pct | `LOC-03` |
| `forma_pagamento` | enum `pix`, `pix_automatico`, `cartao`, `boleto`, `dinheiro` | |
| `parcelamento_mensal` | enum `a_vista`, `quatro_semanais`, nulo | `LOC-14` |
| `status` | enum `rascunho`, `aguardando_retirada`, `ativa`, `devolucao_atrasada`, `encerrada`, `cancelada` | |
| `vistoria_saida_ok_em`, `contrato_assinado_em`, `primeiro_pagamento_em` | momento, nulo | as 3 condições para `ativa`, em qualquer ordem |
| `vendedor` | FK → `contas.Usuario` | comissão `FIN-09` |
| `renovacoes` | int | `LOC-08` |
| `cancelada_em`, `motivo_cancelamento` | momento nulo, texto nulo | |
| `aprovacao_desconto` | FK → `aprovacoes.PedidoAprovacao`, nulo | |
| `km_saida` | int, nulo | gravado na vistoria de saída |
| `encerramento_antecipado_aprovado_em` | momento, nulo | `LOC-12`: segue para a devolução e termina `cancelada` |
| `multa_encerramento_centavos` | centavos, nulo | `LOC-12`, congelada na aprovação |

- **Uma locação ativa por veículo:** `UniqueConstraint(fields=["veiculo"], condition=Q(status__in=["aguardando_retirada", "ativa", "devolucao_atrasada"]), name="uma_locacao_aberta_por_veiculo")`. Violação vira `Conflito` com código `LOC-03`.
- `CHECK (fim_previsto > inicio)`.
- Índices: `(filial, status)`, `(status, fim_previsto)` para `AUT-01`/`AUT-02`, `cliente`, `veiculo`.
- Sinais `pagamento_atrasado`, `devolve_hoje`, `cancelamento_pendente` são calculados no selector (anotação), não guardados.
- `rascunho` com mais de 24 h sem uso é cancelado pela tarefa diária (sem auditoria de negócio além do evento de cancelamento).
- Apoio `TrechoLocacao` (`LOC-09`): `locacao`, `veiculo`, `inicio`, `fim` nulo, `valor_periodo_centavos`, `diaria_centavos`. Único `(locacao)` com `fim IS NULL`.
- Apoio `ExtraLocacao`: `locacao`, `extra`, `quantidade`, `valor_centavos` congelado.
- Apoio `TrocaVeiculo` (`LOC-09`): `locacao`, `veiculo_antigo`, `veiculo_novo`, `motivo`, `status` enum `pendente`, `concluida`, `cancelada`, `vistoria_devolucao` FK nulo, `vistoria_saida` FK nulo. Uma `pendente` por locação.

### 14. Vistoria · `vistorias.Vistoria` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `locacao` | FK → `Locacao` | |
| `veiculo` | FK → `Veiculo` | pode diferir do atual após troca (`LOC-09`) |
| `tipo` | enum `saida`, `devolucao` | |
| `status` | enum `rascunho`, `concluida` | `DEV-05`, `VIS-04` |
| `km` | int | `VEI-01` |
| `combustivel` | enum `reserva`, `um_quarto`, `meio`, `tres_quartos`, `cheio` | `VIS-03` |
| `itens` | json `[{item, ok, observacao}]` | `VIS-02` |
| `responsavel` | FK → `contas.Usuario` | |
| `concluida_em` | momento, nulo | |
| `substitui` | FK → `Vistoria`, nulo | correção (`VIS-04`) |
| `motivo_correcao` | texto, nulo | |

- Concluída não se edita (o serviço recusa). Único: uma vistoria `concluida` vigente por `(locacao, veiculo, tipo)` que não tenha sido substituída.
- Apoio `FotoVistoria`: `vistoria`, `posicao` enum `frente`, `traseira`, `lado_esquerdo`, `lado_direito`, `painel`, `avaria`, `arquivo`. Conclusão exige as 5 posições fixas (`VIS-01`).
- Apoio `Avaria`: `vistoria`, `veiculo`, `descricao`, `preexistente` bool, `valor_centavos` nulo, `vai_para_oficina` bool (`DEV-04`), `foto` FK, `ordem_servico` FK nulo, `resolvida_em` momento nulo (fecha quando a OS ligada é concluída). Índice `(veiculo, resolvida_em)` para "avarias abertas".
- Apoio `Devolucao` (`DEV-01`, `DEV-02`; `docs/api/vistorias.md`; um acerto só por locação, criado na primeira troca de veículo ou na devolução): `locacao` (1:1), `vistoria` FK (chegada), `status` enum `rascunho`, `concluida`, `caucao_centavos`, `saldo_centavos` (centavos±), `forma_devolucao` enum `pix`, `dinheiro`, `estorno_cartao`, nulo, `concluida_em`. Filho `ItemAcerto`: `tipo` enum `combustivel`, `avaria`, `atraso`, `km_excedente`, `parcela_aberta`, `multa_transito`, `multa_encerramento`, `semanas_nao_usadas` (crédito, `LOC-13`), `natureza` enum `cobranca`, `credito`, `modo` enum `informado`, `calculado`, `valor_centavos`, `descricao`, `avaria` FK nulo. Saldo = caução + créditos − cobranças. Exemplo LOC-2836: 3200 + 8500 = 11700; saldo 30000 − 11700 = 18300.

### 15. Contrato · `contratos.Contrato` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| origem genérica | `locacao` ou `venda` | |
| `modelo` | FK → `ModeloContrato` | |
| `versao_modelo` | int | cópia, para auditoria |
| `tipo` | enum `contrato`, `aditivo` | aditivo da renovação (`LOC-08`) |
| `pdf` | arquivo, nulo | WeasyPrint, com a marca da locadora |
| `hash_pdf` | texto(64) | SHA-256 do PDF assinado |
| `status` | enum `gerado`, `enviado`, `assinado`, `cancelado` | fluxo da retirada, passo 3 |
| `assinado_em` | momento, nulo | |
| `assinado_ip` | IP, nulo | |
| `assinatura_aparelho` | texto, nulo | |
| `token_assinatura_hash` | texto(64), único, nulo | link enviado ao cliente final (S-15) |
| `token_assinatura_expira_em` | momento, nulo | 7 dias; uso único: anulado ao assinar ou reenviar (S-15) |
| `versao_texto_html` | texto | HTML final com os marcadores trocados, guardado para auditoria |
| `clausula_juros` | bool | `FIN-03`: verdadeiro quando o modelo usa `{{cobranca.multa_atraso_pct}}` e `{{cobranca.juros_mes_pct}}` |

- Índice origem genérica; `status`.

### 16. Modelo de contrato · `contratos.ModeloContrato`

| Campo | Tipo | Observação |
| --- | --- | --- |
| `nome` | texto(80) | |
| `finalidade` | enum `locacao`, `venda` | aditivo usa texto padrão do sistema |
| `arquivado` | bool | fora de uso, não apagado |
| `versao` | int | |
| `texto` | texto | com campos `{{cliente.nome}}` etc. |
| `publicado` | bool | |
| `publicado_em` | momento, nulo | |
| `grupo` | uuid | identifica as versões do mesmo modelo |

- Versionado: editar um modelo publicado cria nova linha com `versao + 1`; a anterior não muda. Único `(grupo, versao)`. Um publicado vigente por `(grupo)`.
- `IMP-04`: sem modelo publicado de `locacao`, o serviço recusa concluir a locação.
- Segurança (S-09, relatório T-032): o `texto` aceita só marcadores de uma lista fechada (`{{cliente.nome}}`, `{{locacao.codigo}}` etc.), trocados por texto já escapado, sem motor de template sobre o texto do usuário; marcador fora da lista é recusado ao publicar. O HTML é sanitizado para poucas tags (sem `img` externa, `style`, `link`, `script`, `iframe`). O PDF sai numa task Celery com tempo limite, e o `url_fetcher` do WeasyPrint só aceita o logo da própria empresa no storage do schema atual. A lista de marcadores está em `docs/api/contratos.md`.

### 17. Venda · `vendas.Venda` · código `VEN` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `filial` | FK → `Filial` | |
| `cliente` | FK → `Cliente` | |
| `veiculo` | FK → `Veiculo` | só `a_venda` |
| `vendedor` | FK → `contas.Usuario` | |
| `preco_tabela_centavos` | centavos | `VEN-01` |
| `desconto_pct` | pct | |
| `preco_final_centavos` | centavos | 2290000 × 0,92 = 2106800 |
| `forma` | enum `a_vista`, `entrada_parcelas`, `financiamento` | `VEN-03` |
| `entrada_centavos` | centavos | |
| `num_parcelas` | int | |
| `juros_pct` | pct | padrão 0 (`VEN-04`) |
| `troca_veiculo` | FK → `Veiculo`, nulo | `VEN-05` |
| `troca_valor_centavos` | centavos, nulo | |
| `status` | enum `interessado`, `proposta`, `negociacao`, `aguardando_aprovacao`, `vendida`, `perdida`, `cancelada` | `cancelada` só a partir de `vendida`, por gerente ou administrador, com motivo (`VEN-07`) |
| `cancelada_em`, `motivo_cancelamento`, `cancelada_por` | momento, texto, FK; nulos | `VEN-07` |
| `motivo_perda` | texto, nulo | ex.: "veículo vendido" (`VEN-10`) |
| `proposta_enviada_em`, `vendida_em` | momento, nulo | `perdida` com 7 dias sem resposta |

- **Uma venda aberta por veículo (`VEN-10`):** `UniqueConstraint(fields=["veiculo"], condition=Q(status__in=["proposta", "negociacao", "aguardando_aprovacao"]), name="uma_venda_aberta_por_veiculo")`. Vários `interessado` podem existir para o mesmo veículo; quando ele vira `vendido`, o serviço passa os outros `interessado` dele para `perdida` com `motivo_perda` "veículo vendido".
- `VEN-07`: o cancelamento cancela as parcelas em aberto, estorna as pagas, estorna a comissão e devolve o veículo para `a_venda`, tudo na mesma transação.
- Apoio `MetaVenda`: `vendedor`, `mes` (data dia 1), `valor_centavos`; único `(vendedor, mes)` (`VEN-09`). Fase 2.

### 18. Conta a receber · `financeiro.ContaReceber` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `filial` | FK → `Filial` | |
| `cliente` | FK → `Cliente` | |
| origem genérica | `locacao`, `venda`, `devolucao` (saldo negativo `DEV-02`), `cliente` (multa avulsa) | |
| `tipo` | enum `parcela`, `caucao`, `multa`, `avaria`, `acerto`, `outro` | caução não é receita (`LOC-04`, `FIN-13`) |
| `total_parcelas` | int, nulo | "2 de 5" |
| `numero_parcela` | int, nulo | "2 de 4" |
| `vencimento` | data | |
| `valor_centavos` | centavos | |
| `multa_centavos`, `juros_centavos` | centavos | calculados no pagamento (`FIN-03`) |
| `status` | enum `aberta`, `paga`, `cancelada`, `renegociada` guardados; `vence_hoje` e `atrasada` calculados | ver nota |
| `forma` | enum `pix`, `boleto`, `cartao_debito`, `cartao_credito`, `dinheiro`, `pix_automatico`, `caucao`, nulo | `caucao` = paga com a caução no acerto (`DEV-02`) |
| `pago_em` | momento, nulo | |
| `movimento_caixa` | FK → `MovimentoCaixa`, nulo | baixa no caixa |
| `renegociada_em` | FK → `ContaReceber`, nulo | |
| `estorno_de` | FK → `ContaReceber`, nulo | conta reaberta por estorno aponta para a original |
| `estornada_em` | momento, nulo | na original estornada (continua `paga`) |

- **Nota sobre status:** `vence_hoje` e `atrasada` dependem só da data. Para não precisar de uma tarefa que reescreve status à meia-noite, o banco guarda `aberta` e o selector devolve `vence_hoje` (`vencimento = hoje`) ou `atrasada` (`vencimento < hoje`) no campo `status` da API. Os seis valores de `FIN-01` aparecem iguais para quem consome a API. Filtros usam a mesma expressão.
- Paga não se edita: correção é estorno (`estorno_de`, `docs/api/financeiro.md`).
- Apoio `CobrancaExterna`: `conta_receber` FK, `tipo` enum `pix`, `boleto`, `cartao_link`, `recorrente`, `externo_id` texto(60) **único**, `valor_centavos` (valor esperado do dia, comparado na baixa, S-14), `vence_em` data, `pix_copia_e_cola`, `linha_digitavel`, `url`, `caixa` FK nulo (gerada no caixa), `status` enum `aguardando`, `paga`, `cancelada`, `vencida`, `divergente`. Uma `aguardando` por conta.
- Apoio `AutorizacaoRecorrente` (`AUT-04`): `locacao` (origem genérica), `tipo` enum `pix_automatico`, `cartao`, `externo_id` único, `status` enum `pendente`, `ativa`, `cancelada`.
- Apoio `Reembolso` (devolução de dinheiro ao cliente: caução, `LOC-12`, `LOC-13`): `cliente` FK, origem genérica, `valor_centavos`, `forma` enum `pix`, `dinheiro`, `estorno_cartao`, `status` enum `a_fazer`, `feito`, `feito_em`, `feito_por` FK, `comprovante` arquivo, `movimento_caixa` FK nulo.
- Apoio `PendenciaPagamento` (S-14): `cobranca` FK → `CobrancaExterna`, `motivo` enum `valor_diferente`, `estornada_no_parceiro`, `sem_conta`, `valor_pago_centavos`, `status` enum `aberta`, `resolvida`, `resolucao` texto.
- Índices: `(status, vencimento)`, `(cliente, status)`, `(filial, vencimento)`, origem genérica.

### 19. Despesa · `financeiro.Despesa` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `filial` | FK → `Filial` | |
| `data` | data | data da despesa (lista e competência) |
| `descricao` | texto(150) | |
| `categoria` | enum `fixas`, `manutencao`, `rastreamento`, `impostos`, `pessoal`, `outros` | `FIN-06` |
| `valor_centavos` | centavos | |
| `vencimento` | data | |
| `veiculo` | FK → `Veiculo`, nulo | custo do veículo (`VEI-05`) |
| origem genérica | `ordem_servico`, nulo | `MAN-05` |
| `nota` | arquivo, nulo | foto da nota |
| `status` | enum `aguardando_aprovacao`, `a_pagar`, `paga`, `recusada` | `FIN-05` |
| `pago_em` | momento, nulo | |
| `forma` | enum `pix`, `boleto`, `cartao`, `transferencia`, `dinheiro`, nulo | |
| `movimento_caixa` | FK → `MovimentoCaixa`, nulo | paga no caixa |
| `lancada_por` | FK → `contas.Usuario` | |

- Índices: `(status, vencimento)`, `(veiculo)`, `(filial, vencimento)`.

### 20. Ordem de serviço · `manutencao.OrdemServico` · código `OS` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `veiculo` | FK → `Veiculo` | |
| `filial` | FK → `Filial` | filial do veículo na abertura |
| `servico` | texto(150) | |
| `tipo` | enum `corretiva`, `preventiva` | |
| `oficina` | FK → `Oficina`, nulo | |
| `previsao` | data, nulo | obrigatória para `na_oficina` (`MAN-01`) |
| `orcamento_centavos`, `custo_final_centavos` | centavos, nulo | |
| `status` | enum `agendada`, `aguardando`, `na_oficina`, `concluida`, `cancelada` | `atrasada` é sinal calculado (`MAN-04`) |
| `km_abertura` | int | |
| origem genérica | `devolucao` (`DEV-04`), `veiculo` (preventiva), nulo | |
| `status_veiculo_anterior` | enum de veículo, nulo | volta ao cancelar |

- Índices: `(status, previsao)`, `veiculo`.
- Apoio `Oficina` (ativável): nome, CNPJ, telefone, endereço.
- Apoio `RegraPreventiva` (ativável): `servico`, `a_cada_km` nulo, `a_cada_dias` nulo, `aviso_km` (500) (`MAN-03`).

### 21. Caixa do dia · `financeiro.Caixa` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `filial` | FK → `Filial` | |
| `data` | data | dia em `America/Sao_Paulo` |
| `aberto_por` | FK → `contas.Usuario` | |
| `troco_centavos` | centavos | |
| `contado_centavos` | centavos, nulo | contagem no fechamento |
| `esperado_centavos` | centavos, nulo | troco + entradas em dinheiro − saídas em dinheiro (`FIN-07`) |
| `diferenca_centavos` | centavos±, nulo | |
| `motivo_diferenca` | texto, nulo | |
| `status` | enum `aberto`, `aguardando_aprovacao`, `fechado`, `fechado_sem_conferencia` | `FIN-07`, `FIN-08`, `APR-04` |
| `fechado_por`, `fechado_em` | FK nulo, momento nulo | |

- **Único `(filial, data)`** (`FIN-07`). Índice `(status, data)` para `AUT-08`.

### 22. Movimento de caixa · `financeiro.MovimentoCaixa`

| Campo | Tipo | Observação |
| --- | --- | --- |
| `caixa` | FK → `Caixa` | só em caixa `aberto` |
| `tipo` | enum `entrada`, `saida`, `sangria` | |
| `forma` | enum `dinheiro`, `pix`, `cartao_debito`, `cartao_credito` | |
| `valor_centavos` | centavos | |
| origem genérica | conta a receber, despesa, devolução de caução | |
| `descricao` | texto(150) | |
| `registrado_por` | FK → `contas.Usuario` | |
| `estorno_de` | FK → `MovimentoCaixa`, nulo | |

- Imutável depois de gravado (correção por estorno). Índice `(caixa, tipo, forma)`.

### 23. Lançamento bancário · `financeiro.LancamentoBancario`

| Campo | Tipo | Observação |
| --- | --- | --- |
| `conta` | texto(40) | conta bancária de origem |
| `data` | data | |
| `descricao` | texto(200) | do extrato |
| `valor_centavos` | centavos± | crédito positivo, débito negativo |
| `identificador_externo` | texto(100) | FITID do OFX ou id da integração |
| `pagador` | texto(150), nulo | |
| `status` | enum `pendente`, `conciliado`, `ignorado` | `FIN-11` |
| `conciliado_com` | origem genérica, nulo | conta a receber, despesa ou movimento |
| `sugestoes` | json | pares sugeridos (valor, data ±3 dias, nome) |

- Único `(conta, identificador_externo)` (importar duas vezes não duplica, `AUT-12`). Índice `(status, data)`.

### 24. Comissão · `financeiro.Comissao` · máquina

| Campo | Tipo | Observação |
| --- | --- | --- |
| `usuario` | FK → `contas.Usuario` | |
| origem genérica | `venda`, `locacao` | |
| `base_centavos` | centavos | preço final da venda |
| `regra` | enum `percentual_venda`, `fixo_locacao` | |
| `pct` | pct, nulo | 3.00 |
| `valor_centavos` | centavos | 632,04 = 63204 |
| `status` | enum `pendente`, `confirmada`, `paga`, `estornada` | `FIN-09` |
| `mes_pagamento` | data (dia 1), nulo | pago no dia 5 do mês seguinte |

- Único `(origem_tipo, origem_id, usuario)` quando `status <> estornada` (uma comissão por venda ou locação nova). Índice `(usuario, mes_pagamento, status)`.
- Regras configuráveis ficam em `ConfiguracaoEmpresa` (abaixo).

### 25. Evento de auditoria · `auditoria.EventoAuditoria`

Campos, índices e imutabilidade na ADR 0010. Existe nos dois schemas. Apoio `Exportacao` (`AUD-07`): `solicitada_por`, `itens` (lista enum), `formato` enum `planilha`, `csv`, `zip`, `periodo_inicio`, `periodo_fim`, `status` enum `na_fila`, `pronta`, `expirada`, `falhou`, `arquivo`, `expira_em` (+7 dias).

### Apoio do schema da empresa (outros apps)

| Model | App | Campos principais |
| --- | --- | --- |
| `ConfiguracaoEmpresa` (uma linha só) | empresas | marca: `nome_exibicao`, `logo` (SVG), `cor_marca` (hex), `cor_marca_suave`, `cor_sobre_marca` calculada (ADR 0004); ramo: `trabalha_com` (motos/carros/ambos), `atividade` (aluga/vende/ambos); regras configuráveis: `tolerancia_atraso_minutos` (60), `taxa_combustivel_centavos` (1000), `desconto_sem_aprovacao_pct` (5.00), `limite_aprovacao_despesa_centavos` (50000), `multa_atraso_pct` (2.00, teto 2), `juros_mes_pct` (1.00, teto 1), `comissao_venda_pct` (3.00), `comissao_locacao_centavos` (1600), `exige_2fa_todos` (bool), `meta_ocupacao_pct` (80.00, exibida no início e no login); `etapas_implantacao_concluidas` (lista). Os tetos de `FIN-03` são `CHECK` no banco. |
| `PedidoAprovacao` | aprovacoes | `tipo` enum `APR-01` a `APR-06`, origem genérica, `solicitante` FK, `aprovador` FK nulo, `valor_centavos` ou `pct` nulos, `dados` json, `status` enum `pendente`, `aprovado`, `recusado`, `cancelado` (quem pediu desistiu ou a origem deixou de existir), `motivo_recusa`, `decidido_em`, `lembrete_enviado_em` (`APR-08`). `CHECK (aprovador_id <> solicitante_id)` (`APR-09`). Um `pendente` por `(tipo, origem_tipo, origem_id)`. |
| `Notificacao` | notificacoes | `destinatario` FK usuário, `tipo`, `titulo`, `link`, `lida_em`. Índice `(destinatario, lida_em)`. |
| `PreferenciaNotificacao` | notificacoes | `usuario`, `tipo`, `canais` (lista enum `sino`, `push`, `email`, `whatsapp`). Único `(usuario, tipo)`. |
| `MensagemEnviada` | notificacoes | `canal`, `destino` (mascarado), `modelo`, origem genérica, `status` enum `na_fila`, `enviada`, `falhou`, `externo_id`. Idempotência das réguas. |
| `ExecucaoAutomacao` | automacoes | `codigo` (`AUT-02`), `referencia` (data ou objeto), `executada_em`. Único `(codigo, referencia)` (ADR 0012). |

`relatorios` não tem tabela: lê dos outros apps por selector.

## Restrições de integridade (resumo)

| Restrição | Onde | Regra |
| --- | --- | --- |
| Placa e chassi únicos por empresa, em qualquer estado | `Veiculo.placa` e `Veiculo.chassi` únicos no schema | `VEI-01` |
| Chassi com 17 caracteres | `CHECK` em `Veiculo.chassi` | `VEI-01` |
| Km nunca diminui | serviço `veiculos.services.atualizar_km` (correção só com `APR-06`) | `VEI-01` |
| CPF/CNPJ único por empresa | `Cliente.documento_hash` único no schema | `CLI-01` |
| Uma locação aberta por veículo | índice único parcial em `Locacao.veiculo` | regras, "Entidades" |
| Uma venda aberta por veículo | índice único parcial em `Venda.veiculo` | `VEN-10` |
| Um caixa por filial por dia | único `(filial, data)` | `FIN-07` |
| Uma matriz por empresa | único parcial em `Filial.matriz` | — |
| Quem pede não aprova | `CHECK` em `PedidoAprovacao` | `APR-09` |
| Multa ≤ 2%, juros ≤ 1% ao mês | `CHECK` em `ConfiguracaoEmpresa` | `FIN-03` |
| Uma fatura por empresa por competência | único parcial em `FaturaAssinatura` | — |
| Webhook não processa duas vezes | único `WebhookRecebido.evento_id` e `CobrancaExterna.externo_id`; baixa só após consultar o parceiro e conferir o valor | `FIN-04`, S-14 |
| Extrato não duplica | único `(conta, identificador_externo)` | `AUT-12` |
| Auditoria imutável | triggers de linha e de `TRUNCATE`, papel `giro_app` só com `SELECT, INSERT` (ADR 0016) | `AUD-01` |
| Nada é apagado | `PROTECT` em toda FK de negócio; sem `delete()` nos serviços | convenções |

## Ordem de implementação sugerida (fase 1)

`comum` + `auditoria` + `contas` (T-001) → `plataforma` (T-010) → `filiais` (T-012) → `veiculos` (T-013) → `clientes` (T-014) → `contratos` + `locacoes` (T-015) → `vistorias` (T-016) → `financeiro` (contas a receber e caixa, T-017). O contrato de API de cada módulo (`docs/api/<modulo>.md`) sai antes da tarefa do backend.
