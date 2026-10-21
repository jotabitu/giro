# T-342 · Fonte provisória do catálogo (Parallelum) · arquiteto → orquestrador, backend

**O que foi feito:**
1. ADR curta nova, a **0031** (aceita, provisória). Não editei a 0026 porque o README das decisões pede ADR nova em vez de mexer na antiga, e a 0026 deixava a origem para outra tarefa. A ADR registra a fonte (API aberta da Parallelum, v2, sem token), que ela é provisória, o risco aceito pelo dono em 20 out 2026 (dados da Tabela FIPE sem licença, código MIT) e a troca para a FIPE licenciada se houver contrato. A 0030 continua proposta para esse caso. Na T-338 do backlog, a `[decisão]` está marcada como decidida pelo dono, com essa escolha.
2. O "Pronto quando" da T-339 foi reescrito para a Parallelum:
   - um script fora do servidor, só com a biblioteca padrão, a um pedido por segundo e parando no 429;
   - o comando, ainda sem internet, aceitando mais de um arquivo;
   - o CSV versionado com a fonte citada e atualizado a cada trimestre por PR;
   - a chave calculada uma vez;
   - os testes com nomes no formato dos 2 CRLV-e da T-331.
   **Sem dependência nova.**
3. O texto "Da lista FIPE" (`Veiculo-Novo` e `NovoVeiculoForm.tsx`) **continua certo**: os nomes são os da Tabela FIPE. Nenhuma tela muda.

**Conferido na API em 20 out 2026** (cerca de 220 pedidos, com um por segundo):
- tipos `cars`, `motorcycles` e `trucks` (`docs/VehiclesType.md` do fipe-go);
- 500 pedidos por dia sem token;
- 108 marcas de carro e 103 de moto, 9.424 modelos (7.386 carros, 2.038 motos), 404 KB;
- o "POP 110i ES" da Honda está lá.

**Achado que mudou a T-339:** os nomes do seed ("CG 160 Fan", "Factor 150", "Kwid", "Biz 125", "Mobi") não existem iguais na FIPE, que tem uma linha por versão ("CG 160 FAN Flex"). Trocar o CSV só pela lista da Parallelum quebraria o seed e os testes da T-257. Por isso a lista própria da equipe (os 29 de hoje) fica num arquivo próprio e é juntada na carga. O nome genérico também ajuda a leitura: "HONDA/CG 160 FAN" acha um modelo só. Outro detalhe: a API escreve "Honda" nos carros e "HONDA" nas motos, e a T-339 unifica a grafia da marca.

**Onde:** `docs/decisoes/0031-fonte-provisoria-do-catalogo-parallelum.md`, `docs/decisoes/README.md`, `tarefas/backlog.md` (T-338 e T-339).
**Regras cobertas:** `VEI-08` (nenhuma regra muda).
**O que ficou de fora:** o CSV baixado ficou só no meu scratchpad, para medir. Quem gera e versiona é o backend, na T-339.
**Próximo passo para quem recebe:** o orquestrador libera a T-339 para o backend; ela não espera mais a FIPE. Branch `t-342-fonte-parallelum`, sem PR.
