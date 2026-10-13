# T-143 · Faixa "Data simulada" e o "hoje" das telas pela API · frontend → orquestrador, backend (T-142), qa

**O que foi feito:**
- **Faixa** (`FaixaDataSimulada`, `AmbienteDaTela` no layout raiz, então vale no login, no sistema da locadora e no painel da plataforma): com `data_simulada: true`, faixa fixa no topo (`sticky`, tom de aviso `warning-soft`/`warning-ink`), texto "Data simulada: 07/10/2026. Ambiente de desenvolvimento.", sem botão de fechar. Com `false` ou sem resposta, não renderiza nada.
- **Chamada** (`src/lib/api/ambiente.ts`): `GET /api/ambiente/` nas rotas da empresa e `GET /api/plataforma/ambiente/` nas rotas `/plataforma` (`escopoDaRota`). Pública, lida ao abrir e a cada 5 min. 404, falha de rede, erro de servidor ou corpo fora do contrato dão `null`: a tela segue sem faixa e sem erro.
- **"Hoje" das telas** (`src/lib/ambiente.ts`): `agoraDaTela()`/`useAgora()` devolvem o dia de `hoje` da API com a hora de Brasília do navegador (o mesmo desenho do `comum.relogio`). Troquei os `new Date()` de negócio por ele: `periodoDaLocacao` (lista de locações), `horarioDaAgenda` (agenda e início do vistoriador), `retiradaPadrao`/`valoresIniciais` e o "hoje" da nova locação (a retirada padrão acompanha a API se chegar depois do primeiro desenho e ninguém mexeu no campo), "hoje, 18:00" no histórico da locação e a data padrão do cancelamento. Sem resposta da API, vale o relógio do navegador.
- Não troquei `atualizadoHa` ("atualizado há 6 min"): compara `atualizado_em`, que é o relógio real (ADR 0021, item 3), com o agora real.

**Onde:** `frontend/src/lib/{ambiente,painel,locacoes,locacao-form}.ts`, `src/lib/api/{ambiente,tipos,index}.ts`, `src/components/casca/FaixaDataSimulada.tsx`, `src/app/layout.tsx`, `src/components/locacoes/{NovaLocacao,DetalheDaLocacao,AcoesDaLocacao,ListaLocacoes}.tsx`, `src/components/vistorias/AgendaDoVistoriador.tsx`, `src/components/inicio/InicioVistoriador.tsx`, fixture `src/testes/falsos/falso-ambiente.ts`.

**Contrato:** `docs/api/README.md`, seção "Ambiente" (ainda sem a rota no `openapi.yaml`; o tipo `Ambiente` em `tipos.ts` é temporário e sai quando a T-142 gerar o OpenAPI).

**Testes:** `FaixaDataSimulada.test.tsx` (3: ligada, desligada, sem resposta), `lib/ambiente.test.ts` (4: dia trocado com hora mantida, sem API = relógio do navegador, "hoje" da API em `periodoDaLocacao` e `horarioDaAgenda`, escopo da rota), `lib/api/ambiente.test.ts` (2: as duas rotas; 404, 500, corpo inválido e rede dão `null`). `typecheck`, `lint`, 297+ testes e `build` limpos.

**O que ficou de fora:** a faixa não foi vista no navegador nem contra o backend (T-142 não existe). Páginas com altura `100vh` podem ganhar uns 36 px de rolagem com a faixa ligada; conferir no compose quando a T-142 entrar.

**Próximo passo para quem recebe:** backend (T-142) entrega a rota nos dois urlconfs; depois qa confere no compose com `GIRO_DATA_REFERENCIA=2026-10-07` (faixa em login, início e `/plataforma`) e, se quiser, desliga e confere que some. Orquestrador abre o PR (a branch parte da do #151 com a `origin/main` mesclada; refazer o merge da main quando o #151 entrar).
