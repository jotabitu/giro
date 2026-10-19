# T-332 · ADR 0026: o pypdf tenta a senha vazia · arquiteto → orquestrador

**O que foi feito:** no item 6 da ADR 0026 (tabela de limites), a linha do PDF com senha passou de "falha, sem tentar senha vazia" para "falha (`is_encrypted`); o `pypdf` tenta a senha vazia ao abrir, e o trabalhador recusa antes de ler o texto". O status da ADR cita o B-04 da revisão da T-328.
**Onde:** `docs/decisoes/0026-leitura-de-documentos-em-pdf.md`, `tarefas/feito.md`.
**Origem:** B-04 de `docs/seguranca/2026-10-19-t328-leitura-crlv.md` (branch `t-328-revisao-crlv`, PR #355).
**Regras cobertas:** nenhuma regra muda; só o texto da ADR passa a descrever o que o código já faz.
**O que ficou de fora:** a decisão de ler PDF cifrado só com a senha do dono. Se a calibração com CRLV-e reais mostrar documentos assim, a leitura falha sempre, e aceitar esses PDFs pede revisão da ADR (sugestão do B-04 para o produto e o orquestrador).
**Próximo passo para quem recebe:** orquestrador junta esta branch (sem PR próprio, como pedido) e tira a T-332 do backlog na branch da T-328.
