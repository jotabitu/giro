# T-073 · Telas de convite e redefinição com o token no fragmento · frontend → orquestrador, seguranca, qa, backend (T-069)

**O que foi feito (contrato da T-072, `docs/api/contas.md`):**
- `/convite` (era `/convite/[token]`) e `/entrar/redefinir` leem o token do fragmento (`#token`) com `useTokenDoFragmento` (`lib/fragmento.ts`), apagam o fragmento da barra e do histórico com `history.replaceState` e guardam o token só em memória. A query `?token=` da redefinição deixou de valer.
- Convite: `consultarConvite({ token })` (`POST /api/convites/consultar/`) e `aceitarConvite({ token, nome, senha, aparelho })` (`POST /api/convites/aceitar/`) nos dados falsos; o token vai no corpo, nunca no caminho. `redefinirSenha({ token, senha_nova })` já levava no corpo.
- Link sem token: convite mostra "Convite não encontrado" e a redefinição mostra "Link vencido" com "Pedir novo link". Enquanto o navegador não leu o fragmento, as telas mostram "Carregando".
- No modo estrito do React o efeito roda duas vezes; a segunda leitura não apaga o token já guardado.

**Onde:** `frontend/src/lib/fragmento.ts`, `lib/api/falso.ts`, `components/acesso/{AceitarConvite,RedefinirSenha}.tsx`, `app/(publico)/convite/page.tsx`.
**Testes:** `lib/fragmento.test.ts` (leitura do fragmento, `replaceState` mantendo caminho e query, sem fragmento não mexe, e o token no corpo dos três endpoints falsos).
**Check:** `eslint`, `tsc --noEmit`, 126 testes e `next build` verdes. No navegador (Chromium, `next dev`): `/convite#convite-rodrigo` e `/entrar/redefinir#link-valido` abrem a tela certa e a barra fica sem o `#`; `/convite` sem token mostra "Convite não encontrado".
**Dependências novas:** nenhuma (sem jsdom: a lógica do fragmento é função pura testada com `location` e `history` simulados).

**O que ficou de fora:**
- Ligar na API real (T-069 e depois): troca `contas` em `lib/api/index.ts`.
- Convite da plataforma (`admin.<dominio>/convite#<token>`, `{ token, senha }`): não há tela de plataforma ainda; o hook serve a ela.
- `/suporte/entrar#<token>` não existe no frontend.
- O falso não divergiu da main em nada além disso; os contratos de entrada do login real (PR #55) não foram tocados.
