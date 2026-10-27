# T-353 · O que falta para fechar a fase 1 · produto → orquestrador

Análise sem mudança de regra, feita sobre a `origin/main` em 626d432 (25 out 2026).

**Fontes:**
- `docs/plano.md`: núcleo do MVP e "Critérios de pronto do MVP".
- `docs/regras-de-negocio.md`: marcas de fase e as decisões da T-190, da T-283 e do MEMORY.md de 14 out.
- `tarefas/backlog.md`: seção Fase 1 e "Fase 2 em diante".
- `docs/telas/README.md`: rotas do menu e cartões de Configurações.
- Rotas do frontend (`frontend/src/app`), apps e agenda do Celery do backend.
- Os `xfail` em `backend/tests`.
- Testes com o código da regra no nome: das 159 regras, 42 não têm teste com o código no nome.

**Aviso:** `docs/qa/cobertura-de-regras.md` é de 07 out e está desatualizada; quase tudo ali aparece como "esqueleto" ou "sem critério". Não serve como fonte, e uma tarefa abaixo pede para refazê-la.

## Resumo

O núcleo da fase 1 funciona: locação de ponta a ponta com vistoria, clientes, veículos, movimentações, contas a receber, caixa, despesas, aprovações, usuários com 2 etapas, auditoria, filiais, marca, assinatura, cancelar e pausar. Os critérios de pronto do `plano.md` estão atendidos no código, com uma exceção: a implantação não fecha. Há quatro bloqueios para pôr uma locadora real em uso:

1. **Uma empresa nova não termina a implantação pela tela.** Faltam as telas de Tabelas de preço e de Modelos de contrato, e os passos Filial, Preços, Contrato, Recebimentos e Equipe do assistente. Sem preço, não se aluga.
2. **Módulos por plano pela metade (T-196).** O menu já esconde o módulo fora do plano, mas a API não recusa as rotas dele, e `pendencias_dos_modulos` devolve vazio. A recusa do downgrade com algo aberto (`PLT-12`, CA-ASS-24) não acontece.
3. **O catálogo dos planos promete o que não existe** (`PLT-11`). O Profissional e o Completo listam vendas, manutenção, comissões, conciliação e relatórios, que são da fase 2. Pede decisão do dono (D1).
4. **Não há ambiente de produção.** Não existe ADR de hospedagem, e o frontend não tem deploy. Falta a conta de produção do parceiro de pagamento e do WhatsApp, e o domínio continua sem registro. Sem isso, não há piloto.

## Por módulo

### Locação, vistoria e devolução (LOC, VIS, DEV)
- **Pronto:** nova locação, detalhe, vistoria de saída e devolução pelo celular, acerto da caução, renovação, troca, encerramento antecipado, contrato e assinatura pelo celular (`/assinar`). As tarefas `AUT-02` (devolução atrasada) e de rascunhos sem uso estão agendadas.
- **Falta:** `AUT-01`, o lembrete de devolução às 08:00 por WhatsApp. Não há tarefa no Celery, e a regra não marca fase.
- **Recomendo:** fazer na fase 1. É curto, usa o canal de WhatsApp que a `AUT-03` já usa e reduz atraso, que é o dinheiro da locadora.

### Clientes (CLI)
- **Pronto:** cadastro, análise, bloqueio e desbloqueio, lista com o filtro de filial.
- **Fase 2, já decidido:** leitura da CNH-e (`CLI-11`, decisão de 16 out) e consulta de crédito paga.
- **Falta:** nada para a fase 1.

### Veículos e movimentações (VEI, MOV)
- **Pronto:** frota, ficha, cadastro com leitura do CRLV-e, movimentações (quadro, nova, parada, chegada) e baixa com movimentação aberta.
- **Falta:**
  - a carga do catálogo completo de modelos (T-339, fonte provisória da Parallelum, ADR 0031). Hoje o catálogo tem 29 modelos, e uma locadora real cadastra modelos fora dessa lista;
  - a divergência que sobrou da T-275 (selo e fotos da `Veiculo-Desktop`). Não mexi nas telas de Veículos, como pedido.
- **Fica para depois:** o contrato com a FIPE (T-338), que não bloqueia: a fonte provisória cobre.

