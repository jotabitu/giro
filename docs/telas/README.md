# Telas de referência

Todas as telas desenhadas no canvas, em HTML estático. Abra qualquer arquivo de `html/` direto no navegador: os estilos vêm de `../design-system/`. Os links entre telas funcionam.

**Como usar:** a tela é a referência visual e de conteúdo, não o código final. O frontend recria cada uma com os componentes do design system (`frontend/src/design-system`). Textos, rótulos, ordem dos campos, estados e números de exemplo devem ser seguidos; quando a tela e `docs/regras-de-negocio.md` divergirem, vale a regra e a divergência vira item em `tarefas/backlog.md`.

Cada tela tem versão `-Desktop` e `-Mobile` (exceto `Main`, que é a visão geral do administrador no desktop).

Canvas original: https://claude.ai/artifact/5BZCQjBRVfmKwvoDEjEFnb

## Implantação

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| 1 · Escolha do plano | [desktop](html/Compra-Planos-Desktop.dc.html) · [celular](html/Compra-Planos-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 2 · Criar conta e pagar | [desktop](html/Compra-Checkout-Desktop.dc.html) · [celular](html/Compra-Checkout-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 3 · Ambiente pronto | [desktop](html/Compra-Pronto-Desktop.dc.html) · [celular](html/Compra-Pronto-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 4 · Primeiro acesso | [desktop](html/Acesso-Senha-Desktop.dc.html) · [celular](html/Acesso-Senha-Mobile.dc.html) | `(publico)/entrar` | `contas` | USR |
| 5 · Empresa e marca | [desktop](html/Onboarding-Marca-Desktop.dc.html) · [celular](html/Onboarding-Marca-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 6 · Assistente: primeira filial | [desktop](html/Onboarding-Filial-Desktop.dc.html) · [celular](html/Onboarding-Filial-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 7 · Assistente: o que a empresa faz | [desktop](html/Onboarding-Ramo-Desktop.dc.html) · [celular](html/Onboarding-Ramo-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 8 · Assistente: tabela de preços | [desktop](html/Onboarding-Precos-Desktop.dc.html) · [celular](html/Onboarding-Precos-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 9 · Assistente: modelo de contrato | [desktop](html/Onboarding-Contrato-Desktop.dc.html) · [celular](html/Onboarding-Contrato-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 10 · Assistente: recebimentos | [desktop](html/Onboarding-Recebimentos-Desktop.dc.html) · [celular](html/Onboarding-Recebimentos-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 11 · Assistente: importar dados | [desktop](html/Onboarding-Importar-Desktop.dc.html) · [celular](html/Onboarding-Importar-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |
| 12 · Assistente: convidar equipe | [desktop](html/Onboarding-Equipe-Desktop.dc.html) · [celular](html/Onboarding-Equipe-Mobile.dc.html) | `(publico)/compra, (empresa)/implantacao` | `plataforma, empresas` | PLT, IMP |

## Acessos e perfis

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| 1 · Dashboard com primeiros passos | [desktop](html/Pos-Dashboard-Desktop.dc.html) · [celular](html/Pos-Dashboard-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| 2 · Convite e aceite do funcionário | [desktop](html/Convite-Desktop.dc.html) · [celular](html/Convite-Mobile.dc.html) | `(publico)/entrar` | `contas` | USR |
| 3 · Início do vistoriador | [desktop](html/Vistoriador-Desktop.dc.html) · [celular](html/Vistoriador-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| 4 · Início do vendedor | [desktop](html/Vendedor-Desktop.dc.html) · [celular](html/Vendedor-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| 5 · Administração › Usuários | [desktop](html/Admin-Usuarios-Desktop.dc.html) · [celular](html/Admin-Usuarios-Mobile.dc.html) | `(empresa)/admin/usuarios` | `contas` | USR |
| 6 · Administração › Assinatura | [desktop](html/Admin-Assinatura-Desktop.dc.html) · [celular](html/Admin-Assinatura-Mobile.dc.html) | `(empresa)/admin/assinatura` | `plataforma` | PLT |
| 7 · Início do financeiro | [desktop](html/Financeiro-Desktop.dc.html) · [celular](html/Financeiro-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| 8 · Início do gerente | [desktop](html/Gerente-Desktop.dc.html) · [celular](html/Gerente-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |

## Operação essencial

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Caixa do dia | [desktop](html/Caixa-Desktop.dc.html) · [celular](html/Caixa-Mobile.dc.html) | `(empresa)/financeiro` | `financeiro` | FIN |
| Despesas | [desktop](html/Despesas-Desktop.dc.html) · [celular](html/Despesas-Mobile.dc.html) | `(empresa)/financeiro` | `financeiro` | FIN |
| Devolução | [desktop](html/Devolucao-Desktop.dc.html) · [celular](html/Devolucao-Mobile.dc.html) | `(empresa)/locacoes/[id]/vistoria|devolucao` | `vistorias` | VIS, DEV |
| Detalhe da locação | [desktop](html/Locacao-Detalhe-Desktop.dc.html) · [celular](html/Locacao-Detalhe-Mobile.dc.html) | `(empresa)/locacoes` | `locacoes` | LOC |
| Locações | [desktop](html/Locacoes-Desktop.dc.html) · [celular](html/Locacoes-Mobile.dc.html) | `(empresa)/locacoes` | `locacoes` | LOC |
| Manutenções | [desktop](html/Manutencao-Desktop.dc.html) · [celular](html/Manutencao-Mobile.dc.html) | `(empresa)/manutencoes` | `manutencao` | MAN |
| Ficha do veículo | [desktop](html/Veiculo-Desktop.dc.html) · [celular](html/Veiculo-Mobile.dc.html) | `(empresa)/veiculos` | `veiculos` | VEI |
| Nova venda | [desktop](html/Venda-Desktop.dc.html) · [celular](html/Venda-Mobile.dc.html) | `(empresa)/vendas` | `vendas` | VEN, APR |
| Menu Mais | [celular](html/Menu-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| Vendas | [desktop](html/Vendas-Desktop.dc.html) · [celular](html/Vendas-Mobile.dc.html) | `(empresa)/vendas` | `vendas` | VEN, APR |

## Clientes

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Novo cliente | [desktop](html/Cliente-Desktop.dc.html) · [celular](html/Cliente-Mobile.dc.html) | `(empresa)/clientes` | `clientes` | CLI |
| Clientes | [desktop](html/Clientes-Desktop.dc.html) · [celular](html/Clientes-Mobile.dc.html) | `(empresa)/clientes` | `clientes` | CLI |

## Dashboard

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Dashboard | [celular](html/Dashboard-Mobile.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |
| Dashboard | [desktop](html/Main.dc.html) | `(empresa)/inicio` | `relatorios (agregados)` | USR, AUT |

## Filiais

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Nova filial | [desktop](html/Filial-Desktop.dc.html) · [celular](html/Filial-Mobile.dc.html) | `(empresa)/admin/filiais` | `filiais` | PLT, USR |
| Filiais | [desktop](html/Filiais-Desktop.dc.html) · [celular](html/Filiais-Mobile.dc.html) | `(empresa)/admin/filiais` | `filiais` | PLT, USR |

## Frota

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Frota | [desktop](html/Frota-Desktop.dc.html) · [celular](html/Frota-Mobile.dc.html) | `(empresa)/veiculos` | `veiculos` | VEI |

## Nova locação

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Nova locação | [desktop](html/Locacao-Desktop.dc.html) · [celular](html/Locacao-Mobile.dc.html) | `(empresa)/locacoes` | `locacoes` | LOC |

## Login

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Login | [desktop](html/Login-Desktop.dc.html) · [celular](html/Login-Mobile.dc.html) | `(publico)/entrar` | `contas` | USR |

## Painel da plataforma

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Auditoria de acessos | [desktop](html/Plat-Auditoria-Desktop.dc.html) · [celular](html/Plat-Auditoria-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Cobrança das assinaturas | [desktop](html/Plat-Cobranca-Desktop.dc.html) · [celular](html/Plat-Cobranca-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Detalhe da empresa | [desktop](html/Plat-Empresa-Detalhe-Desktop.dc.html) · [celular](html/Plat-Empresa-Detalhe-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Empresas | [desktop](html/Plat-Empresas-Desktop.dc.html) · [celular](html/Plat-Empresas-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Equipe interna | [desktop](html/Plat-Equipe-Desktop.dc.html) · [celular](html/Plat-Equipe-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Implantações | [desktop](html/Plat-Implantacoes-Desktop.dc.html) · [celular](html/Plat-Implantacoes-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Login da plataforma | [desktop](html/Plat-Login-Desktop.dc.html) · [celular](html/Plat-Login-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Planos e preços | [desktop](html/Plat-Planos-Desktop.dc.html) · [celular](html/Plat-Planos-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Entrar como suporte | [desktop](html/Plat-Suporte-Acesso-Desktop.dc.html) · [celular](html/Plat-Suporte-Acesso-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Suporte | [desktop](html/Plat-Suporte-Desktop.dc.html) · [celular](html/Plat-Suporte-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |
| Painel da plataforma | [desktop](html/Plataforma-Desktop.dc.html) · [celular](html/Plataforma-Mobile.dc.html) | `(plataforma)` | `plataforma` | PLT |

## Contas a receber

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Contas a receber | [desktop](html/Receber-Desktop.dc.html) · [celular](html/Receber-Mobile.dc.html) | `(empresa)/financeiro` | `financeiro` | FIN |

## Vistoria

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Vistoria de check-out | [desktop](html/Vistoria-Desktop.dc.html) · [celular](html/Vistoria-Mobile.dc.html) | `(empresa)/locacoes/[id]/vistoria|devolucao` | `vistorias` | VIS, DEV |

## Administração e relatórios

| Tela | Arquivos | Rota no frontend | App no backend | Regras |
| --- | --- | --- | --- | --- |
| Relatórios | [desktop](html/Relatorios-Desktop.dc.html) · [celular](html/Relatorios-Mobile.dc.html) | `(empresa)/relatorios` | `relatorios` | FIN, LOC, VEN |
| Configurações | [desktop](html/Config-Desktop.dc.html) · [celular](html/Config-Mobile.dc.html) | `(empresa)/admin` | `empresas, locacoes` | IMP, LOC |
| Empresa e marca | [desktop](html/Admin-Marca-Desktop.dc.html) · [celular](html/Admin-Marca-Mobile.dc.html) | `(empresa)/admin` | `empresas, locacoes` | IMP, LOC |
| Tabelas de preço | [desktop](html/Precos-Desktop.dc.html) · [celular](html/Precos-Mobile.dc.html) | `(empresa)/admin` | `empresas, locacoes` | IMP, LOC |
| Modelos de contrato | [desktop](html/Contratos-Modelos-Desktop.dc.html) · [celular](html/Contratos-Modelos-Mobile.dc.html) | `(empresa)/admin` | `empresas, locacoes` | IMP, LOC |
| Integrações | [desktop](html/Integracoes-Desktop.dc.html) · [celular](html/Integracoes-Mobile.dc.html) | `(empresa)/admin` | `empresas, locacoes` | IMP, LOC |
| Auditoria da empresa | [desktop](html/Admin-Auditoria-Desktop.dc.html) · [celular](html/Admin-Auditoria-Mobile.dc.html) | `(empresa)/admin/auditoria` | `auditoria` | AUD |
| Exportar dados | [desktop](html/Admin-Exportar-Desktop.dc.html) · [celular](html/Admin-Exportar-Mobile.dc.html) | `(empresa)/admin/auditoria` | `auditoria` | AUD |
| Cancelar assinatura | [desktop](html/Admin-Cancelar-Desktop.dc.html) · [celular](html/Admin-Cancelar-Mobile.dc.html) | `(empresa)/admin/assinatura` | `plataforma` | PLT |
| Comissões | [desktop](html/Comissoes-Desktop.dc.html) · [celular](html/Comissoes-Mobile.dc.html) | `(empresa)/financeiro` | `financeiro` | FIN |
| Conciliação | [desktop](html/Conciliacao-Desktop.dc.html) · [celular](html/Conciliacao-Mobile.dc.html) | `(empresa)/financeiro` | `financeiro` | FIN |
