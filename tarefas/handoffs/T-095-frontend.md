# T-095 · Cadastrar veículo · frontend → orquestrador

**O que foi feito:**
- Frota (`/veiculos`): botão "Cadastrar veículo" para quem tem `pode.veiculos === "editar"` (botão com texto no desktop, ícone + no celular).
- `/veiculos/novo`: recria Veiculo-Novo (desktop e celular) com os componentes do design system. Envia `POST /api/veiculos/` (falso), mostra os erros 400 no campo, o 409 `VEI-01` na placa ou no chassi com link para o veículo existente e o 422 `PLT-03` como aviso. "Salvar" abre a ficha; "Salvar e cadastrar outro" limpa o formulário e mantém tipo e filial.
- Falso (`falso-frota.ts`): `criar` (placa e chassi únicos, chassi com 17 caracteres, anos, categoria da filial, limite do plano, 403 para quem não cadastra), `categorias`, `registrarKm` (km nunca diminui, 422 `VEI-01`). Preço da categoria vem da API, a tela não calcula.
**Onde:** `frontend/src/components/frota/NovoVeiculoForm.tsx`, `ListaVeiculos.tsx`, `src/app/(empresa)/veiculos/novo/`, `src/lib/veiculos.ts`, `src/lib/api/falso-frota.ts`, `tipos-frota.ts`.
**Regras cobertas:** VEI-01, VEI-02, PLT-03, LOC-15.
**Testes:** `falso-frota.test.ts`, `veiculos.test.ts`, `NovoVeiculo.test.tsx`.
**Check:** lint, tsc, vitest (158 passed) e `next build` limpos.
**O que ficou de fora (a tela de referência pede, o contrato não tem):**
- Leitura do CRLV-e e "Importar planilha": desativados.
- Consulta FIPE: campo desativado.
- Combustível, cilindrada, finalidade, plano de manutenção, origem, fornecedor, preparação, IPVA, seguro, rastreador, upload de documentos e fotos: não estão no `POST`; a tela manda enviar na ficha depois de salvar. Pergunta para produto/arquiteto se entram no contrato.
- Checklist "Antes de liberar para locação" e barra "Veículos no plano": exigem dado da API que o contrato não devolve; ficou só o texto de que o veículo entra Disponível.
- Ligar na API real fica para a tarefa que ligar a frota inteira.
**Próximo passo para quem recebe:** orquestrador, abrir o PR e mover a T-095 para `feito.md`.
