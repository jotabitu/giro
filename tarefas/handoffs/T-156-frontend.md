# T-156 · Custo e rendimento do veículo fora da ficha do vendedor (frontend) · frontend → qa, orquestrador

**O que foi feito:**
- Os cartões "Rendeu no ano" e "Custo de manutenção" da ficha (`FichaVeiculo.tsx`, desktop e celular) já saíam só com `indicadores_financeiros` no corpo; a tela não olha o perfil. O que sobrava era espaço: a grade do desktop tem 4 colunas fixas e a do celular 2, então sem os cartões a fileira deixava lugar vazio. Agora, sem a chave, o desktop usa 2 colunas (Ocupação e Km atual) e o celular 1 (Ocupação).
- `KpiGrid` (design system) ganhou a prop opcional `colunas`; sem ela nada muda. É uma mudança pequena em componente do design-system, avisada aqui para a revisão dele.
- O falso da API (`testes/falsos/falso-frota.ts`) mandava `indicadores_financeiros: null` para o vendedor; agora a chave vem ausente, como o backend (T-156 backend, D-25).

**Conferido na API real:** `GET /api/veiculos/4/` como Bruna não tem a chave `indicadores_financeiros`. Lúcia (financeiro) exige 2 etapas e não conferi na tela.

**Testes:** `FichaVeiculo.test.tsx`: `t_156_vendedor_fileira_de_indicadores_sem_cartao_vazio_nem_lugar_reservado` (2 cartões no desktop, 1 no celular, sem texto de rendimento, custo ou traço) e `t_156_gerente_com_a_chave_mostra_os_quatro_cartoes_no_desktop_e_dois_no_celular`. `tsc`, `eslint` e os testes de frota e dos falsos passam.

**O que ficou de fora:** conferência visual em 1440px e 390px com a Bruna e a Lúcia no navegador (a pilha em execução serve outra cópia do código); o QA ou o design-system confere. A ficha idêntica à referência é a T-242.

**Próximo passo:** QA entra como Bruna e como Lúcia na ficha e confere a fileira nos dois tamanhos.
