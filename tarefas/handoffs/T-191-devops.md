# T-191 · Variáveis do Asaas no .env.example · devops → orquestrador

**O que foi feito:** a seção "Pagamentos" do `.env.example` trazia `ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN` e `ASAAS_AMBIENTE`, que nenhum código lê (conferido no `backend/` e no resto do repositório). Foi trocada pelas variáveis que a T-029 lê em `config/settings/base.py`:
- `GIRO_ASAAS_URL=https://api-sandbox.asaas.com/v3` (padrão sandbox; produção `https://api.asaas.com/v3`, dito no comentário).
- `GIRO_ASAAS_CHAVE_API=` (vazia; chave da conta principal, só abre subcontas).
- `GIRO_URL_WEBHOOK_PAGAMENTOS=` (vazia; vazio usa `https://admin.<DOMINIO_BASE>/api/webhooks/pagamentos/asaas/`, no dev com sandbox vai o endereço HTTPS do túnel).
- Além das três pedidas, `GIRO_PROVEDOR_PAGAMENTOS=falso`: é o que liga o Asaas (`falso` ou `asaas`) e não estava no arquivo. Sem ela, quem preenchesse a chave não veria efeito.

**Onde:** `.env.example`, `tarefas/feito.md`.

**Compose e CI:** sem mudança. O compose lê tudo por `env_file: .env` (backend, worker, beat e frontend); o `check-env.sh` só cobra as variáveis `${VAR}` do compose (passou); o job de infra do CI copia o `.env.example` e roda `docker compose config`, que não depende dos valores. Não rodei o `docker compose config` aqui porque ele exige um `.env` local e você pediu para não mexer nele.

**O que ficou de fora:** `infra/deploy/homologacao.env.example` e `producao.env.example` listam só o que muda; não mexi, porque o provedor real nesses ambientes ainda não foi decidido. Quando for, entram `GIRO_PROVEDOR_PAGAMENTOS=asaas`, `GIRO_ASAAS_URL` de produção e `GIRO_ASAAS_CHAVE_API` (cofre). Os testes de sandbox local usam `GIRO_ASAAS_SANDBOX_*` direto do shell, fora do `.env.example` de propósito.

**Próximo passo para quem recebe:** orquestrador abre o PR. Quem tiver um `.env` antigo mantém as três `ASAAS_*` sem efeito; pode apagá-las.
