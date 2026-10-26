# Hospedagem e ambiente de produção

**Status:** aceita · 25 out 2026 · T-357 (decisão D7 do dono; M-02 da T-355) · **o dono escolheu a opção B** (uma VPS com tudo em Docker Compose), com preferência por provedor no Brasil · detalha a 0027 (servidor), a 0029 (Admin pelo proxy) e a 0016 (papéis de banco)

## Contexto

O `infra/README.md` deixava a hospedagem "a definir em ADR". A revisão de fechamento da fase 1 (T-355, M-02, `docs/seguranca/2026-10-25-t355-fechamento-fase-1.md`) pede que, antes do primeiro cliente real, estejam decididos:
- o backup cifrado, fora da conta principal e com restauração testada;
- a retenção dos backups compatível com a `AUD-08`;
- o Django alcançável só pelo proxy;
- o cofre de segredos, com `giro_migracao` só no deploy e no worker do apagamento (M-01).

O dono decidiu, em 25 out 2026, resolver isso já (D7).

### O que já está fixo e vale em qualquer opção

- **Imagem e processos.** Uma imagem `producao` (ADR 0027): Gunicorn `gthread` 3 × 4 com 4 GiB para o backend; o worker Celery e o beat com a mesma imagem; o Next em `output: standalone`. O compose de homologação (`infra/deploy/docker-compose.homologacao.yml`) já sobe `estaticos`, `migrar`, `backend`, `worker`, `beat` e `proxy`.
- **Proxy.** O nginx de `infra/proxy` fica na frente de tudo:
  - `/api/` vai direto ao Django, e o resto vai ao Next;
  - os cabeçalhos `X-Forwarded-*` são sobrescritos pelo proxy;
  - há limites de borda, e a lista de IPs do Admin vem do cofre (ADR 0029);
  - o corpo vai até 12 MB.
  O Next **não** vai para uma CDN separada nem para a Vercel: a API precisa ficar na mesma origem (ADR 0013, item 5), e o IP do cliente precisa chegar ao Django por um proxy só (ADR 0018).
- **Banco.** PostgreSQL 16 com os três papéis da ADR 0016 e o Redis, os dois com senha (T-274).
- **Arquivos.** Armazenamento compatível com S3, com buckets separados para homologação e produção (`GIRO_ARMAZENAMENTO=s3`).
- **Sentry.** O Sentry SaaS (plano gratuito no piloto e Team quando passar da cota) já está sem segredos (T-270). Vale para as três opções.
- **Domínio.** `admin.girolocadoras.com.br` para a plataforma e `<subdominio>.girolocadoras.com.br` para as empresas (07 out 2026). Domínio próprio de cliente é fase 2 (`PLT-11`).

## Decisão a tomar: três opções

Os custos são estimativas de outubro de 2026, em reais, com o dólar a R$ 5,50. Conferir na calculadora do provedor no dia da contratação. Não incluem e-mail, WhatsApp, Asaas nem domínio, que estão na lista do fim.

- **Piloto:** 1 a 3 empresas, poucos usuários.
- **20 empresas:** cerca de 20 empresas, 150 usuários e 2.000 veículos, com fotos de vistoria.

### Opção A · AWS São Paulo, banco gerenciado

| Peça | Onde |
| --- | --- |
| Backend, worker, worker do apagamento, beat, Next e nginx | Uma EC2 (t4g.medium no piloto, t4g.large com 20 empresas), em subnet pública só com 443 e 80 abertos. Os serviços sobem pelo mesmo compose da homologação |
| PostgreSQL | RDS PostgreSQL 16 (db.t4g.small no piloto; db.t4g.medium Multi-AZ com 20 empresas), em subnet privada |
| Redis | Contêiner na própria EC2, com senha e AOF, no piloto: o Redis não guarda dado de negócio. ElastiCache com 20 empresas |
| Arquivos | S3 em `sa-east-1`, bucket privado com versionamento |

