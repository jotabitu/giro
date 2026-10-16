# T-187 · Assinatura completa (tela) · frontend → orquestrador, qa (T-204), segurança, design-system

**O que foi feito:** a `/admin/assinatura` da T-170 ganhou, tudo pelo que a API manda (`acoes` e blocos de `GET /api/assinatura/`; nada calculado na tela):
- **Plano:** "a partir de 22 out" pela `proxima_fatura`; "Muda para Essencial em 22 nov, a R$ 199,00." com `plano_proximo`; botões Mudar de plano, Desfazer mudança e Escolher forma de pagamento por `acoes`.
- **Mudar de plano e Comparar planos** (`PlanosDaAssinatura`): a mesma lista de `GET /planos/`; cartão por plano com limites e itens; o que não cabe vem de `excede` ("86 de 30 veículos", "5 de 3 usuários", "Resolva antes: ...") e o botão fica parado; escolher simula (`mudanca-plano/simular/`), mostra a mensagem, a data e a diferença, e confirma com `confirmar_valor_centavos`; `valor_mudou` leva a "Ver o novo valor"; 422 `PLT-04` aparece como a API escreveu. Sem `acoes.mudar_plano` vira só comparação.
- **Forma de pagamento** (`PUT forma-pagamento/`): situação da API, três opções, Em uso; Pix automático abre o QR (desenhado do copia e cola) com a validade; cartão abre o aviso e leva à página do parceiro (`window.location.assign`); boleto só salva. Nenhum dado de cartão passa pela tela (ADR 0023).
- **Faturas:** tabela no desktop e lista no celular, com a linha do teste; Pagar por `acoes.pagar` (pela forma cadastrada ou por Pix, boleto ou cartão sem trocar a forma), com a cobrança (QR, copia e cola, linha digitável, abrir boleto, página do cartão); Recibo por `acoes.recibo` abre o `recibo_url`.
- **Dados fiscais:** razão social, CNPJ, e-mail de cobrança e endereço; Editar por `acoes.editar_dados_fiscais` com CEP que preenche rua, bairro e cidade; CNPJ somente leitura; erros da API por campo.
- **Cartão da oferta** ("Precisa de mais veículos ou filiais?", itens da API, Comparar planos).
**Onde:** frontend/src/components/admin/{AssinaturaDaEmpresa,PlanosDaAssinatura,FormaDePagamentoDaAssinatura,FaturasDaAssinatura,DadosFiscaisDaAssinatura,ComunsDaAssinatura}.tsx, lib/api/{assinatura,tipos-assinatura}.ts, lib/assinatura.ts, falso-assinatura.ts. Testes: Assinatura.test.tsx e AssinaturaAcoes.test.tsx (30).
**Contrato:** `docs/api/assinatura.md` (T-185 partes 1 e 2).
**Regras cobertas:** PLT-01, PLT-04, PLT-05, PLT-11, PLT-13, PLT-14, PLT-15 (CA-ASS-01, 02, 11 a 13, 15, 18 a 21, 26 a 29, 48 na parte de tela).
**O que ficou de fora:**
- Cancelar e pausar (T-195): o botão Cancelar assinatura segue parado com o aviso; `acoes` ainda não traz `cancelar` nem o bloco `cancelamento`.
- A volta do cartão: o contrato não traz URL de retorno; a tela abre a página do parceiro na mesma aba e relê a assinatura ao voltar (foco da janela). Se o parceiro precisar de uma URL de retorno, é pedido ao backend.
- Pix automático autorizado: a API ainda não escuta o aviso (T-186), então a situação fica "Autorize o Pix automático" até lá.
- Nota fiscal (`nota_fiscal` e `acoes.nota_fiscal`): a tela não mostra, porque a emissão está desligada até a T-197.
- Sem teste de clique (marcação estática); a simulação, a confirmação, o Pix, o pagar e os dados fiscais são testados pelo falso e pelo cliente HTTP.
- A referência `Admin-Assinatura-Mobile` não tem dados fiscais nem a oferta; no celular entram empilhados depois das faturas. Pedido ao design-system se quiserem desenhar.
- `veiculos.test.ts` linha 30 ainda falha no typecheck estrito nesta base (correção no PR #284).
**Próximo passo para quem recebe:** orquestrador abre o PR depois do #294; qa confere no navegador os CA-ASS acima com a API real.
