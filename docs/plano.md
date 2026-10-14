# Plano do Sistema de Gestão de Venda e Aluguel de Veículos

Oct 6, 2026 · @João Victor

> **Leia primeiro:** este é o plano original (visão, módulos, roadmap). Onde ele divergir de `regras-de-negocio.md`, valem as regras. Divergências conhecidas:
> - Estados do veículo: valem os 8 das regras (`disponivel`, `reservado`, `alugado`, `em_manutencao`, `indisponivel`, `a_venda`, `vendido`, `baixado`); "em preparação" não existe. Veículo da troca entra como `indisponivel` (VEN-05).
> - Pagamento parcial não existe (FIN-01): paga a parcela inteira ou renegocia.
> - 2FA obrigatório para administrador e financeiro, opcional para os demais (USR-02).
> - Exclusão: `ativo=False` ou status cancelado, não `deletado_em`. Dinheiro só em centavos inteiros (ADR 0003).
> - Perfis do MVP: administrador, gerente, vendedor, vistoriador, financeiro. Mecânico e portal do cliente ficam para depois.
> - O mapa de telas atualizado está em `telas/README.md` (63 telas, 123 arquivos); listas de Clientes, Vendas e Filiais já foram desenhadas.


## Visão geral e objetivos

O sistema centraliza em uma única plataforma web a venda e a locação de motos e automóveis: estoque, clientes, vendedores, contratos, financeiro, manutenção e despesas, com controle de acesso por perfil e trilha de auditoria.

**Objetivos principais**

- Saber, a qualquer momento, onde está cada veículo (disponível, alugado, reservado, em manutenção, vendido) e quanto ele rende ou custa.
- Automatizar contratos de venda e locação, cobranças recorrentes, multas por atraso e comissões de vendedores.
- Dar visão financeira completa: contas a pagar e a receber, fluxo de caixa, DRE gerencial e rentabilidade por veículo.
- Reduzir custo de frota com manutenção preventiva programada por quilometragem e data.
- Atender exigências legais brasileiras: LGPD, emissão de nota fiscal, transferência de propriedade (ATPV-e) e controle de multas de trânsito.

**Escopo:** produto SaaS white label vendido a micro e pequenas empresas do segmento; cada empresa assinante opera com uma ou várias filiais (lojas/pátios), operando venda de veículos novos e seminovos, locação diária/semanal/mensal e locação para motoristas de aplicativo e entregadores (modelo muito comum em motos).

## Modelo white label e multiempresa

Uma única instalação atende várias empresas: cada uma vê o sistema com a própria marca, tem os dados totalmente isolados das demais e paga uma assinatura mensal.

**Isolamento de dados**

- Recomendado: `django-tenants`, com um schema PostgreSQL por empresa. O isolamento é forte, e backup, exportação ou remoção de um cliente ficam simples.
- Alternativa: banco compartilhado com `empresa_id` em todas as tabelas. É mais simples de operar, mas um filtro esquecido expõe dados de outro cliente.
- Cada empresa acessa por subdomínio próprio (empresa.girolocadoras.com.br); domínio próprio do cliente fica para a fase 4.

**O que cada empresa personaliza**

- Logo, favicon, nome exibido e cor primária, aplicados em todo o sistema, nos PDFs e nos e-mails.
- Modelos de contrato, mensagens de WhatsApp e e-mail com a marca dela.
- Tabelas de preço, regras de comissão, plano de contas e módulos ativos conforme o plano contratado.

**Painel da plataforma (seu uso, como dono do produto)**

- Cadastro de empresas, planos e limites (veículos, usuários, filiais).
- Cobrança recorrente da assinatura e suspensão automática por inadimplência.
- Métricas de uso por cliente e acesso de suporte com registro em auditoria.

**Entrada de novos clientes**

- Cadastro self-service com teste grátis, assistente de configuração inicial e importação de planilha de veículos e clientes.

**Pontos legais:** perante a LGPD, você é operador dos dados de cada cliente; são necessários termos de uso e um acordo de tratamento de dados com cada empresa.

