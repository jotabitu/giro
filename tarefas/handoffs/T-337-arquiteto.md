# T-337 · Catálogo completo de marcas e modelos · arquiteto → orquestrador, dono, backend

**O que foi feito:** levantei as fontes da lista completa de motos e carros para o catálogo da T-257 (ADR 0026, item 7) e medi cada uma. A escolha depende de licença e custo, então ficou como `[decisão]` do dono no backlog ("Levantada pelo arquiteto em T-337"), com as opções A, B e C. O contrato ganhou uma nota curta.
**Onde:** `tarefas/backlog.md` (seção Decisões), `docs/api/veiculos.md` (seção `GET /api/veiculos/modelos/`), este handoff.
**Regras cobertas:** `VEI-08` (nenhuma regra muda).

## As fontes (medidas em 19 out 2026)

| | A. FIPE pelo site | B. FIPE licenciada | C. Renavam (Senatran) |
| --- | --- | --- | --- |
| Onde | veiculos.fipe.org.br, rotas internas do site (`ConsultarMarcas`, `ConsultarModelos`) | contrato com a FIPE ou API paga de terceiro | dados.transportes.gov.br, conjunto "Registro Nacional de Veículos Automotores - RENAVAM" |
| Licença | não publicada; site sem API oficial; recusou a coleta com 429 | a do contrato | domínio público |
| Repositório público | risco do dono (só nomes, sem preço) | depende do contrato | pode |
| Custo | nenhum | mensal, a cotar | nenhum |
| Tipo moto ou carro | sim (tipo 1 carro, 2 moto) | sim | não tem |
| Tamanho | 108 marcas de carro, 103 de moto; Fiat tem 708 modelos e Honda moto 245; estimativa de 5 a 10 mil linhas, centenas de KB | igual à A | ZIP de 129 MB (TXT de 1,1 GB); 38.082 nomes distintos (776 KB), com caminhões, reboques e importados |
| Texto | "Honda / POP 110i ES", "Fiat / ARGO DRIVE 1.3 8V Flex" | igual à A | "HONDA/POP 110I ES", "FIAT/ARGO DRIVE 1.3", "VW/...", "I/..." |
| Atualização | tabela mensal | mensal | mensal (o último visto foi jun 2025) |

O Pop 110i ES, do CA-247-01, está nas três.

## Como o comando carrega e atualiza

- **A e B:** nada muda no código. A equipe gera o CSV `marca,modelo,tipo` (na A, devagar e fora do servidor; na B, pela entrega do fornecedor) e roda `python manage.py atualizar_catalogo_modelos <arquivo.csv>`. O comando já aceita `carros`/`motos`, tira duplicatas e ordena. O CSV regravado vai por PR. Frequência: **a cada trimestre** basta. Modelo novo que ainda não está na lista só faz a leitura mandar a dica (CA-247-05). Se o contrato da B proibir publicar a lista, o CSV sai do git e é baixado do armazenamento privado no deploy. Isso pede uma ADR.
- **C:** o comando passa a ler o TXT do Senatran (latin1, `;`, coluna `Marca Modelo`), separa marca e modelo pela `/`, tira o `I/`, troca as siglas por um de-para curto ("VW" vira Volkswagen, "GM" vira Chevrolet, "M.BENZ" vira Mercedes-Benz, "MMC" vira Mitsubishi) e corta pela quantidade mínima de veículos. O tipo continua faltando: alguém classifica à mão, e a Honda tem moto e carro. É a opção mais trabalhosa.

## O que muda no contrato

- A rota, o formato do CSV e o comando continuam iguais nas três opções.
- A tela busca pela rota (`tipo` e `busca`, até 50) e nunca carrega a lista inteira. Isso já está no contrato e agora está escrito.
- Na FIPE, o carro tem uma linha por versão. O CRLV-e de carro ("FIAT/ARGO DRIVE 1.3") costuma achar mais de um modelo ("ARGO DRIVE 1.3 8V Flex" e "... Flex Aut.") e vai para a dica. Motos acertam mais ("POP 110i ES"). Isso segue a ADR 0026 (achou mais de um, não preenche), e por isso não há mudança.
- Para o backend, junto com a carga: com milhares de linhas, `listar` e `achar_modelo` não devem normalizar `marca + modelo` a cada pedido (`Modelo.chave` é uma property). A chave deve ser calculada uma vez, na leitura do CSV.

## O que ficou de fora

O CSV completo não foi gerado. A coleta da A foi interrompida pelo 429 e espera a decisão. Os 2 modelos dos CRLV-e reais da T-331 não foram conferidos pelo nome (dado pessoal, fora do git). O qa confere depois da carga.

**Próximo passo para quem recebe:** orquestrador leva a `[decisão]` ao dono. Com a escolha feita, numera a tarefa do backend (carga, chave pré-calculada e teste com os modelos dos CRLV-e da T-331). Na C, o produto e o design trocam o texto "Da lista FIPE". Branch `t-337-catalogo-completo`, sem PR, como pedido.

Fontes: [conjunto RENAVAM no dados.transportes.gov.br](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907) (arquivo `i_frota_por_uf_municipio_marca_e_modelo_ano_junho_2025.zip`), [consulta FIPE](https://veiculos.fipe.org.br/).
