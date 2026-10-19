# T-330 · Referência do celular do cadastro do veículo com "Enviar CRLV-e" · design-system → frontend, orquestrador

**O que foi feito:** em `Veiculo-Novo-Mobile.dc.html`, o botão "Fotografar o CRLV para preencher" virou "Enviar CRLV-e para preencher", o ícone de câmera virou o de documento e o texto de apoio passou de "Lido agora" para "CRLV-e lido · 9 campos preenchidos". O contrato só lê PDF (ADR 0026), então a tela de referência não promete mais foto. A tela real já faz assim (T-265).
**Onde:** docs/telas/html/Veiculo-Novo-Mobile.dc.html (linha 36).
**Regras cobertas:** VEI-08 (sem teste novo: só HTML de referência).
**O que ficou de fora:** nada. Outras telas de referência não citam "Fotografar".
**Próximo passo para quem recebe:** nenhum. Sem PR, a pedido do orquestrador; a branch `t-330-crlv-mobile` segue a `origin/main`.
