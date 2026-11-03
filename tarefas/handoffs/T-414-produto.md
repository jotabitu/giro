# T-414 · Fotos do veículo: galeria própria e fotos da vistoria para ver e baixar · produto → arquiteto, design-system, backend, frontend, qa

**O que foi feito:** a decisão do dono de 29 out 2026 virou a `VEI-10`, com nota de mudança, caso no seed e critérios.

1. **Galeria do veículo:** até 20 fotos; JPG ou PNG até 10 MB, reprocessada e sem localização (o mesmo da vistoria); recusa por foto, as outras do envio seguem. Capa: a primeira enviada, trocável por "Usar como capa"; apagada a capa, a mais antiga vira capa. Trocar mantém a posição e a capa.
2. **Quem mexe:** administrador e gerente, no editar, em qualquer estado menos `vendido` e `baixado`. Suporte Giro só vê (403 `PLT-07`). Apagar inativa o arquivo e gera evento de auditoria; todas as ações têm evento, sem a imagem.
3. **Ficha:** galeria para todos os perfis; fotos da última vistoria concluída (todas, com as de avaria) para quem faz vistoria (o financeiro não recebe, como o bloco `vistoria_recente` hoje). Visualizador com ampliar, anterior e próxima dentro da mesma origem, e "Baixar" com nome "QXA-4B21-galeria-1.jpg" ou "QXA-4B21-vistoria-saida-frente.jpg", pelo link de 15 minutos (`AUD-05`).
4. **Origens separadas:** vistoria nunca entra na galeria nem no catálogo; galeria não vale como vistoria.
5. **Seed:** QXA-4B21 com 3 fotos (frente é a capa); os outros sem galeria.

**Código:** `VEI-10`, porque a `VEI-09` ficou com a T-421 (PR #459), aberta antes.

**Onde:** `docs/regras-de-negocio.md` (Veículos, Dados de referência, "Decisões de 29 e 30 out 2026"); `docs/qa/criterios/T-414.md` (CA-414-01 a 14).

**Leituras do produto (não vieram do dono):** limite de 20, o arquivo igual ao da vistoria, regra da capa, galeria travada em vendido e baixado, nome do arquivo baixado, galeria visível a todos. Sem ponto em aberto.

**Próximo passo:**
- **Arquiteto:** modelo `FotoVeiculo` (ordem, capa, ativo), rotas de enviar, trocar, apagar, capa e lista, URL assinada para ver e para baixar (com `Content-Disposition` e o nome), o bloco da vistoria com todas as fotos ou o link para `GET /api/vistorias/{id}/`.
- **Design-system:** tela de referência da galeria no editar e do visualizador na ficha, desktop e celular.
- **Backend:** modelo, migração, seed das 3 fotos, testes `test_vei_10_...`.
- **Frontend:** galeria, visualizador e baixar, a 1440 e a 390.
- **T-418 (catálogo):** usa a capa e a ordem da galeria.
