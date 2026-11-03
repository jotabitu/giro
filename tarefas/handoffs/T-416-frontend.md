# T-416 · Ver o comprovante da despesa paga (frontend) · frontend → orquestrador

**O que foi feito (na mesma branch e no mesmo PR #456 do backend):**
- `DetalheDaDespesa.tsx`: "Ver comprovante" na despesa que a API devolve com `comprovante` preenchido. Abre a URL assinada de 15 minutos em aba nova (`noopener noreferrer`), alvo de 44 px no celular. A nota continua como estava ("Ver a nota"). Sem `comprovante` (a pagar, paga sem ele, ou token de suporte, `AUD-09`) não há botão; a tela só lê o campo, não decide pelo perfil.
- CI do #456 (typecheck em `falso-financeiro.ts` linha 132): o `schema.d.ts` local estava velho; rodei `npm run api:gerar` e o erro apareceu igual ao do CI. A despesa falsa agora traz `comprovante: null` por padrão, a despesa 804 (paga, boleto) traz um comprovante, e `pagarDespesa` do falso devolve o comprovante quando o arquivo é enviado.
- `ComprovanteDaDespesa.test.tsx` (arquivo próprio, para não esgotar o limite de 10 entradas por minuto do `Despesas.test.tsx`): botão com URL assinada e nota junto, ausência sem comprovante, suporte com `null` e a nota visível, e pagamento com comprovante. Suíte inteira (831), lint e typecheck passam.

**O que ficou de fora:** não conferi a 1440 e a 390 px no navegador. O `schema.d.ts` não vai para o git; quem baixar a branch precisa rodar `npm run api:gerar`.

**Próximo passo para quem recebe:** conferir o CI do #456 e seguir com o merge, se o dono liberar.
