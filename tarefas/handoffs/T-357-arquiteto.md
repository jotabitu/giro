# T-357 · ADR de hospedagem e produção (D7) · arquiteto → orquestrador, dono, devops

**O que foi feito:** ADR 0033, `docs/decisoes/0033-hospedagem-e-producao.md`, como **proposta**, com três opções para o backend, o worker e o beat, o Next, o PostgreSQL, o Redis e os arquivos. Cada opção traz o custo, o certificado curinga, o backup, a rede e o cofre.

| Opção | Piloto (R$/mês) | 20 empresas (R$/mês) | Resumo |
| --- | --- | --- | --- |
| A · AWS São Paulo | 600 a 750 | 1.500 a 1.900 | EC2 com o compose da homologação, RDS, S3; backup em conta separada com Vault Lock; Parameter Store; dados no Brasil |
| B · Uma VPS | 200 a 350 | 450 a 750 | Tudo em Compose, Postgres operado por nós; pgBackRest e restic cifrados para outro provedor |
| C · DigitalOcean | 350 a 450 | 850 a 1.200 | Droplet, Postgres gerenciado e Spaces; `pg_dump` cifrado para outro provedor; dados fora do Brasil |

Os custos são estimativas de outubro de 2026, com o dólar a R$ 5,50. É preciso conferir na calculadora do provedor ao contratar.

**Vale para qualquer opção:**
- **Certificado curinga:** Let's Encrypt por DNS-01, instalado no próprio nginx, sem balanceador, para manter o IP real da ADR 0029.
- **Backup:** cifrado, com chave fora do servidor da aplicação, e retenção máxima de 30 dias. Assim, o dado apagado no 90º dia (`AUD-08`) some das cópias até 120 dias depois do cancelamento.
- **Restauração:** testada antes do primeiro cliente e depois uma vez por mês, com registro em `infra/backup/`.
- **Rede:** nenhuma porta publicada além de 80 e 443.
- **Cofre:** `giro_migracao` só no `migrar` e no worker do apagamento (M-01 da T-355).

**A lista do que o dono contrata** está na ADR: domínio, hospedagem, conta de produção do Asaas, WhatsApp, e-mail transacional, Sentry e, na B e na C, o cofre e o destino do backup.

**Recomendação:** a opção A, com o Redis em contêiner no piloto. Se o custo pesar mais, a C.

**Achados:**
- O WhatsApp só tem o provedor falso no código (`integracoes/whatsapp`). A integração real precisa de ADR (escolha do provedor), contrato e tarefa antes do primeiro cliente que use convite ou cobrança por WhatsApp.
- Se o produto quiser, o texto do cancelamento pode citar os 30 dias das cópias de segurança. Isso é `[decisão]` do produto e não bloqueia a subida.

**Onde:** `docs/decisoes/0033-hospedagem-e-producao.md`, `docs/decisoes/README.md` e `tarefas/feito.md`.
**Regras cobertas:** `AUD-08`, `AUD-05`, `AUD-02` (nenhuma muda).
**O que ficou de fora:** não contratei nem criei conta em nenhum provedor. Os preços não foram cotados no site dos provedores.
**Próximo passo para quem recebe:**
- o dono escolhe a opção;
- o arquiteto passa a ADR para aceita;
- o devops faz a subida de produção do M-02 (rede, cofre, curinga, backup, primeira restauração registrada, worker do apagamento).

A T-358 segue numa branch própria. Branch `t-357-adr-hospedagem`, sem PR.