### Financeiro (FIN)
- **Pronto:**
  - contas a receber com régua (`AUT-03`) e baixa pelo parceiro (`AUT-05`);
  - caixa do dia com fechamento automático (`AUT-08`);
  - despesas com aprovação e exportação.
- **Fase 2, já decidido:**
  - conciliação (`FIN-11`, `FIN-12`, `AUT-12`) e relatórios com a DRE (`FIN-13`, `FIN-14`). São os xfail `test_fin_12_seed_019_31_*` e `test_fin_13_seed_019_31_*`, e o backlog e o `GIRO_MODULOS_ATIVOS` já os põem na fase 2;
  - a tela Comissões;
  - Pix Automático na locação (`AUT-04`, decisão de 16 out).
- **Pede decisão (D2): comissão de locação.** A `FIN-09` faz a comissão de locação nascer e mudar de estado, mas a tela Comissões é da fase 2. O fechamento do mês (`AUT-10`) não existe, e ninguém vê nem paga a comissão pelo sistema. Recomendo que a comissão inteira (`FIN-09`, `FIN-10` e `AUT-10`) vá para a fase 2, junto com a tela. O que o código já grava fica guardado, e a locadora paga como paga hoje.

### Aprovações (APR)
- **Pronto:** pedidos de desconto, encerramento e despesa, a tela com indicadores e "Meus pedidos".
- **Fase 2, já decidido:** aprovação esquecida (`APR-08`, `AUT-09`).
- **Falta:** nada para a fase 1.

### Usuários, acesso e auditoria (USR, AUD)
- **Pronto:** login, convite, 2 etapas com reconfirmação, esqueci a senha, perfis e menu, auditoria e a exportação em CSV, suporte Giro com as recusas da `PLT-07`.
- **Falta, baixa severidade, já no backlog:**
  - T-159: o login revela o e-mail com convite pendente;
  - T-160: a API navegável do DRF continua ligada em produção. Esta precisa entrar antes de produção.
- **Pede decisão (D3): tela Meu perfil.** Não há a tela (trocar senha, ligar as 2 etapas por vontade própria). A `USR-02` diz que as 2 etapas são opcionais para gerente, vendedor e vistoriador, mas sem a tela eles não têm onde ligar. Recomendo deixar para a fase 2. Quem é obrigado a usar liga no primeiro acesso, e trocar a senha já funciona pelo "Esqueci a senha".
- **Pede decisão (D4): expurgo de 5 anos.** O expurgo da auditoria (`AUT-16`, `AUD-02`) não está agendado. Recomendo a fase 2, porque nenhum evento terá 5 anos antes de 2031.

### Plataforma, assinatura, cancelar e pausar (PLT, AUD-08)
- **Pronto:**
  - faturas, régua (`AUT-13`), cartão pela página do parceiro, mudar de plano;
  - cancelar, pausar e desfazer, com a janela de 5 minutos para as 2 etapas recentes;
  - aviso e apagamento do `AUD-08`;
  - fim do acesso de suporte (`AUT-15`).
- **Falta:**
  - **T-196, módulos por plano:** a API recusa as rotas do módulo fora do plano, e `pendencias_dos_modulos` conta o que está aberto (CA-ASS-15, CA-ASS-22 a 25);
  - **reativar a empresa cancelada** (`PLT-06`, CA-ASS-46): o xfail `test_plt_06_reativar_so_com_atrasada_paga` mostra que `reativar_empresa` não existe. A regra diz que a equipe reativa nos 90 dias, e isso tem que existir antes do 90º dia do primeiro cancelamento real;
  - **NFS-e da assinatura** (T-197, `PLT-15`): bloqueada pelo contador e pelo cadastro municipal. Pede decisão (D5).
- **Fase 2, já decidido:** compra pública e painel da plataforma (`PLT-10`, `PLT-16`, telas `Compra-*` e `Plat-*`). No MVP, a equipe cria a empresa pelo Django Admin (MEMORY.md, 14 out).
- **Pede decisão (D1), catálogo da fase 1.** Pela `PLT-11`, nenhum plano promete o que não existe, mas hoje o Profissional e o Completo listam vendas, manutenção, comissões, conciliação e relatórios (`plataforma/catalogo.py`, migração `0005_planos_iniciais`). Opções:
  - **A (recomendo):** na fase 1, a equipe vende o Essencial e o Profissional, e o texto do Profissional lista só o que existe (despesas, Pix e boleto automáticos pelo parceiro, WhatsApp na régua); o Completo não é vendido até ter o que o diferencia;
  - B: vender os três com o texto atual, que contraria a `PLT-11`;
  - C: trazer vendas para a fase 1, o maior módulo que falta.
  Na opção A, o preço do Profissional é do dono: o mesmo ou um preço de entrada.