- **Custo:** piloto cerca de R$ 600 a 750 por mês; 20 empresas, cerca de R$ 1.500 a 1.900.
- **Certificado curinga:** `*.girolocadoras.com.br` da Let's Encrypt pelo desafio DNS-01 no Route 53 (certbot com `dns-route53`, renovação automática), instalado no nginx. Não usa ALB: assim o nginx continua vendo o IP real para a lista do Admin e os limites, e não paga o balanceador.
- **Backup:**
  - **Banco:** backup automático do RDS com recuperação até o minuto (7 dias), cifrado por KMS. Por cima, o AWS Backup copia um snapshot diário para um cofre em **outra conta AWS só de backup**, com Vault Lock e retenção de 30 dias.
  - **Arquivos:** S3 com versionamento, versões antigas apagadas em 30 dias, e replicação para um bucket da conta de backup, cifrado com SSE-KMS.
- **Rede:**
  - Na EC2, só o nginx publica porta.
  - O backend, o Next e o Redis ficam na rede interna do compose.
  - O security group do RDS só aceita a EC2.
  - Sem SSH aberto: o acesso é pelo SSM Session Manager.
- **Cofre:** Parameter Store (SecureString com KMS), lido pelo job de deploy, que gera o `.env` de cada serviço. Os parâmetros de `giro_migracao` só vão para o `migrar` e para o worker do apagamento.
- **Prós e contras:**
  - Os dados ficam no Brasil.
  - Banco gerenciado, com recuperação até o minuto, Multi-AZ quando crescer e atualização pelo provedor.
  - Tem a conta separada de backup que o M-02 pede.
  - É a opção mais cara, e a AWS pede mais cuidado de configuração (IAM, MFA, alertas de custo).

### Opção B · Uma VPS com tudo em Docker Compose

| Peça | Onde |
| --- | --- |
| Tudo (backend, workers, beat, Next, nginx, PostgreSQL, Redis) | Uma VPS de 4 vCPU e 8 GB no piloto (por exemplo, Hetzner nos EUA ou Magalu Cloud no Brasil); duas VPS (aplicação e banco) com 20 empresas |
| Arquivos | Object storage compatível com S3 do mesmo provedor |

- **Custo:** piloto cerca de R$ 200 a 350 por mês; 20 empresas, cerca de R$ 450 a 750.
- **Certificado curinga:** Let's Encrypt por DNS-01 na Cloudflare (DNS gratuito, token só de DNS no cofre), renovado por certbot ou lego no host.
- **Backup:**
  - **Banco:** pgBackRest (ou WAL-G) com cifra AES-256 do próprio pgBackRest: backup completo semanal, diferencial diário e WAL contínuo.
  - **Arquivos:** restic, cifrado.
  - **Destino:** os dois vão para um bucket de **outro provedor** (Backblaze B2 ou Cloudflare R2), com retenção de 30 dias e Object Lock quando o provedor oferecer.
- **Rede:**
  - Firewall do provedor com só 80 e 443 abertos.
  - SSH só por chave e por lista de IPs (ou por Tailscale).
  - Postgres e Redis sem porta publicada.
- **Cofre:** não há cofre do provedor. Usar o Bitwarden Secrets Manager ou o Doppler (os dois com plano gratuito), lido pelo job de deploy. As senhas nunca ficam no servidor fora do `.env` gerado, que tem permissão 600.
- **Prós e contras:**
  - É a mais barata, e o mesmo compose roda igual no dev e na produção.
  - O banco fica **sob responsabilidade nossa**: atualização, disco cheio, recuperação até o minuto, failover e monitoramento. Um erro de operação derruba tudo junto.
  - Num provedor fora do Brasil, os dados saem do país. A LGPD permite essa transferência, mas o aviso de privacidade tem de dizer isso (art. 33, a confirmar com o produto).

### Opção C · DigitalOcean, aplicação em VM e banco gerenciado

| Peça | Onde |
| --- | --- |
| Backend, workers, beat, Next e nginx | Um Droplet de 4 GB no piloto, 8 GB com 20 empresas (região Nova York ou São Francisco; não há região no Brasil) |
| PostgreSQL | Managed PostgreSQL 16 (1 GB no piloto; 4 GB com nó em espera com 20 empresas) |
| Redis | Managed Valkey, compatível com Redis, ou contêiner no Droplet no piloto |
| Arquivos | Spaces (compatível com S3) |

