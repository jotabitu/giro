# T-428 · Correções da conferência da fase 2 · frontend → orquestrador

**O que foi feito** (D1 a D5 do `conferencia-fase2-qa.md`):
- **D1** `FaixaDaAssinatura.tsx`: a faixa vira coluna no celular, com texto em `text-caption`, `py-2` e o botão em largura cheia; o aviso "Fale com o administrador" fica embaixo, em uma linha. Do desktop (`md`) em diante continua tudo numa linha. Não medi a altura no navegador; a conta é duas a três linhas de texto mais o botão, longe dos 520 px.
- **D2 e D3** `FichaVeiculo.tsx`: a causa era um erro meu na T-413. Meu replace pôs o histórico duas vezes no desktop e nenhuma no celular. Agora há um por tamanho.
- **D4** `DocumentosDoVeiculo.tsx`: `min-w-0` na lista, na grade e nos filhos, arquivo com `w-full max-w-full` e botão em largura cheia no celular.
- **D5** `DetalheDaDespesa.tsx`: "Ver comprovante" e "Ver a nota" usam `wl-btn--quiet`. Antes, `wl-btn` puro tinha o mesmo fundo do cartão e parecia texto.
- Testes: um por defeito, em `FaixaDaAssinatura.test.tsx`, `DocumentosDoVeiculo.test.tsx` (D2, D3 e D4) e `ComprovanteDaDespesa.test.tsx`. Rodei só os arquivos afetados, mais ficha, reserva, lint e typecheck; passam.

**O que ficou de fora:** não reabri o navegador a 1440 e 390 px; o QA precisa repetir D1 (vendedora e administrador), D3 e D4 com as capturas. D6 é do produto. Os testes só olham as classes, não o tamanho renderizado.

**Próximo passo para quem recebe:** QA reconferir D1 a D5 depois do merge.