### Implantação (IMP)
- **Pronto:**
  - assistente com Marca, Ramo e Importar dados;
  - "Continuar implantação" em Configurações;
  - importação de dados, que atende o critério "dados antigos migrados".
- **Falta, bloqueio 1 do resumo:**
  - telas de Tabelas de preço (`/admin/precos`) e Modelos de contrato (`/admin/contratos`). As rotas da API existem, e os cartões de Configurações abrem para nada;
  - os passos Filial, Preços, Contrato, Recebimentos e Equipe do assistente, hoje com "Esta etapa ainda não está disponível aqui.".
- **Recebimentos (passo 10):** depende da subconta da locadora no parceiro, que não tem contrato de tela. Pede o arquiteto.
- **Pede decisão (D6): implantação parada.** O aviso de implantação parada (`AUT-14`, `IMP-06`) não existe. Recomendo a fase 2, junto com a compra pública. Enquanto a equipe cria cada empresa, ela acompanha a implantação à mão.

### Vendas, manutenção, comissões, conciliação e relatórios
Fase 2, já decidido: rotas marcadas "fase 2" em `docs/telas/README.md`, fora de `GIRO_MODULOS_ATIVOS`, e com os xfail `SEM_VENDAS` e `test_man_03_*`. Nada a fazer na fase 1, só a decisão D1 sobre o que o catálogo promete.

### Infra e operação
- **Falta:**
  - ADR de hospedagem (`infra/README.md` diz "a definir em ADR");
  - ambiente de produção com o frontend, banco gerenciado, backup e Sentry;
  - contas de produção do parceiro de pagamento e do WhatsApp;
  - registro do domínio, aberto em "Pontos em aberto" das regras.
- **Ainda no backlog e pequenas:**
  - T-281: o seed em banco limpo com as configurações de teste;
  - T-165: PNG com paleta perde as cores.

## Decisões do dono

| | Pergunta | Recomendação do produto |
| --- | --- | --- |
| D1 | O que se vende na fase 1, se o Profissional e o Completo listam módulos da fase 2 (`PLT-11`) | A: Essencial e Profissional, este só com o que existe; Completo fora até ter o que o diferencia. Preço do Profissional com o dono |
| D2 | Comissão de locação sem tela nem fechamento do mês (`FIN-09`, `FIN-10`, `AUT-10`) | Tudo para a fase 2, com a tela Comissões |
| D3 | Tela Meu perfil (2 etapas opcionais da `USR-02`, trocar senha) | Fase 2 |
| D4 | Expurgo de 5 anos da auditoria (`AUT-16`) | Fase 2 |
| D5 | NFS-e da assinatura bloqueada pelo contador (T-197, `PLT-15`) | A equipe emite a nota à mão no portal da prefeitura até a T-197 destravar. A cobrança real não espera |
| D6 | Aviso de implantação parada (`AUT-14`, `IMP-06`) | Fase 2, com a compra pública |
| D7 | Hospedagem e contas de produção (parceiro, WhatsApp, domínio) | Escolher já: é o caminho mais longo e não depende de código |

Se o dono aceitar as recomendações, o produto registra as mudanças de fase nas regras (marca "fase 2" em `FIN-09`, `FIN-10`, `AUT-10`, `AUT-14`, `AUT-16` e na tela Meu perfil) numa tarefa própria.

## Tarefas sugeridas, na ordem

Sem número: o orquestrador numera.

