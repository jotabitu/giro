# T-435 · Compra pública de ponta a ponta · faz-tudo → seguranca, design-system, qa

**O que foi feito:** a compra self-service inteira, pelo contrato `docs/api/compra.md`, com a T-378 junto.
- **Backend:** `PedidoCompra` no `public`; serviços em `apps/plataforma/compra.py`; rotas em `apps/plataforma/api/compra.py`, só no domínio principal (`urls_publico`). O domínio principal entra na migração `plataforma.0014`. Código de 6 dígitos no e-mail (hash, 15 min, 5 tentativas, 3 reenvios com 60 s entre eles); limites por IP (throttles do DRF) e por e-mail e CNPJ (contados no banco); teto de 50 empresas por dia com liberação pelo Django Admin; criação no Celery chamando `criar_empresa`; expiração diária com apagamento dos dados pessoais em 7 dias.
- **`criar_empresa`:** recebe `origem`, o aceite dos Termos e o `andamento`. Confere a situação do CNPJ (`PLT-16`) nas duas portas: quem já foi cliente nasce `ativa`, sem teste, com a 1ª fatura hoje e `empresa_anterior`. O CNPJ passou a ser único só entre empresas não apagadas (B-02 da T-230).
- **T-378:** `Plano.a_venda`, com o Completo fora da venda. Ele sai de Mudar de plano, de Comparar planos e do cartão do plano acima, e a API recusa a mudança com 400 `plano_fora_da_venda`. O catálogo do Profissional passou ao texto da fase 1 (`PLT-11`).
- **CNPJ pela BrasilAPI (ADR 0039):** o dono trocou a D-430-03 em 05 nov 2026. `integracoes/cnpj` (`falso` em dev e testes), com cache de 7 dias. Só preenche o checkout: a pessoa edita, e a compra não depende da consulta.
- **Frontend:** rota `(publico)/compra` com escolha do plano, checkout (CNPJ e endereço checados enquanto a pessoa digita), código com reenvio e ambiente pronto, que consulta o andamento a cada 2 s. A chave do pedido fica só em memória e no `sessionStorage`. Logo Giro por SVG do kit.

**Onde:** backend `apps/plataforma/{compra.py, situacao_cnpj.py, api/compra.py, api/urls_compra.py, models.py, services.py, selectors.py, catalogo.py, admin.py, tasks.py, migrations/0014_compra_publica.py}`, `integracoes/cnpj/`, `comum/limites.py`, `apps/contas/services.py` (`link_do_convite_da_compra`), `config/`; frontend `src/components/compra/`, `src/lib/compra.ts`, `src/lib/api/{compra,tipos-compra}.ts`, `public/marca/`; docs `docs/api/compra.md`, ADR 0039.

**Testes:** `tests/aceitacao/test_t435_compra_publica.py` (todos os nomes da lista do contrato, mais BrasilAPI, provedor fora do ar e validação) e `src/components/compra/CompraPublica.test.tsx`, `src/lib/compra.test.ts`.

**O que ficou de fora:**
- **T-431 (segurança) não foi feita:** o código saiu antes da revisão, por pedido do dono. Pontos para olhar: rotas anônimas, enumeração do CNPJ (agora com dados da Receita na resposta), o link do convite na tela, o IP atrás do proxy e o `before_send` do Sentry.
- **T-434 (telas de referência) não foi feita.** Por isso faltam a conferência lado a lado e o E2E da T-433.
- `aceita_whatsapp` vai sempre `false`: a tela não tem o aceite e a empresa não tem o campo (ADR 0034 proposta). O pedido guarda o valor.
- Os textos dos Termos (D-430-05) continuam em aberto: a compra não entra no ar sem eles (`GIRO_TERMOS_VERSAO=rascunho`).
- O Pix automático escolhido na compra grava a forma, mas a autorização (QR) fica para a `Admin-Assinatura`.
- Ao recarregar a aba antes do código, a compra recomeça do plano. Depois do código, volta ao andamento.

**Configuração nova:** `GIRO_PROVEDOR_CNPJ` (`brasilapi` em homologação e produção), `GIRO_COMPRA_TETO_DIARIO` (50), `GIRO_TERMOS_VERSAO`, `GIRO_EMAIL_EQUIPE`. O devops acrescenta nos ambientes.

**Próximo passo:** seguranca faz a T-431 sobre o código; design-system faz a T-434; depois o qa faz a conferência e o E2E.
