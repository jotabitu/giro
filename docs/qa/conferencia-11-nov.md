# Conferência no navegador · 11 nov 2026 (T-437, T-446, T-447, T-450)

Pedido do Orquestrador. Conferido em 1440 e 390 px no giro-integracao (develop em b4f202c7, frontend reiniciado), `http://motorapida.localhost:3000`, uma sessão por perfil. Capturas em `tarefas/handoffs/anexos/conferencia-11-nov/`. Arquivos de teste: os da T-414 mais `moto-19.jpg` a `moto-21.jpg`, gerados por mim.

## Resumo

| Item | Resultado |
| --- | --- |
| 1 · T-437 (#507) | CA-437-01 a 05, 07, 09, 10 e 12 passam. Não exercitados: 06, 08, 11 e 13. |
| 2 · T-446 (#510) | Passa: visualizador de 1100 x 820 a 1440 e tela cheia a 390; miniatura de 64 px. |
| 3 · T-447 (#512) | Passa: contratos e preços abrem para a Mariana e ficam bloqueados para Rodrigo, Bruna, João e Lúcia. |
| 4 · T-450 (#517) | Passa no editar e no cadastro. |

Nenhuma divergência nova. Uma observação de aparência no fim.

## T-437 · fotos no cadastro (Veiculo-Novo)

| CA | Resultado | Como foi |
| --- | --- | --- |
| 437-01 | Passa | `moto-1.jpg`, `moto-2.jpg` e `moto.png` aparecem em lista com "3 de 20 fotos", a 1ª com "Capa"; nenhuma requisição de foto antes de "Salvar veículo". |
| 437-02 | Passa | "Tirar" na 2ª e "Usar como capa" em `moto.png`: ficam duas, `moto.png` com "Capa". |
| 437-03 | Passa | 21 arquivos: 20 na lista ("20 de 20 fotos") e o aviso "O veículo pode ter até 20 fotos." |
| 437-04 | Passa | `grande.jpg`, `moto.heic` e `documento.pdf` recusados na escolha, na hora, com "Envie uma foto JPG ou PNG de até 10 MB."; `moto-1.jpg` entra; nenhuma requisição saiu. |
| 437-05 | Passa | TBC-5H22 (a TBC-5H21 ficou para o 437-07): `POST /api/veiculos/` 201 e três `POST .../fotos/`; a tela mostrou "Enviando fotos · 1 de 3", "2 de 3" e "3 de 3" e abriu a ficha, com 3 fotos e a primeira é `moto.png` (capa), depois as duas `.jpg`. |
| 437-06 | Não exercitado | Cadastro sem fotos: cada cadastro cria um veículo que não dá para apagar; poupei. |
| 437-07 | Passa | Placa SAK-1D39: 409, mensagem "Já existe um veículo com esta placa", nenhum `POST .../fotos/` e as 2 fotos continuam na tela. Trocada para TBC-5H21 e salva: 201 e dois `POST .../fotos/` (veículo 92), sem escolher de novo. |
| 437-08 | Não exercitado | Precisa da empresa com 150 veículos. |
| 437-09 | Passa (simulado) | Com o servidor respondendo 400 na 2ª foto (interceptado no navegador), a tela mostra "Envie uma foto JPG ou PNG de até 10 MB." na linha de `moto-2.jpg` e "Ir para o veículo". |
| 437-10 | Passa (simulado) | Com a conexão derrubada na 2ª: "Enviando fotos · parou na 2 de 3", "Sem conexão. A foto não subiu." e "Tentar de novo", com a nota "envia só as que faltam, sem repetir as que já subiram". Tocando: abre a ficha com "3 de 20 fotos" (4 requisições: 1ª, 2ª que caiu, 2ª de novo, 3ª). |
| 437-11 | Não exercitado | Fechar a tela no meio. |
| 437-12 | Passa na tela | Rodrigo abre `Veiculo-Novo` com o bloco "Fotos do veículo". Bruna, João e Lúcia: "Seu perfil não tem acesso a esta página." O suporte Giro não foi testado. |
| 437-13 | Não verificado | A tela de Auditoria não mostrou os eventos `veiculo.foto_enviar` na lista aberta (sem filtro aplicado); não procurei pelo filtro. |

Criei 4 veículos de teste, que ficam no banco porque veículo não se apaga (nada de negócio é apagado): TBC-5H21 (id 92), TBC-5H22 (93), TBC-5H23 (94) e TBC-5H24 (95), cada um com 3 fotos (o 92 com 2) de teste. A frota passa de 87 para 91. Se o Orquestrador quiser o seed de volta, é o `make seed` na stack.

## T-446 · visualizador e miniatura

- **Visualizador, 1440 px:** diálogo de 1100 x 820 px, centrado, foto de 1052 x 789 px; setas do teclado, título "Galeria do veículo · QXA-4B21" e "Baixar (QXA-4B21-galeria-2.jpg)" funcionam. Sem rolagem lateral.
- **Visualizador, 390 px:** tela cheia, 390 x 844 px; foto de 342 x 486 px, setas laterais, três miniaturas de navegação e "Baixar" visíveis.
- **Miniatura no editar:** 64 x 64 px a 390 px (lista, uma linha por foto) e 251 x 140 px a 1440 (grade).

## T-447 · rotas de contratos e preços

- Mariana: `/admin/contratos` ("Modelos de contrato") e `/admin/precos` ("Tabelas de preço") abrem a 1440 e a 390 px.
- Rodrigo, Bruna, João e Lúcia: as duas rotas respondem "Seu perfil não tem acesso a esta página.".

## T-450 · foto acima de 10 MB

- **Editar do QXA-4B21:** `grande.jpg` (11 MB) recusada em 1,5 s com "grande.jpg: Envie uma foto JPG ou PNG de até 10 MB.", sem nenhum `POST` de foto (antes: 25 s e erro genérico).
- **Cadastro:** a mesma recusa na escolha, sem requisição (CA-437-04).

## Observação

- O título do visualizador a 390 px quebra a linha no hífen da placa ("QXA-" e "4B21" em linhas diferentes). Não impede nada; fica para a revisão do design-system.