- **Custo:** piloto cerca de R$ 350 a 450 por mês; 20 empresas, cerca de R$ 850 a 1.200.
- **Certificado curinga:** Let's Encrypt por DNS-01 no DNS da DigitalOcean ou na Cloudflare.
- **Backup:**
  - **Banco:** backup diário gerenciado, com recuperação até o minuto por 7 dias. Por cima, um `pg_dump` diário cifrado com age para um bucket de outro provedor (B2 ou R2), com 30 dias de retenção: o backup do provedor fica na mesma conta e não atende ao "fora da conta principal".
  - **Arquivos:** restic, cifrado, para o mesmo destino.
- **Rede:** o firewall do Droplet abre só 80 e 443; o banco tem *trusted sources* só com o Droplet; o SSH é só por chave e por IP.
- **Cofre:** Bitwarden Secrets Manager ou Doppler, como na B.
- **Prós e contras:**
  - Banco gerenciado pela metade do custo da AWS, e mais simples de operar.
  - Os dados ficam fora do Brasil (mesma observação da B).
  - A latência para o Brasil é de cerca de 120 ms, o que basta para as telas.
  - O backup fora da conta depende de um job nosso.

## Vale para a opção escolhida

1. **Retenção máxima dos backups: 30 dias**, contados de cada cópia, para o banco e para os arquivos.
   - O dado apagado no 90º dia (`AUD-08`) some do último backup até 30 dias depois, ou seja, até 120 dias depois de a empresa virar `cancelada`. Não guardar cópia mensal nem anual.
   - Se o produto quiser, o texto do cancelamento pode dizer "e das cópias de segurança em até 30 dias". Isso é `[decisão]` do produto e não bloqueia a subida.
   - A auditoria de 5 anos (`AUD-02`) fica no banco vivo; o expurgo dela é fase 2 (D4).
2. **Cifra.** O backup fica cifrado em repouso com chave que não está no servidor da aplicação: KMS da conta de backup na A, chave do pgBackRest e do restic no cofre na B e na C. Uma cópia da chave fica com o dono, fora do provedor.
3. **Restauração testada.**
   - Antes do primeiro cliente e depois uma vez por mês, o devops restaura o backup mais recente num ambiente descartável: banco e uma amostra de arquivos.
   - O teste confere que o seed ou a empresa de teste abre, que `migrate_schemas` não acusa nada e que uma foto abre pela URL assinada.
   - O resultado vai para um registro em `infra/backup/`, com data, duração e quem fez.
   - Restauração que não foi testada não conta como backup.
4. **Django só pelo proxy.** Nenhuma porta do backend, do Next, do Postgres ou do Redis fica publicada. `GIRO_REDES_PROXY` é a sub-rede real do compose ou da VPC (`prod.py` já recusa rede vazia ou aberta). O teste de subida confere de fora que só 80 e 443 respondem.
5. **Cofre.** Todos os segredos de `infra/deploy/producao.env.example` ficam no cofre. `DATABASE_URL_MIGRACAO` (`giro_migracao`) só vai para o `migrar` e para o worker próprio do apagamento (`aud_08_apagar_empresas`, M-01 da T-355); o backend, o worker comum e o beat usam `giro_app`. A lista de IPs do Admin (ADR 0029) é um arquivo do cofre, vazio por padrão.
6. **Contas.** A raiz da conta do provedor fica com MFA e sem uso diário, com um usuário por pessoa e alerta de custo. A conta ou o bucket de backup tem credencial própria, que a aplicação não tem.
7. **Homologação** fica no mesmo provedor, com o menor tamanho, buckets e cofre próprios, e o Asaas sandbox.

## O que o dono precisa contratar