1. **arquiteto · ADR de hospedagem e produção** (D7). **Regras:** S-15, ADR 0027. **Pronto quando:** há uma ADR com onde rodam backend, frontend, banco, Redis e arquivos, com backup, Sentry, certificado curinga e custo mensal. O devops tem uma lista do que contratar.
2. **produto · Regras das decisões D1 a D6.** **Regras:** PLT-11, PLT-12, FIN-09, FIN-10, AUT-10, AUT-14, AUT-16, USR-02, PLT-15. **Pronto quando:** as marcas de fase e o catálogo da fase 1 estão nas regras, com a tabela de decisões e os critérios ajustados (CA-ASS do catálogo).
3. **backend · Módulos por plano** (T-196 existente; reabrir com o escopo de hoje). **Regras:** PLT-12, PLT-04. **Pronto quando:**
   - a rota de módulo fora do plano dá 403 `PLT-12`;
   - `pendencias_dos_modulos` conta o que está aberto por grupo (CA-ASS-15: 1 despesa aguardando aprovação e 2 a pagar no seed de 07 out);
   - passam o `test_plt_12_*` e o CA-ASS-22 a 25;
   - o catálogo da API segue a D1.
4. **backend · Reativar a empresa cancelada.** **Regras:** PLT-06, AUD-08. **Pronto quando:**
   - existe `reativar_empresa` no Django Admin da plataforma, com a recusa 409 `fatura_em_atraso` ("Receba a fatura em atraso antes de reativar.");
   - a fatura nova vence no dia seguinte ao fim do período pago ou no dia da volta, como na `PLT-06`;
   - o xfail `test_plt_06_reativar_so_com_atrasada_paga` vira teste comum (CA-ASS-46).
5. **arquiteto · Contrato dos passos que faltam no assistente.** **Regras:** IMP-05, LOC-01, FIL-01, USR-01, FIN-04. **Pronto quando:** cada passo (Filial, Preços, Contrato, Recebimentos, Equipe) diz quais rotas usa. Os quatro primeiros reaproveitam as rotas de filiais, preços, modelos de contrato e convites. O de Recebimentos define como a locadora cria ou liga a subconta do parceiro.
6. **frontend · Tabelas de preço** (`/admin/precos`, tela `Precos`), depois do 5. **Regras:** LOC-01, FIL-04. **Pronto quando:** o administrador vê e muda o preço por categoria, da empresa ou da filial, com o histórico, pela API e com os números do seed. Serve também ao passo Preços.
7. **frontend · Modelos de contrato** (`/admin/contratos`), depois do 5. **Regras:** as das cláusulas e do contrato digital (`docs/api/contratos.md`). **Pronto quando:** dá para ver, editar, pré-visualizar, publicar e arquivar, e para escolher um modelo pronto. Serve também ao passo Contrato.
8. **frontend · Passos Filial, Preços, Contrato e Equipe do assistente**, depois do 6 e do 7. **Regras:** IMP-05. **Pronto quando:** os quatro passos usam as telas já feitas dentro da casca (`CascaDoAssistente`), Continuar e Pular pela API, também no Essencial.
9. **backend e frontend · Passo Recebimentos**, depois do 5. **Regras:** FIN-04, PLT-12. **Pronto quando:** a locadora do Profissional liga a subconta pelo passo, e o Essencial não vê o passo.
10. **backend · Lembrete de devolução** (`AUT-01`). **Regras:** AUT-01. **Pronto quando:** a tarefa das 08:00 manda WhatsApp a cada cliente com devolução no dia, com o horário e o endereço da filial, uma vez por locação. Teste `test_aut_01_lembrete_de_devolucao` com a LOC-2836, que devolve em 14 out.
11. **backend · Carga do catálogo completo** (T-339 existente).
12. **backend · Antes de produção** (T-160 e T-159 existentes, mais a T-281).
13. **devops · Ambiente de produção**, depois do 1. **Pronto quando:** homologação e produção no ar com o frontend, banco gerenciado, backup testado com restauração, Sentry, domínio e certificado, e as chaves de produção no cofre.
14. **qa · Fechamento da fase 1**, por último. **Pronto quando:**
    - `docs/qa/cobertura-de-regras.md` está refeita a partir dos testes de hoje;
    - as 42 regras sem teste com o código no nome foram conferidas: fase 2, teste com outro nome ou falta;
    - o E2E percorre os critérios de pronto do `plano.md` na homologação, com a Moto Rápida: implantação, locação, devolução, cobrança, caixa e 2 etapas.

A T-165 (PNG com paleta) e a divergência da T-275 podem entrar em qualquer momento, sem bloquear.
