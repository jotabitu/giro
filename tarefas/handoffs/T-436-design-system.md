# T-436 (parte da tela) · Página pública do recibo da devolução · design-system → arquiteto, backend, frontend, qa

**O que foi feito:** desenhadas e entregues as telas de referência em `docs/telas/html/` (desktop a 1440 px e celular a 390 px) para a nova página pública do recibo da devolução (`/recibo#<token>`), aberta pelo cliente quando a locadora copia e envia o link (`POST /api/devolucoes/{id}/recibo/link/`, `docs/api/copiar-link.md`, `docs/api/vistorias.md`, regras `DEV-01` a `DEV-08`, `S-15`, `AUD-05`).

1. **Casca pública (modelo da página pública de assinatura de contrato `/assinar`):**
   - Cabeçalho com a marca da locadora em white label: logotipo (`wl-logo-slot`), nome "Moto Rápida", subdomínio `motorapida.girolocadoras.com.br` e cores `--brand: #0E7C66`, `--on-brand`, `--brand-soft`;
   - Sem menu lateral, sem navegação interna da empresa e sem necessidade de login;
   - Rodapé com "Tecnologia Giro · Termos de uso · Privacidade";
   - Segurança de token no fragmento (`#<token>`): a URL pública não expõe o token para logs de servidor nem cabeçalhos `Referer`, sendo lido em memória, removido da barra com `history.replaceState` e enviado via `POST /api/publico/recibos/consultar/`.

2. **Conteúdo completo do recibo da devolução (`Recibo-Desktop.dc.html` e `Recibo-Mobile.dc.html`):**
   - **Identificação do recibo e cliente:**
     - Título "Recibo da devolução" e código "LOC-2836" com badge de devolução concluída;
     - Data e horário da devolução: "14 de outubro de 2026, às 17:35";
     - Saudação personalizada com o primeiro nome: "Olá, Juliana. Aqui estão os dados da devolução concluída (...)";
     - Botão principal **Baixar recibo (PDF)** via URL assinada temporária (15 min, `AUD-05`) com nome de arquivo padronizado `recibo-devolucao-LOC-2836.pdf`.
   - **Bloco 1: Dados do veículo e da devolução:**
     - Veículo: Yamaha Factor 150 ED (placa `PNB-7C04`, cor Vermelha, ano 2023, categoria Street);
     - Filial de devolução: Filial Centro (Fortaleza, CE);
     - Período da locação: 30/09/2026 a 14/10/2026 (14 diárias);
     - Quilometragem: saída 18.402 km → retorno 19.630 km (rodou 1.228 km em plano com km livre);
     - Nível de combustível: saída com tanque cheio → retorno com 3/4 do tanque (faltou 1/4 = 4 L).
   - **Bloco 2: Valores e acerto da caução (`DEV-01`, `DEV-02`, `DEV-03`):**
     - Caução depositada na retirada: R$ 300,00;
     - Combustível faltante: − R$ 32,00 (4 L × R$ 5,50 + R$ 10,00 taxa de serviço da filial);
     - Avaria identificada na devolução: − R$ 85,00 (retrovisor esquerdo riscado conforme tabela/orçamento);
     - Atraso na devolução: R$ 0,00 (entregue no horário contratual);
     - Subtotal de retenções/descontos: − R$ 117,00;
     - **Saldo final da caução / Restituição:** destaque com badge de sucesso e valor **R$ 183,00**;
     - Informação de pagamento: *"Devolução de R$ 183,00 por Pix em até 1 dia útil na sua chave cadastrada"* (`DEV-02`).
   - **Bloco 3: Fotos da vistoria de devolução com funcionalidade de ampliar:**
     - Galeria com 6 fotos registradas na vistoria de chegada:
       1. Frente (vista frontal);
       2. Lado direito (carenagem e escapamento);
       3. Traseira (lanterna e placa PNB-7C04);
       4. Lado esquerdo (com indicação/badge de avaria nova apontada);
       5. Painel (odômetro 19.630 km e combustível em 3/4);
       6. Detalhe da avaria (retrovisor esquerdo riscado, valor R$ 85,00).
     - **Visualizador Lightbox modal integrado:**
       - Ao tocar/clicar em qualquer foto, abre o visualizador com scrim escuro semitransparente (`rgba(10,10,14,0.78)`);
       - Exibição ampliada da imagem;
       - Título, tipo de foto e legenda detalhada da conferência;
       - Controles de navegação "Foto anterior" e "Próxima foto" com suporte a teclas de seta e atalho `Esc`;
       - Botão "Baixar foto" com nome padronizado (`PNB-7C04-vistoria-foto-[n].jpg`);
       - Botão "Fechar (Esc)".

