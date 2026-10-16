# Decisões de arquitetura (ADRs)

Uma decisão por arquivo. Para mudar uma decisão, escreva uma nova ADR que substitui a anterior; não edite a antiga.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-monolito-modular-django.md) | Monólito modular em Django | aceita, detalhada pela 0011 |
| [0002](0002-multiempresa-schema-por-empresa.md) | Multiempresa com um schema por empresa (django-tenants) | aceita, detalhada pelas 0008 e 0012 |
| [0003](0003-dinheiro-em-centavos.md) | Dinheiro em centavos inteiros | aceita, complementada pela 0009 |
| [0004](0004-white-label-por-tokens.md) | White label por tokens de cor e slot de logo | aceita |
| [0005](0005-regras-na-api.md) | Regras de negócio só na API | aceita |
| [0006](0006-contrato-de-api-primeiro.md) | Contrato da API antes do código | aceita |
| [0007](0007-pagamentos-asaas.md) | Pagamentos pelo Asaas, com subconta por locadora | aceita |
| [0008](0008-usuarios-e-autenticacao-por-schema.md) | Usuários e autenticação por schema | aceita, complementada pela 0013 |
| [0009](0009-fundacao-comum.md) | Fundação comum dos models (`backend/comum/`) | aceita |
| [0010](0010-auditoria-imutavel.md) | Auditoria imutável em cada schema | aceita; item 3 complementado pela 0016, item 7 substituído pela 0014 |
| [0011](0011-apps-e-limites.md) | Apps Django, dependências e comunicação entre apps | aceita (Admin fora de `TENANT_APPS` pela 0013; app `importacao` pela 0017) |
| [0012](0012-tarefas-celery-por-empresa.md) | Tarefas Celery por empresa | aceita |
| [0013](0013-endurecimento-da-autenticacao.md) | Endurecimento da autenticação (tokens, suporte, 2 etapas, Admin, cookie) | aceita, complementada pela 0014 |
| [0014](0014-sessoes-e-dados-sensiveis.md) | Sessões revogáveis e dados sensíveis (cifra, HMAC, auditoria) | aceita |
| [0015](0015-leituras-compostas-entre-apps.md) | Leituras compostas entre apps por registro de anotações | aceita |
| [0016](0016-papeis-de-banco-e-expurgo-da-auditoria.md) | Papéis de banco separados e expurgo da auditoria | aceita |
| [0017](0017-app-importacao.md) | App `importacao` no último nível da ordem de dependências | aceita |
| [0018](0018-ajustes-da-conferencia-da-fundacao.md) | Ajustes da conferência da fundação (T-001) | aceita |
| [0019](0019-pedido-de-aprovacao-pela-porta-em-comum.md) | Pedido de aprovação aberto por uma porta em `comum` (`comum.aprovacoes.pedir`) | aceita, detalha a 0011 |
| [0020](0020-formato-dos-momentos-na-api.md) | Momentos da API em UTC com `Z`, sem fração, formatados só pelo renderizador de `comum` | aceita, detalha a 0006 |
| [0021](0021-data-de-referencia-no-desenvolvimento.md) | Data de referência do relógio só no desenvolvimento (`GIRO_DATA_REFERENCIA`), com a hora real e a faixa "Data simulada" na tela | aceita, detalha a 0009 |
| [0022](0022-sanitizacao-do-logo-da-empresa.md) | Sanitização do logo da empresa: SVG relido com `defusedxml`, conteúdo ativo recusado, lista fechada; PNG reconstruído pelo Pillow (aceito pela Segurança em 13 out 2026) | aceita |
| [0023](0023-cartao-da-assinatura-na-pagina-do-parceiro.md) | Cartão da assinatura só na página do parceiro: o número nunca passa pelo Giro; guarda token cifrado, bandeira e final | aceita, detalha a 0007 |
| [0024](0024-modulos-por-plano.md) | Módulos por plano e por ramo, decididos por empresa: `Recurso` como módulo, 403 `PLT-12` nas rotas, leituras, tarefas e eventos pelo mesmo conjunto, pendências do downgrade por registro em `comum` | aceita, detalha a 0011 e a 0015 |
| [0026](0026-leitura-de-documentos-em-pdf.md) | Leitura do CRLV-e e da CNH-e por PDF (T-247, revisada pela segurança na T-273): camada de texto com `pypdf` num processo filho isolado com limites (2 MB, 3 páginas, 5 s de CPU, 512 MB), sem OCR, sem QR code, sem conferir a assinatura e sem consulta externa; o PDF não fica no servidor entre ler e salvar (comprovante assinado sem valores); nada do conteúdo em log; filho chamado por caminho com `-I`, ambiente só com `PATH` e `LANG`, limites aplicados por ele mesmo, `pypdf` mínimo pelo `pip-audit`, comprovante com chave própria e amarrado à empresa e ao usuário | aceita |
| [0025](0025-apagamento-da-empresa-cancelada.md) | Apagamento da empresa cancelada no 90º dia: `DROP SCHEMA` pela conexão de migração numa função única que confere a empresa, storage pelo prefixo, passos retomáveis, o que fica no `public` | aceita, detalha a 0002, a 0010 e a 0016 |
| [0027](0027-servidor-de-aplicacao-de-producao.md) | Servidor de homologação e produção: Gunicorn WSGI com `gthread` e o `gunicorn.conf.py` da T-258 (2 × 4 em homologação, 3 × 4 em produção, timeout 30 s, corte por requisição no proxy), imagem com alvos `dev` (`runserver`) e `producao` (sem root, só `requirements.txt`) | aceita, detalha a 0026 |
| [0028](0028-app-movimentacoes.md) | App `movimentacoes` no nível 11 (ao lado de `vistorias`): vistoria rápida da chegada no próprio app, uma movimentação aberta por veículo com trava na linha do veículo (também no `confirmar` da locação), blocos na Frota e na ficha pela ADR 0015, despesa da parada pelo `lancar_despesa` com a origem `movimentacao`, transferência na chegada pelo serviço de `veiculos` e a rota `transferir` fora do contrato | aceita, detalha a 0011 e a 0015 |

