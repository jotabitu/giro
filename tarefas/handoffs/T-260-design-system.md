# T-260 · Onboarding-Ramo pela tela Admin-Ramo · design-system → frontend

**O que foi feito:** o passo 7 da implantação (`Onboarding-Ramo`, desktop e celular) passou a ter o mesmo conteúdo e os mesmos textos da troca do ramo em Configurações (`Admin-Ramo`, T-253), como pede a etapa 7 ajustada pelo produto na T-256. O cartão do ramo nos hubs `Config-Desktop` e `Config-Mobile` passou a usar o texto que a API manda (`configuracoes.md`, T-259): "Locação e venda · motos".

**Onde:** `docs/telas/html/Onboarding-Ramo-Desktop.dc.html`, `Onboarding-Ramo-Mobile.dc.html`, `Config-Desktop.dc.html`, `Config-Mobile.dc.html`. Os dois `Admin-Ramo-*` e o cartão em `Config-*` vêm da branch da T-253 (PR #249), com o mesmo conteúdo, para esta branch compilar a referência; na junção não há conflito.

**O que a tela mostra, e de onde vem:**
- Atividades "Locação" e "Venda de veículos" (`atividades`) e tipos Motos e Carros (`trabalha_com`), com pelo menos um de cada grupo marcado.
- Essencial: Locação travada (`atividades_aceitas` é `aluga` e `ambos`), "Venda de veículos" com o aviso "Vendas faz parte do plano Profissional.", e nenhuma opção "só vende".
- "Módulos que vamos ligar": a lista `modulos` da combinação marcada, com os nomes do `Recurso.label` e a contagem "{n} módulos no plano {plano}" (Profissional 9, 8 ou 8; Essencial 3).
- Saíram "Como você aluga" e "CNH exigida" (nenhuma regra os pede; a CNH segue a `CLI-02`) e os nove módulos antigos ("Clientes e documentos", "Avaliação de troca"...).
- Mantidos: passo 3 de 8, Voltar e Continuar, a barra de passos. Sem recusa na tela: no passo 7 não há nada aberto no módulo que sai, e a rota só recusa por plano.
- Os dois botões "Profissional" e "Essencial" no alto existem só na referência, para mostrar os dois casos; o frontend não os leva.

**Checagens:** as duas telas renderizadas em Chromium (1440 e 390 px) nos dois planos, com cliques em Essencial e em Locação (travada); links iguais aos de antes; sem emoji nem exclamação; sem token novo.

**Regras cobertas:** PLT-12, etapa 7 da implantação; CA-ASS-51 (passo 7 do Essencial sem "só vende").

**O que ficou de fora:** nada do pedido. Fica registrado que o frontend do passo 7 precisa tratar o 422 `PLT-12` de `PUT /api/ramo/` (`motivo: "plano"`), mesmo que a tela não deixe chegar nele.

**Próximo passo para quem recebe:** o frontend liga as duas telas (passo 7 e Configurações) no mesmo componente, em `GET` e `PUT /api/ramo/`, e o cartão do hub em `GET /api/configuracoes/`, que traz o `resumo`.