3. **Estados de erro contemplados (Link vencido e Link inválido):**
   - Ambas as telas (desktop e celular) trazem seletor de visualização interativo no topo para conferência imediata dos três estados da página pública:
     - **Link vencido (HTTP 410 `link_expirado`):** exibe mensagem *"Este link venceu após 7 dias da sua emissão por razões de segurança (S-15)"* e botão direto para falar com a locadora no WhatsApp;
     - **Link não encontrado / inválido (HTTP 404):** exibe *"Este link não tem o recibo ou não existe mais. Ele pode estar incompleto ou ter sido substituído por um link mais recente."* com orientação para solicitar reenvio.

4. **Índice de telas atualizado (`docs/telas/README.md`):**
   - Tabela de "Operação essencial" atualizada incluindo a tela `Recibo da devolução` (`Recibo-Desktop.dc.html` e `Recibo-Mobile.dc.html`), associada à rota `(publico)/recibo`, app `vistorias` e regras `DEV-01 a DEV-08, AUD-05, S-15`;
   - Registro de último ajuste datado em 05/11/2026 (T-436).

---

**Onde:**
- `docs/telas/html/Recibo-Desktop.dc.html` *(nova)*
- `docs/telas/html/Recibo-Mobile.dc.html` *(nova)*
- `docs/telas/README.md` *(índice e histórico atualizados)*
- `tarefas/feito.md` *(registro de entrega atualizado)*

---

**Regras cobertas:**
- `DEV-01` (Cobranças da devolução: combustível faltante com taxa de R$ 10,00, avarias e atraso)
- `DEV-02` (Saldo da caução, restituição por Pix em até 1 dia útil com texto específico no recibo)
- `DEV-03` (Exemplo canônico da LOC-2836 / Juliana: caução R$ 300,00, cobranças R$ 117,00, devolve R$ 183,00)
- `DEV-08` (Quilometragem e combustível de saída consistentes com a locação)
- `AUD-05` (URLs temporárias assinadas para visualização de fotos e download do PDF do recibo)
- `S-15` (Validade de 7 dias do link gerado e estados de erro 410/404)
- `copiar-link.md` e `vistorias.md` (Contrato do `POST /api/publico/recibos/consultar/` e comportamento da página `/recibo`)

---

**Componentes do design system necessários para o frontend:**
> *"A tela do repositório vale; se faltar componente, diga no handoff."*

Para a página pública `(publico)/recibo`:
1. Reutilizar a casca pública já existente: `PaginaAcesso` (ou layout equivalente sem navegação), `CabecalhoMarca` (white label com logo e nome da locadora) e `RodapeGiro` ("Tecnologia Giro · Termos de uso · Privacidade").
2. `ReciboDevolucaoPublico`: componente responsável por consultar a rota `POST /api/publico/recibos/consultar/`, renderizar os blocos de dados do veículo, acerto de caução, saldo Pix e a grade de fotos da vistoria.
3. `VisualizadorFotosPublico`: modal / lightbox simplificado para visualização ampliada das fotos da vistoria de chegada pelo cliente no navegador (desktop e celular), com controles anterior/próxima e botão de download.

---

**Próximo passo para quem recebe:**
- **Arquiteto / Backend:** garantir que `POST /api/publico/recibos/consultar/` devolva os dados do acerto (caução, cobranças detalhadas, combustível, avarias, saldo final), fotos da vistoria e a URL assinada do PDF.
- **Frontend:** implementar a rota `frontend/src/app/(publico)/recibo/page.tsx` consumindo o fragmento da URL, tratando os estados 200, 410 (link vencido) e 404 (link inexistente/inválido) conforme as telas de referência.
- **QA:** incluir a tela de recibo na rotina de conferência (`npm run conferencia`) e validar os fluxos desktop e mobile com as respostas de sucesso e erro.