**Impacto no roadmap:** multiempresa e personalização de marca entram na fase 1. Planos, módulos por plano, cobrança da assinatura, cancelar e pausar também entram na fase 1 (decisão do dono do produto em 14 out 2026, T-190, `PLT-01` a `PLT-15`); antes, ficavam na fase 3. Continuam para depois a tela de cobrança da plataforma (`Plat-Cobranca`, fase 2) e os adicionais (filial, pacote de veículos, assinatura digital avulsa).

## Implantação de um novo cliente

O cliente faz a primeira locação no mesmo dia, sem depender de suporte; o mínimo para operar é empresa, uma filial, um veículo e um cliente.

1. **Compra:** escolhe o plano no site de vendas, informa CNPJ e responsável e paga (ou inicia teste grátis de 14 dias). O sistema cria o ambiente isolado e o subdomínio e envia o e-mail de boas-vindas.
2. **Primeiro acesso:** o responsável cria a senha e ativa a autenticação em dois fatores.
3. **Assistente de configuração** (cada passo pode ser pulado e retomado):
   1. Empresa e marca: dados preenchidos pelo CNPJ, logo e cor com pré-visualização ao vivo.
   2. Primeira filial (matriz) e horário de funcionamento.
   3. O que a empresa faz: locação e/ou venda, motos e/ou carros; liga só os módulos necessários.
   4. Tabela de preços a partir de modelos prontos.
   5. Modelo de contrato: multa, caução, franquia de km, tolerância de atraso.
   6. Recebimentos: conta bancária, Pix e boleto (opcional no início).
   7. Importação de veículos e clientes por planilha modelo, com erros apontados por linha.
   8. Convite da equipe com perfil de cada pessoa.
4. **Checklist de primeiros passos** no dashboard: locação de teste completa, app instalado no celular de vistoria, WhatsApp conectado.
5. **Acompanhamento pela plataforma:** painel mostra em qual passo cada cliente parou; mensagens automáticas no 1º, 3º e 7º dia; chamada de implantação nos planos maiores.

## Perfis, autenticação e permissões

O acesso é controlado por perfis (RBAC) com permissões granulares por módulo e ação, restritas à filial do usuário quando aplicável.

| Perfil | O que acessa | Restrições |
| --- | --- | --- |
| Administrador | Tudo, incluindo configurações, usuários, filiais e auditoria | Nenhuma |
| Gerente | Todos os módulos operacionais e relatórios da sua filial; aprova descontos e cancelamentos | Não altera configurações globais |
| Vendedor | Clientes, propostas, vendas e locações próprias, suas comissões | Desconto limitado ao teto do perfil; não vê margem nem custo |
| Financeiro | Contas a pagar/receber, caixa, conciliação, comissões, relatórios | Não altera contratos assinados |
| Operador de pátio / vistoriador | Check-in/check-out, vistorias com fotos, quilometragem, combustível | Sem acesso a valores |
| Mecânico / responsável de frota | Ordens de serviço, plano de manutenção, peças | Sem acesso ao financeiro geral |
| Cliente (portal, fase 3) | Seus contratos, boletos, segunda via, agendamento | Somente seus dados |

**Autenticação e segurança**

- Login por e-mail e senha com hash forte (Argon2 ou bcrypt), política de senha mínima e bloqueio após tentativas falhas.
- JWT de curta duração (15 min) + refresh token rotativo armazenado em cookie httpOnly.
- Autenticação em dois fatores (TOTP) obrigatória para Administrador, Gerente e Financeiro.
- Recuperação de senha por e-mail com token de uso único e expiração.
- Sessões ativas visíveis e revogáveis pelo usuário e pelo administrador.
- Log de auditoria imutável: quem fez, o quê, quando, IP, valores antes e depois — obrigatório em contratos, pagamentos, descontos e estornos.
- Permissões configuráveis pelo administrador (perfil base + ajustes por usuário).

## Telas por perfil

Cada perfil entra pelo mesmo login da empresa e cai numa tela inicial própria. O menu só mostra o que o perfil pode usar. O painel da plataforma é separado: tem login próprio e só a sua equipe acessa.

