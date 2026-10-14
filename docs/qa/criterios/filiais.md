# Filial: nome curto e preço do litro (decisões da T-190) · critérios de aceite

**Regras:** FIL-01, DEV-01, PLT-03 · **Contrato:** `docs/api/filiais.md` (`nome_curto` a acrescentar pelo arquiteto; `preco_litro_centavos` já existe) · **Telas:** Filiais, Filial, seletor de filial, Admin-Usuarios, Config (desktop e celular) · **Decisão:** dono do produto, 14 out 2026 (T-190, D11 e C-1)

As tarefas de código ainda não têm número (propostas em `tarefas/backlog.md`, seção da T-190). Seed Moto Rápida em 07 out 2026: Filial Centro, preço do litro R$ 5,50. O nome do teste leva o código da regra (`test_fil_01_...`, `test_dev_01_...`).

**CA-FIL-01 · Nome curto no seletor e nas listas curtas**
Dado a Filial Centro com nome curto "Centro", então o seletor de filial mostra "Centro", a lista de filiais da pessoa em `Admin-Usuarios` mostra "Centro", e o resumo de Configurações diz "1 filial · Centro, Fortaleza". A tela `Filial` e as outras telas mostram "Filial Centro". O frontend não corta texto do nome.

**CA-FIL-02 · Sem nome curto vale o nome**
Dado uma filial nova "Filial Messejana" sem nome curto, então o seletor mostra "Filial Messejana".

**CA-FIL-03 · Preço do litro pelo administrador**
Dado a Mariana (administradora) na tela `Filial` da Filial Centro, quando muda o preço do litro, no bloco Operação, de R$ 5,50 para R$ 5,90, então o valor é gravado com evento de auditoria (antes e depois), e o próximo acerto de combustível usa R$ 5,90. O Rodrigo (gerente) não vê o campo, e o pedido direto à API é recusado (403).

**CA-FIL-04 · Acerto com o preço do seed**
Dado o preço do litro R$ 5,50, então a Factor 150 (tanque de 16 L) que sai cheia e volta com 3/4 cobra R$ 32,00 de combustível (4 L × R$ 5,50 + R$ 10,00), como no caso "Acerto da devolução LOC-2836".

**CA-FIL-05 · Sem preço do litro**
Dado uma filial sem preço do litro, quando a devolução tem combustível faltando, então o acerto pede o valor do combustível à mão.

**CA-FIL-06 · Limite de filiais diz "mude de plano"**
Dado uma empresa no Profissional com 3 de 3 filiais, quando o administrador abre "Nova filial", então a tela diz para mudar de plano, sem falar em filial adicional (`PLT-03`).
