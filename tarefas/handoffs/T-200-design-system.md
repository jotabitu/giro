# T-188 e T-200 · Telas de referência pelas decisões do dono de 14 out · design-system → orquestrador, frontend, qa

**O que foi feito:** as telas de `docs/telas/html/` seguem as regras `PLT-01`, `PLT-11`, `FIL-01`, `FIL-04`, `USR-03`, `USR-04`, `APR-12` e o `docs/api/assinatura.md`. Só HTML de referência; nenhum código de `frontend/` mudou.

**Onde (22 arquivos):**
- `Compra-Planos-*`, `Plat-Planos-*`: catálogo da `PLT-11`. Sem NF-e, domínio próprio, portal do cliente nem API. Contrato digital em todos os planos (a `PLT-11` o tira de extra; o texto do backlog dizia "extra" e a regra prevaleceu). Essencial com "Contrato digital, assinado pelo cliente no celular"; Completo com "Tudo do Profissional", sem limites, implantação por chamada e suporte prioritário. `Plat-Planos-Desktop` sem o bloco Adicionais (`PLT-03`); regra "Mudança de plano" diz upgrade proporcional e downgrade na próxima fatura. Rodapé da `Compra-Planos-Desktop` sem "dados exportados a qualquer momento".
- `Admin-Assinatura-*`: "a partir de 22 out"; fatura FAT-0001 vence 22 out com "Plano Profissional · 22 out a 21 nov" e situação "Sem forma de pagamento" (celular também); cartão "Precisa de mais veículos ou filiais?" com os 3 itens da API; sai "Você pode exportar todos os seus dados".
- `Admin-Cancelar-*`: sem "Pausar" (empresa em teste, `PLT-06`); "Exportar dados antes" ganha a frase de que baixa a auditoria em CSV e o resto se pede à equipe Giro (CA-ASS-38). `Admin-Exportar-Desktop` com a mesma frase.
- `Compra-Checkout-*`: sem número, validade e CVV (ADR 0023); fica a escolha Cartão, Pix ou Boleto e o aviso de que o cartão é digitado na página do parceiro. 1ª mensalidade em 22 out; lembrete em 19 out (D-3 da `PLT-02`, por e-mail).
- `Filial-*`: preço do litro no bloco Operação (só o administrador altera; sem preço o acerto pede o valor à mão, CA-FIL-05); horário com 2º intervalo por dia; Telefone no celular; "O recebimento é da empresa; o preço pode ser da empresa ou da filial"; no limite, "mude de plano".
- `Admin-Usuarios-*`: rótulos neutros (Administrador, Vendedor, Ativo); "a pessoa"; "A pessoa sai do sistema na hora"; Redefinir 2 etapas e Encerrar sessões; Reativar (desativado) e Cancelar convite (pendente); no celular, gaveta de edição.
- `Admin-Auditoria-Mobile`: chip Suporte sem número (o desktop já estava).
- `Aprovacoes-*`: aba "Meus pedidos"; sai a frase das 4 horas úteis.
- `Config-*`: "Baixe a auditoria em CSV".
- `Onboarding-Importar-*`: "Corrigir aqui" em cada linha com erro, dentro da lista.

**Regras cobertas:** PLT-01, PLT-03, PLT-06, PLT-11, FIL-01, FIL-04, USR-03, USR-04, APR-08, APR-12, AUD-07. Checagem feita: tags balanceadas nos 22 arquivos; sem renderização no navegador.

**O que ficou de fora:**
- "Passo 7 de 8" (assistente) e "6 de 10 passos" (Configurações): nenhuma tela mostra os dois juntos; nada mudou.
- `Aprovacoes-*`: o conteúdo da aba "Meus pedidos" e os números da `APR-12` seguem os do desenho atual; a lista de "Meus pedidos" não foi desenhada (só a aba), à espera do `resumo` da T-201.
- `Admin-Assinatura-Mobile` não ganhou o cartão "Precisa de mais veículos ou filiais?" (não tinha cartão de plano antes).
- Fora do escopo, mas contra a `PLT-11` (função que não existe não aparece em texto): `Admin-Marca-*` ("Domínio próprio … no plano Completo") e `Integracoes-*` (cartões "Nota fiscal (NF-e / NFS-e)" no Completo e "Assinatura digital" como item do plano). Decisão do produto antes de mexer.

**Próximo passo para quem recebe:** orquestrador abre o PR e segue com a T-214 (`Onboarding-Filial` e desfazer cancelamento, PR #206). Frontend das T-187 e T-198 pode usar as telas como estão.

## Ajuste de 14 out (PLT-11, pedido do orquestrador)

- `Admin-Marca` (desktop e celular): saiu a dica "Domínio próprio (ex.: app.motorapida.com.br) no plano Completo"; o endereço pelo subdomínio fica.
- `Integracoes` (desktop e celular): saiu o cartão "Nota fiscal (NF-e / NFS-e)" (Plano Completo, "Conhecer"), sem "em breve".