| [0029](0029-django-admin-pelo-proxy.md) | Django Admin da plataforma em `admin.<dominio>/admin/`, por um bloco próprio do host da plataforma no proxy; só `is_staff` (função Dono), 2 etapas, lista de IPs do cofre fechada por padrão (404 fora dela), limite no login e sessão de 4 horas | aceita, detalha a 0013 e a 0027 |

O modelo de dados detalhado fica em [`modelo-de-dados.md`](modelo-de-dados.md).

Modelo para uma nova ADR: título, status e data, contexto, decisão, consequências.

## Revisão de 07 out 2026 (T-006)

As ADRs 0001 a 0007 continuam válidas. O que faltava foi coberto por ADRs novas, sem editar as antigas:

| ADR revisada | Ponto encontrado | Onde foi resolvido |
| --- | --- | --- |
| 0001 | "Serviços ou eventos" sem ordem de dependência entre apps; risco de import e migração circulares; contrato preso em `locacoes` | 0011 (ordem dos apps, origem genérica, eventos em processo, app `contratos`) |
| 0002 | Não dizia onde ficam os usuários, como o token se prende à empresa nem como o Celery entra no schema | 0008 e 0012 |
| 0003 | "Arredondamento só na exibição" não cobre percentuais que geram fração de centavo (desconto, multa, comissão, juros); faltava o tipo de campo para valores com sinal | 0009 (`ROUND_HALF_UP` no centavo, `CentavosField` e `CentavosComSinalField`) |
| 0004 | Sem lacunas. Os campos de marca ficam em `empresas.ConfiguracaoEmpresa` | modelo de dados |
| 0005 | Sem lacunas. Endpoints de simulação seguem `POST /api/<recurso>/simular/` | contratos de módulo |
| 0006 | Sem lacunas | — |
| 0007 | Não dizia onde fica a chave da subconta nem como o webhook encontra a empresa | modelo de dados: `plataforma.ContaPagamento` no `public` (id da subconta, chave cifrada, token do webhook); o webhook entra pelo `public` e só depois muda para o schema da empresa |
| README | A linha da 0007 estava fora da tabela (linha em branco no meio) | corrigido aqui |