| Item | Para quê | Observação |
| --- | --- | --- |
| Domínio `girolocadoras.com.br` | Endereço de todas as empresas e da plataforma | No registro.br, cerca de R$ 40 por ano. Confirmar se já está registrado em nome do Giro. O DNS vai para o Route 53 (A) ou para a Cloudflare (B e C) |
| Hospedagem | A opção escolhida | Uma conta de produção e, na A, uma segunda conta só de backup. Cartão da empresa, MFA, alerta de custo |
| Asaas, conta de produção | Faturas da assinatura (conta principal) e Pix e boleto das locadoras (subcontas, ADR 0007) | Conta no CNPJ do Giro, com a aprovação cadastral do Asaas. Confirmar com o Asaas a liberação de subcontas pela API (white label) e a taxa por cobrança. A chave vai só para o cofre |
| WhatsApp | Convites, cobrança e régua (`USR-01`, `AUT-03`) | Meta Business verificada, um número só do Giro e a API oficial (WhatsApp Cloud API) ou um parceiro oficial; cobrança por conversa. **O código ainda só tem o provedor falso**: a integração real precisa de contrato e tarefa próprios, e a escolha do provedor pede ADR (integração externa) |
| E-mail transacional | Convite, senha, avisos, faturas | SMTP de um serviço transacional (Amazon SES em São Paulo na A; Brevo, Postmark ou similar na B e na C), com SPF, DKIM e DMARC no domínio |
| Sentry | Erros do backend e do worker | Plano gratuito no piloto |
| Cofre (só B e C) | Segredos | Bitwarden Secrets Manager ou Doppler, plano gratuito |
| Backup fora do provedor (só B e C) | Destino cifrado | Backblaze B2 ou Cloudflare R2, poucos reais por mês no piloto |

A NFS-e da assinatura segue à mão pela equipe no portal da prefeitura até a T-197 (D5): não pede contratação aqui.

## Recomendação do arquiteto

**Opção A (AWS São Paulo), com o Redis em contêiner no piloto.** É a única das três que entrega, sem código nosso:
- os dados no Brasil;
- o banco gerenciado, com recuperação até o minuto;
- o backup numa conta separada e travada;
- um cofre nativo.

Isso cobre o M-02 com menos peças para a equipe operar. A diferença de custo para a C, de cerca de R$ 300 por mês no piloto, compra operação e residência dos dados.

**Se o custo pesar mais,** a C é a alternativa: banco gerenciado, com o backup fora da conta por um job nosso.

**A B só vale com alguém que cuide do Postgres no dia a dia,** e não é o caso hoje.

## Consequências

### O que a opção B, escolhida pelo dono, pede de nós

- **Provedor:** a preferência é um provedor com região no Brasil, como a Magalu Cloud, com VPS e object storage compatível com S3. Assim os dados ficam no país. Se nenhum servir (preço, tamanho de VPS ou object storage), vale um provedor de fora, com o aviso de privacidade abaixo.
- **Backup:** pgBackRest (ou WAL-G) cifrado para o banco e restic cifrado para os arquivos, os dois para um bucket de **outro provedor** (Backblaze B2 ou Cloudflare R2), com retenção de 30 dias. A chave fica no cofre e com o dono. A restauração é testada e registrada como manda o item 3 acima.
- **Monitoramento, que fica conosco:** saúde do Postgres (conexões, replicação de WAL para o backup, tamanho e vacuum), disco da VPS e do volume do banco (alerta a partir de 80%), memória, falha do job de backup e validade do certificado. Os alertas vão por e-mail para o dono e para quem estiver de plantão.
- **Atualização, também conosco:**
  - patches de segurança do sistema da VPS (atualização automática dos de segurança, reinício planejado);
  - versão menor do Postgres 16 e imagens do Redis e do nginx, uma vez por mês;
  - registro do que foi atualizado.
- **Aviso de privacidade:** se os dados ficarem fora do Brasil, o aviso de privacidade e os termos dizem que há transferência internacional (LGPD, art. 33). Isso fica a confirmar com o Produto antes do primeiro cliente.
- **Cofre:** Bitwarden Secrets Manager ou Doppler, como descrito na opção B.

### Para todas as opções

- O devops faz a "Subida de produção" do M-02: rede, cofre, certificado, backup e o primeiro teste de restauração registrado, com o `teste-subida-producao.sh` adaptado ao provedor. O worker do apagamento (M-01) entra no mesmo compose.
- `infra/README.md` troca "a definir em ADR" pela opção escolhida.
- A integração real de WhatsApp e o e-mail transacional viram tarefas próprias; a de WhatsApp precisa de ADR.