| Perfil | Tela inicial | O que usa no dia a dia | Onde mais trabalha |
| --- | --- | --- | --- |
| Dono do produto (você) | Visão da plataforma | Empresas, implantações, cobrança das assinaturas, suporte, planos, equipe interna, auditoria | Desktop |
| Equipe interna (suporte, financeiro, sucesso do cliente) | Visão da plataforma, com menu limitado pela função | Chamados, entrar como suporte (com motivo e prazo), cobrança, implantações | Desktop |
| Administrador da locadora | Visão geral de todas as filiais | Tudo da operação + Administração: empresa e marca, filiais, usuários, assinatura, auditoria, exportar, configurações | Desktop |
| Gerente de filial | Início do gerente (aprovações no topo) | Aprovar descontos, cancelamentos e despesas; locações, frota, manutenções, caixa da filial | Celular e desktop |
| Vendedor | Início do vendedor (meta e propostas) | Nova locação, nova venda, clientes, veículos à venda | Celular |
| Vistoriador | Agenda de vistorias do dia | Vistoria de saída, devolução com fotos, consulta de veículo | Celular |
| Financeiro | Início do financeiro (saldo e tarefas do dia) | Contas a receber, contas a pagar, caixa e bancos, conciliação, comissões, relatórios e DRE | Desktop |

O funcionário recebe um convite por e-mail ou WhatsApp, cria a senha e já entra com o perfil e a filial definidos pelo administrador.

## Mapa de telas

