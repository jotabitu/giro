# App `importacao` no último nível da ordem de dependências

**Status:** aceita · 07 out 2026 · acrescenta um app à ADR 0011, sem mudar a ordem existente

## Contexto

A importação por planilha (`IMP-02`, `IMP-03`, passo 11 da implantação) cria veículos e clientes. Ela precisa chamar `veiculos.services` e `clientes.services`, e guarda dados temporários (linhas da planilha, com erros e correções) que não são de nenhum dos dois. O assistente de implantação é do app `empresas`, que fica acima de `veiculos` e `clientes` na ordem da ADR 0011 e por isso não pode chamá-los.

## Decisão

1. App novo **`importacao`**, em `TENANT_APPS`, no **nível 13** da ordem da ADR 0011, junto de `automacoes` e `relatorios`: pode chamar os serviços de qualquer app acima e ninguém depende dele.
2. Ele só orquestra: cada linha vira um cadastro pelo serviço do app dono (`veiculos.services.criar`, `clientes.services.criar`), com as mesmas validações, limites e auditoria de um cadastro pela tela.
3. Os dados da planilha são temporários e não são registro de negócio: o arquivo e as linhas são apagados 30 dias depois da importação. As linhas de clientes guardam os dados pessoais cifrados (ADR 0014).

## Consequências

- A tabela de apps da ADR 0011 passa a ter `importacao` em `TENANT_APPS` e no nível 13.
- O teste de limites entre apps aceita `importacao` importando de `veiculos`, `clientes`, `filiais`, `plataforma` e `comum`.
- O backend cria o app na T-027 e o acrescenta em `backend/README.md`.
