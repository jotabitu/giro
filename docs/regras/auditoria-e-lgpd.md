# Auditoria, LGPD e exportação

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Toda ação que muda dado de negócio grava um evento de auditoria que ninguém consegue editar ou apagar, nem o dono do produto. Telas: `Admin-Auditoria` (da empresa), `Plat-Auditoria` (da plataforma), `Admin-Exportar`, `Admin-Cancelar`.

- `AUD-01` O evento guarda: quem (usuário ou "Sistema" ou "Suporte Giro"), quando, ação, objeto (tipo e código), valores antes e depois dos campos mudados, IP e aparelho.
- `AUD-02` Categorias para filtro: financeiro, operação, configurações, segurança, suporte. Guardado por 5 anos.
- `AUD-03` Entradas do suporte da plataforma aparecem na auditoria da empresa com destaque e com o motivo (`PLT-07`).
- `AUD-04` Dados pessoais de clientes (CPF, CNH, endereço, fotos de documento) só aparecem completos para quem tem permissão de cadastro; nas listas, o CPF aparece mascarado (`***.218.330-**`).
- `AUD-05` Fotos de documentos e vistorias ficam em armazenamento privado, com link temporário (15 minutos) a cada visualização.
- `AUD-06` Pedido do titular (LGPD): o administrador exporta os dados de um cliente ou anonimiza o cadastro. Contratos e registros financeiros ficam guardados pelo prazo legal, anonimizados.
- `AUD-07` Exportação (`Admin-Exportar`): escolhe o que (clientes, veículos, locações e contratos, financeiro, vistorias e fotos, auditoria), formato (planilha, CSV, backup completo em ZIP) e período. O arquivo fica pronto em segundo plano e o link vale 7 dias.
- `AUD-08` Após o cancelamento da assinatura, os dados ficam guardados por 90 dias a partir do dia em que a empresa vira `cancelada` e são apagados de vez no 90º dia, com aviso por e-mail ao administrador 7 dias antes (`PLT-06`). No MVP, nesses 90 dias, os dados são pedidos à equipe Giro (a empresa `cancelada` não entra no sistema). A tarefa que apaga tem de existir antes do 90º dia do primeiro cancelamento real.
  - **O que fica depois do apagamento**, só no painel da plataforma, igual para toda empresa (MEI, empresário individual ou não):
    - a linha da empresa, `cancelada` e marcada como apagada, só com o CNPJ, sem razão social, nome de exibição, endereço e dados de contato (nome, e-mail e telefone do responsável e o e-mail de cobrança). Ficam também o plano, as datas e a cidade e o UF, que não identificam mais que o CNPJ. O painel mostra "Dados apagados" com o CNPJ;
    - as faturas da assinatura (`PLT-14`), cada uma com o tomador como foi na nota, registro de cobrança e fiscal do próprio Giro. O tomador sai com a fatura, no prazo de guarda (Pontos em aberto). A fatura ainda devida (`atrasada`, `PLT-06`) guarda também o e-mail de cobrança, para a equipe Giro continuar cobrando à mão, até ser paga ou acabar o prazo de guarda;
    - a auditoria da plataforma (`AUD-02`, 5 anos), que guarda quais dados da empresa mudaram, sem o valor: razão social, endereço e contato aparecem como "alterado". O valor completo fica só na auditoria da empresa, que sai com ela.

    Quando a última fatura sai pelo prazo de guarda, o CNPJ também sai da linha, e ficam reservados só o subdomínio e o schema, para nenhuma outra locadora usar o endereço antigo. Todo o resto da empresa sai no 90º dia: o schema, os arquivos, os usuários, os clientes. No parceiro de pagamento, o cadastro da empresa como pagadora perde o e-mail e o telefone. Quem volta a comprar depois do apagamento segue a `PLT-16`.
- `AUD-09` O suporte Giro, dentro de uma empresa (`PLT-07`), vê CPF e CNH sempre mascarados, como nas listas (`AUD-04`), em qualquer tela e com qualquer permissão de acesso ("só ver" ou "ver e editar"). Nunca vê os dados completos.

- **Exportação no MVP (`AUD-07`):** no MVP, a tela `Admin-Exportar` exporta só a auditoria, em CSV, por período, com o link de 7 dias; os outros itens, formatos e o cartão do backup automático não aparecem (nem desabilitados). Vão para a fase 2: clientes, veículos, locações e contratos, financeiro, vistorias e fotos; a planilha; o backup completo em ZIP; o backup mensal (`AUT-11`); a exportação da plataforma; a `AUD-06` e a `AUD-08`. Antes, a regra não dizia o que do `AUD-07` era MVP. O que fica de fora segue o quadro (fase 2) e os critérios de pronto do MVP, que pedem só a auditoria ativa.
- **Pedido do titular até a fase 2 (`AUD-06`):** sem a exportação de um cliente e a anonimização no sistema, o pedido do titular é atendido à mão: o administrador da locadora pede à equipe Giro, que gera os dados ou anonimiza o cadastro. Vale até a `AUD-06` existir.
- **CPF e CNH no evento (`AUD-04`, `AUD-09`):** a máscara de CPF e CNH é das telas, listas e exportações de cadastro. No evento de auditoria, CPF e CNH ficam omitidos ("alterado", sem nenhum dígito), porque o evento é guardado por 5 anos e a anonimização da `AUD-06` não o alcança. É o que o código da T-018 faz; ADR 0014, nota de 12 out 2026.