São 63 telas desenhadas, em desktop e celular (123 arquivos), no [canvas de design](https://claude.ai/artifact/5BZCQjBRVfmKwvoDEjEFnb) (cópia local em `docs/telas/`). Todas usam o design system white label: a cor da marca troca em todas de uma vez e os menus já navegam entre elas.

| Área | Telas | Quem usa | Qtd. |
| --- | --- | --- | --- |
| Compra e implantação | Escolha do plano, pagamento, conta criada, criar senha, assistente de 8 passos (marca, filial, ramo e veículos, preços, contrato, recebimentos, importar dados, equipe) | Administrador (1ª vez) | 12 |
| Acesso e início | Login, visão geral, visão geral pós-implantação, aceitar convite | Todos | 4 |
| Inícios por perfil | Gerente, vendedor, vistoriador, financeiro | Cada perfil | 4 |
| Operação | Frota, ficha do veículo, nova locação, locações, detalhe da locação, vistoria de saída, devolução, manutenções, nova venda, cliente | Gerente, vendedor, vistoriador | 10 |
| Financeiro | Caixa do dia, contas a receber, despesas, comissões, conciliação, relatórios e DRE | Financeiro, gerente, administrador | 6 |
| Administração | Configurações, empresa e marca, filiais, usuários, tabelas de preço, modelos de contrato, integrações, assinatura, auditoria, exportar dados, cancelar assinatura | Administrador | 11 |
| Painel da plataforma | Login, visão da plataforma, empresas, detalhe da empresa, entrar como suporte, implantações, cobrança das assinaturas, suporte, planos e preços, equipe interna, auditoria de acessos | Você e sua equipe | 11 |

Os dados de exemplo são os mesmos em todas as telas: a locadora Moto Rápida (Fortaleza), com Mariana (administradora), Rodrigo (gerente), Bruna (vendedora), João (vistoriador) e Lúcia (financeiro). Assim dá para seguir um caso de ponta a ponta, como a venda da CB 300F com 8% de desconto, que aparece na tela de venda, na aprovação do gerente e nas comissões.

## Telas que ainda faltam

O fluxo principal de cada perfil já está desenhado. Faltam 16 telas, quase todas de apoio:

- [ ] **Acesso e conta:** esqueci a senha, ativar verificação em 2 etapas, meu perfil, notificações
- [x] **Listas:** clientes e vendas (feitas)
- [ ] contas a pagar separada de despesas
- [ ] **Operação:** multas de trânsito (vincular ao locatário), documentos dos veículos com vencimentos, avarias abertas e histórico do vistoriador
- [ ] **Vendedor:** minhas comissões
- [ ] **Cliente final:** assinar contrato pelo celular, pagar com Pix e baixar recibo
- [ ] **Site de vendas (plano Completo):** vitrine de veículos, página do veículo, pedido de proposta

A divergência de preço da Honda Biz foi decidida em 07 out 2026: vale a tabela (R$ 299,40 por semana). Ver "Decisões de 07 out 2026" nas regras.

## Módulos funcionais

São 14 módulos; os sete primeiros formam o núcleo do MVP.

### 1. Dashboard

- Indicadores do dia e do mês: vendas, receita de locação, taxa de ocupação da frota, inadimplência, caixa.
- Alertas: contratos vencendo, devoluções atrasadas, manutenções vencidas, documentos (IPVA, licenciamento, seguro) a vencer, parcelas em atraso.
- Ranking de vendedores e metas.

### 2. Veículos (estoque e frota)

- Cadastro: tipo (moto/carro), marca, modelo, versão, ano fab./modelo, cor, placa, RENAVAM, chassi, combustível, câmbio, cilindrada, quilometragem, opcionais, fotos.
- Finalidade: venda, locação ou ambos; origem: compra, consignação, troca.
- Status com histórico: disponível, reservado, alugado, em manutenção, em preparação, vendido, inativo.
- Custos de aquisição e preparação, preço de venda sugerido, preço mínimo, tabela FIPE de referência.
- Documentação: IPVA, licenciamento, seguro, rastreador, com datas de vencimento e anexos.
- Ficha financeira do veículo: tudo que ele custou e rendeu (base da rentabilidade).

### 3. Clientes

- Pessoa física e jurídica: CPF/CNPJ, RG, CNH (número, categoria A/B, validade), endereço, contatos, referências.
- Upload de documentos (CNH, comprovante de residência, contrato social).
- Análise de crédito/score (integração opcional) e lista de bloqueio.
- Histórico de compras, locações, pagamentos, multas e avarias.
- Consentimento LGPD registrado.

### 4. Vendedores e comissões

- Cadastro vinculado ao usuário e à filial; metas mensais.
- Regras de comissão configuráveis: % sobre venda, % sobre margem, valor fixo por locação, bônus por meta.
- Comissão gerada automaticamente ao faturar e liberada ao receber (ou na assinatura, conforme regra).
- Extrato de comissões e fechamento mensal integrado ao contas a pagar.

### 5. Vendas

- Funil: lead → proposta → negociação → venda fechada / perdida (com motivo).
- Proposta com simulação de pagamento: à vista, entrada + parcelas próprias, financiamento bancário, veículo na troca.
- Avaliação de veículo na troca, que entra no estoque ao concluir.
- Aprovação de desconto acima do limite do vendedor.
- Geração de contrato de compra e venda, recibo, termo de entrega e checklist de transferência (ATPV-e).
- Pós-venda: garantia e revisões programadas.

### 6. Locações e contratos

- Tabelas de preço por categoria e período (diária, semanal, mensal), temporada e franquia de km.
- Reserva com verificação de disponibilidade por período (calendário da frota).
- Contrato com caução, seguro/proteção, adicionais (capacete, baú, cadeirinha, condutor extra).
- Check-out e check-in com vistoria: fotos, quilometragem, combustível, avarias marcadas em diagrama.
- Cobrança recorrente para locação longa (motoristas de aplicativo): semanal ou mensal, com bloqueio automático por inadimplência.
- Renovação, aditivo, troca de veículo, encerramento antecipado com cálculo de multa.
- Fechamento: km excedente, combustível, avarias, atraso, multas de trânsito; devolução ou retenção de caução.
- Locação com opção de compra (aluguel que vira venda).

### 7. Financeiro

- Contas a receber e a pagar com parcelas, juros, multa, descontos e baixa parcial.
- Plano de contas e centros de custo (por filial e por veículo).
- Caixa e contas bancárias, transferências, conciliação bancária (importação OFX).
- Meios: dinheiro, Pix, boleto, cartão; integração com gateway para emissão e baixa automática.
- Fluxo de caixa previsto x realizado, DRE gerencial, inadimplência por faixa de atraso.
- Estornos e cancelamentos sempre com motivo e aprovação.

### 8. Manutenções

- Plano preventivo por modelo: a cada X km ou Y meses (óleo, pneus, freios, correia/relação).
- Alertas automáticos baseados na quilometragem informada no check-in.
- Ordem de serviço: oficina interna ou externa, peças, mão de obra, fotos, status, garantia do serviço.
- Veículo fica indisponível para locação enquanto a OS estiver aberta.
- Custo lançado automaticamente no contas a pagar e na ficha do veículo.

### 9. Despesas

- Despesas por veículo (combustível, lavagem, guincho, documentação) e gerais (aluguel, salários, marketing).
- Categorias, recorrência, anexos de comprovante e aprovação por valor.
- Rateio entre filiais ou centros de custo.

### 10. Multas e sinistros

- Registro de multas de trânsito, identificação do locatário na data/hora, indicação de condutor e cobrança.
- Sinistros: boletim de ocorrência, acionamento de seguro, franquia, cobrança do cliente.

### 11. Documentos e contratos

- Modelos de contrato editáveis com variáveis (cliente, veículo, valores).
- Geração de PDF e assinatura eletrônica (integração).
- Repositório de anexos por cliente, veículo e contrato.

### 12. Fiscal

- Emissão de NF-e (venda de veículo) e NFS-e quando aplicável, via integrador.
- Locação de bens móveis em geral não sofre ISS; validar o enquadramento com o contador.

### 13. Relatórios

- Vendas por período, vendedor, modelo e margem.
- Ocupação da frota, receita por veículo, ROI e ponto de equilíbrio por veículo.
- Custo de manutenção por veículo e por km rodado.
- Comissões, inadimplência, fluxo de caixa, DRE.
- Exportação para Excel e PDF.

### 14. Configurações e notificações

- Empresa, filiais, usuários, perfis, tabelas de preço, regras de comissão, plano de contas, modelos de contrato.
- Notificações por e-mail e WhatsApp: lembrete de vencimento, devolução, revisão, documentos.

## Fluxos principais

O status do veículo amarra todos os fluxos: cada venda, locação, devolução e manutenção move o veículo de um status a outro, e só o status Disponível libera nova locação ou venda.

&#91;embedded content: ciclo de vida do veículo · 8 status\]

A retirada sem reserva prévia vai direto de Disponível para Alugado; uma reserva cancelada volta para Disponível.

**Venda**

1. Vendedor registra o lead e cria a proposta (veículo, condições, eventual troca).
2. Desconto acima do limite vai para aprovação do gerente.
3. Cliente aceita; sistema gera contrato, títulos a receber e comissão prevista.
4. Assinatura eletrônica e recebimento da entrada.
5. Emissão da NF-e, entrega com termo e checklist, transferência (ATPV-e).
6. Veículo passa a Vendido; veículo da troca entra em Em preparação.

**Locação**

1. Consulta de disponibilidade e reserva para o período.
2. Validação do cliente (CNH, documentos, crédito) e cobrança da caução.
3. Check-out: vistoria com fotos, km, combustível e assinatura do cliente.
4. Cobranças recorrentes geradas automaticamente durante o contrato.
5. Check-in: nova vistoria, cálculo de km excedente, atraso, combustível e avarias.
6. Fechamento: cobrança final, devolução ou retenção da caução, veículo para Disponível ou Em manutenção.

**Manutenção**

1. Alerta preventivo por km ou data, ou abertura de OS corretiva após vistoria.
2. Veículo bloqueado para locação; OS registra serviços, peças e oficina.
3. Conclusão gera título a pagar e lança o custo na ficha do veículo.
4. Veículo volta para Disponível.

## Modelo de dados

O banco gira em torno de quatro entidades centrais — Veículo, Cliente, Contrato e Lançamento financeiro — e toda tabela operacional carrega `filial_id`, `criado_por`, `criado_em` e `atualizado_em`.

| Grupo | Entidades | Relacionamentos principais |
| --- | --- | --- |
| Acesso | `empresa`, `filial`, `usuario`, `perfil`, `permissao`, `sessao`, `log_auditoria` | Usuário pertence a filial(is) e tem um perfil com N permissões |
| Veículos | `marca`, `modelo`, `veiculo`, `veiculo_foto`, `veiculo_documento`, `veiculo_status_historico`, `leitura_km` | Veículo tem um modelo, N fotos, N documentos e histórico de status |
| Clientes | `cliente`, `cliente_documento`, `cliente_contato`, `consentimento_lgpd` | Cliente tem N contratos, N documentos |
| Comercial | `vendedor`, `meta`, `regra_comissao`, `comissao`, `lead`, `proposta`, `avaliacao_troca` | Proposta liga cliente, vendedor e veículo; vira contrato de venda |
| Contratos | `contrato` (tipo venda/locação), `contrato_item`, `contrato_aditivo`, `reserva`, `tabela_preco`, `vistoria`, `vistoria_avaria`, `caucao` | Contrato liga cliente, veículo(s), vendedor; locação tem vistorias de saída e retorno |
| Financeiro | `plano_contas`, `centro_custo`, `conta_bancaria`, `titulo` (pagar/receber), `parcela`, `pagamento`, `movimento_caixa`, `conciliacao` | Parcela pertence a um título; título pode vir de contrato, OS, despesa ou comissão |
| Manutenção | `plano_manutencao`, `item_plano`, `ordem_servico`, `os_item`, `fornecedor`, `peca` | OS pertence a um veículo e gera título a pagar |
| Despesas e ocorrências | `despesa`, `categoria_despesa`, `multa_transito`, `sinistro` | Despesa e multa podem apontar para veículo e contrato |
| Documentos e fiscal | `modelo_documento`, `documento_gerado`, `assinatura`, `nota_fiscal` | Documento gerado pertence a um contrato |

**Decisões de modelagem**

- Um único `contrato` com campo `tipo` (venda, locação, locação com opção de compra) simplifica relatórios e o financeiro.
- `titulo` tem origem polimórfica (`origem_tipo`, `origem_id`), assim qualquer módulo gera cobrança ou pagamento pelo mesmo caminho.
- Valores em centavos (inteiro) ou `NUMERIC(14,2)`; nunca ponto flutuante.
- Exclusão lógica (`deletado_em`) em cadastros; contratos e pagamentos nunca são apagados, só cancelados com motivo.

## Regras de negócio e requisitos não funcionais

As regras abaixo são as que mais causam prejuízo quando ficam fora do sistema; os valores entre parênteses são padrões configuráveis.

**Regras de negócio**

1. Um veículo não pode ter duas reservas ou locações sobrepostas no mesmo período.
2. Veículo com OS aberta, documento vencido ou seguro vencido fica bloqueado para locação.
3. Locação exige CNH válida na categoria do veículo (A para motos, B para carros) e idade mínima (21 anos).
4. Venda de veículo reservado só com cancelamento da reserva pelo gerente.
5. Desconto acima do limite do vendedor (5%) exige aprovação do gerente, registrada na auditoria.
6. Venda abaixo do preço mínimo exige aprovação do administrador.
7. Atraso na devolução cobra diária extra após tolerância (1 hora).
8. Km excedente à franquia é cobrado por km conforme a tabela da categoria.
9. Locação recorrente com parcela atrasada há mais de N dias (3) gera alerta de bloqueio/recolhimento.
10. Comissão só é liberada para pagamento quando a parcela correspondente for recebida (configurável).
11. Cancelamento de venda estorna comissão, devolve o veículo ao estoque e cancela títulos em aberto.
12. Toda multa de trânsito é associada automaticamente ao contrato ativo na data/hora da infração.
13. Leitura de km nunca pode ser menor que a anterior (exceto correção autorizada).
14. Encerramento de mês financeiro bloqueia alterações em lançamentos daquele período.

**Requisitos não funcionais**

- **Segurança:** HTTPS obrigatório, criptografia de dados sensíveis (CPF, CNH) em repouso, rate limiting, proteção contra OWASP Top 10.
- **LGPD:** finalidade e consentimento registrados, exportação e anonimização de dados do cliente sob solicitação, retenção definida.
- **Desempenho:** telas principais abaixo de 2 s; relatórios pesados em segundo plano com aviso ao concluir.
- **Disponibilidade:** 99,5% no horário comercial; backup diário automático com retenção de 30 dias e teste de restauração mensal.
- **Usabilidade:** responsivo; vistoria pensada para celular (câmera, assinatura na tela).
- **Rastreabilidade:** auditoria em todas as operações financeiras e contratuais.
- **Escalabilidade:** multiempresa e multi-filial desde o início, com isolamento total de dados entre empresas.

## Arquitetura e stack sugerida

A recomendação é um monólito modular em Django (Python) com PostgreSQL: uma equipe pequena entrega mais rápido, e os módulos já nascem separados para virar serviços se um dia for preciso. O Django Admin entrega telas de cadastro prontas desde a fase 1.

&#91;embedded content: arquitetura · 3 camadas e integrações\]

Todas as regras de negócio ficam na API; telas nunca calculam valores nem mudam status por conta própria.

| Camada | Tecnologia sugerida | Alternativa |
| --- | --- | --- |
| Front-end | Next.js (React) + TypeScript, Tailwind, shadcn/ui, TanStack Query, cliente tipado gerado do OpenAPI (drf-spectacular) | Vue/Nuxt |
| Back-end | Django 5 + Django REST Framework, ORM do Django, serializers para validação, Django Admin para back-office | NestJS (TypeScript) |
| Banco de dados | PostgreSQL 16 | MySQL 8 |
| Filas e cache | Redis + Celery e Celery Beat (cobranças recorrentes, alertas, relatórios) | — |
| Arquivos | Armazenamento compatível com S3 | Cloudflare R2 |
| Autenticação | JWT com djangorestframework-simplejwt, 2FA com django-otp, hash Argon2 | Keycloak ou Auth0 |
| PDF e documentos | Templates HTML para PDF com WeasyPrint | — |
| Infraestrutura | Docker, deploy em nuvem (AWS, GCP ou VPS), CI/CD no GitHub Actions | — |
| Monitoramento | Sentry (erros) e logs centralizados | — |

**Integrações a contratar (escolher na fase 1):** gateway de pagamento com Pix e boleto, integrador de NF-e, assinatura eletrônica, API de WhatsApp, consulta FIPE e, opcionalmente, rastreador veicular e consulta de multas/débitos.

## Roadmap de implementação

Com uma equipe de 2 a 3 desenvolvedores, a estimativa é de cerca de 7 meses até o sistema completo, com o MVP em uso real a partir da semana 12.

&#91;embedded content: roadmap · 4 fases e 3 marcos\]

Cada marco no fim de uma fase é o critério para seguir: a fase 2 só começa com o piloto rodando em uma filial. Prazos são estimativas e devem ser revistos após a fase 0.

**Fase 0 — Descoberta (2 semanas, antes da fase 1):** validar regras com a operação, levantar contratos e planilhas atuais, prototipar telas, definir integrações e montar o backlog.

**Critérios de pronto do MVP**

- [ ] Cadastrar veículos e clientes com documentos e fotos.
- [ ] Fazer reserva, check-out, check-in e fechamento de uma locação com vistoria pelo celular.
- [ ] Gerar cobranças recorrentes e dar baixa em pagamentos.
- [ ] Ver contas a pagar e a receber e o caixa do dia.
- [ ] Controlar acesso por perfil com 2FA e auditoria ativa.
- [ ] Dados antigos migrados e conferidos.

## Riscos e próximos passos

O maior risco é tentar entregar tudo de uma vez; o MVP deve operar locação, venda e financeiro básico antes de qualquer integração.

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Escopo grande demais no início | Atraso e sistema que ninguém usa | MVP enxuto com os fluxos que geram receita; demais módulos por fase |
| Regras fiscais e tributárias mal definidas | Autuação e retrabalho | Validar com o contador antes da fase 3; usar integrador de NF-e |
| Migração de dados de planilhas ou sistema antigo | Saldos e históricos errados | Script de importação com validação e conferência em paralelo por 1 mês |
| Inadimplência em locação recorrente | Perda de receita e de veículo | Caução, cobrança automática, bloqueio e integração com rastreador |
| Vazamento de dados pessoais | Multa LGPD e dano à imagem | Criptografia, perfis mínimos, auditoria, backups protegidos |
| Baixa adesão da equipe | Dados incompletos | Telas simples para celular, treinamento e piloto em uma filial |

**Próximos passos**

- [ ] Validar módulos e regras deste plano com sócios, gerentes e financeiro.
- [ ] Definir valores padrão das regras (limites de desconto, tolerância, multas, comissões).
- [ ] Levantar modelos atuais de contrato e documentos.
- [ ] Escolher gateway de pagamento, integrador fiscal e assinatura eletrônica.
- [ ] Desenhar protótipos das telas do MVP (veículos, locação, vistoria, financeiro).
- [ ] Montar o backlog da fase 1 e iniciar o desenvolvimento.
