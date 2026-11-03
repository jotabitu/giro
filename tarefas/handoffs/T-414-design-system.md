# T-414 (parte da tela) · Fotos do veículo: galeria própria e visualizador · design-system → arquiteto, backend, frontend, qa

**O que foi feito:** desenhadas e entregues as telas de referência em `docs/telas/html/` (desktop a 1440 px e celular a 390 px) para a nova regra `VEI-10` (fotos do veículo) e critérios CA-414-01 a CA-414-14 (PR #465 do Produto), cobrindo a galeria no editar e a ficha com visualizador e download.

1. **Galeria do veículo no editar (`Veiculo-Editar-Desktop.dc.html` e `Veiculo-Editar-Mobile.dc.html`):**
   - Rota `/veiculos/[id]/editar` com seção dedicada **Galeria de fotos** do veículo QXA-4B21 (Honda CG 160 Fan, 2023, vermelha, Filial Centro).
   - Contador de fotos com limite de 20 (`3 de 20 fotos`) e nota de limite atingido (CA-414-03).
   - Área de envio (dropzone e botão) aceitando JPG e PNG de até 10 MB, com nota de reprocessamento e remoção automática de dados de localização GPS (CA-414-04).
   - Exemplo visual de mensagem de recusa de arquivo (CA-414-02: *"Envie uma foto JPG ou PNG de até 10 MB."*).
   - Cartões das fotos existentes com:
     - Foto 1 (Frente): marcada com badge `Capa` (`wl-badge--solid`), ações de [Trocar] e [Apagar].
     - Foto 2 (Traseira) e Foto 3 (Painel): ações de [Usar como capa], [Trocar] e [Apagar].
   - Nota explicativa das regras (CA-414-05, CA-414-06, CA-414-07): a primeira enviada vira capa; trocar mantém a posição e o status de capa; apagar a capa faz a foto mais antiga seguinte virar capa; fotos apagadas são inativadas e geram evento de auditoria sem a imagem.
   - Permissões (CA-414-08, CA-414-09): gerenciamento restrito a Administrador e Gerente; em veículos vendidos ou baixados, a galeria permanece somente para consulta.

2. **Ficha do veículo com origens separadas (`Veiculo-Desktop.dc.html` e `Veiculo-Mobile.dc.html`):**
   - Atualizada para separar com clareza as duas origens que nunca se misturam (CA-414-14):
     - **Galeria de fotos:** fotos de cadastro para catálogo e anúncio (capa primeiro), visível a todos os perfis (administrador, gerente, vendedor, vistoriador e financeiro). Botão/link "Gerenciar fotos" para quem tem permissão de editar. Sem fotos, exibe *"Nenhuma foto do veículo."* e link *"Adicionar fotos"* para quem edita (CA-414-13).
     - **Fotos da última vistoria:** bloco *"Vistoria de saída · LOC-2841 · 23 set · João Silva"* com as 12 fotos da vistoria e indicadores de avarias. Visível a quem faz vistoria (administrador, gerente, vendedor, vistoriador); o financeiro não recebe esta seção.
   - Botão "Editar" do cabeçalho da ficha direcionando para `Veiculo-Editar-Desktop.dc.html` / `Veiculo-Editar-Mobile.dc.html`.
   - Fotos clicáveis que abrem o visualizador ampliado.

3. **Visualizador de fotos (`Veiculo-Visualizador-Desktop.dc.html` e `Veiculo-Visualizador-Mobile.dc.html`):**
   - Tela de referência com o modal lightbox aberto em destaque sobre a ficha:
     - Barra superior com identificação da foto e origem (ex: *"Foto 1 de 3 · Frente"*, badge *"Galeria do veículo"*, badge *"Capa"*).
     - Botão **Baixar** com nome de arquivo padronizado conforme a origem (CA-414-12):
       - Galeria: `QXA-4B21-galeria-1.jpg`.
       - Vistoria: `QXA-4B21-vistoria-saida-frente.jpg`.
     - Indicação de link temporário assinado válido por 15 minutos (`AUD-05`).
     - Botão Fechar ("X") retornando à ficha.
     - Palco central com imagem ampliada e controles de navegação **Anterior** e **Próxima**.
     - Navegação estritamente dentro da mesma origem: ao folhear a galeria, não pula para fotos da vistoria; ao folhear a vistoria, não entra na galeria (CA-414-10, CA-414-14).
     - Barra inferior com miniaturas da mesma origem e foto ativa destacada.

4. **Índice de telas atualizado (`docs/telas/README.md`):**
   - Tabela do módulo "Frota" atualizada com as novas telas de `Editar veículo` e `Visualizador de fotos`, citação das regras `VEI-01`, `VEI-10`, `VIS-01` e `AUD-05`, e registro do ajuste de 03/11/2026.

---

**Onde:**
- `docs/telas/html/Veiculo-Editar-Desktop.dc.html` *(nova)*
- `docs/telas/html/Veiculo-Editar-Mobile.dc.html` *(nova)*
- `docs/telas/html/Veiculo-Visualizador-Desktop.dc.html` *(nova)*
- `docs/telas/html/Veiculo-Visualizador-Mobile.dc.html` *(nova)*
- `docs/telas/html/Veiculo-Desktop.dc.html` *(ajustada)*
- `docs/telas/html/Veiculo-Mobile.dc.html` *(ajustada)*
- `docs/telas/README.md` *(índice atualizado)*

---

**Regras cobertas:**
- `VEI-10` (Galeria do veículo e fotos da vistoria na ficha)
- `VIS-01` (Fotos da vistoria e avarias)
- `AUD-05` (Links temporários assinados com validade de 15 minutos)
- Critérios CA-414-01 a CA-414-14 integralmente considerados no desenho e na experiência de uso.

---

**Componentes do design system necessários para o frontend:**
> *"A tela do repositório vale; se faltar componente, diga no handoff."*

Os componentes existentes em `frontend/src/design-system/components/` (`Panel`, `Button`, `StatusBadge`, `Dialogo`, etc.) cobrem a estrutura base, mas o frontend precisará compor ou introduzir dois padrões novos inspirados nas telas de referência:
1. `GaleriaVeiculoForm`: componente para a página de edição contendo dropzone com suporte a drag & drop, limites de arquivo (JPG/PNG até 10 MB, máx 20 fotos), badges de capa e botões de contexto ("Usar como capa", "Trocar", "Apagar").
2. `VisualizadorDeFotos` / `Lightbox`: componente de visualização modal com imagem ampliada, controles de próximo/anterior restritos à origem ativa, carrossel inferior de miniaturas e gatilho de download assinado com o atributo `download="<nome-padrao>"` (`QXA-4B21-galeria-1.jpg` ou `QXA-4B21-vistoria-saida-frente.jpg`).

---

**Próximo passo para quem recebe:**
- **Arquiteto:** confirmar os contratos e endpoints de fotos do veículo (upload, ordenação, capa, troca, exclusão e URL assinada temporária para download com `Content-Disposition`).
- **Backend:** criar modelo `FotoVeiculo`, migrations, serviços de expurgo de metadados GPS e endpoints correspondentes com testes `test_vei_10_*`.
- **Frontend:** implementar a interface da galeria no `/veiculos/[id]/editar` e os blocos separados com o modal visualizador na ficha `/veiculos/[id]`, em 1440 e 390 px.
- **QA:** validar os critérios CA-414-01 a 14 na homologação e testes de conferência visual.
