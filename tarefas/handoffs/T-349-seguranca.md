# T-349 · Janela das 2 etapas recentes: 5 ou 15 minutos · segurança → orquestrador, arquiteto

**O que foi feito:** análise, sem código. Pergunta: a janela efetiva de 5 minutos (a vida do access que traz o `auth_time`) está boa, ou o `auth_time` deveria seguir pela rotação do refresh até os 15 minutos de `DOIS_FATORES_RECENTE`?
**Onde:** li `comum/autenticacao.py:44-72` e `:116-159`, `config/settings/base.py:303-307`, `apps/contas/api/acesso.py:524-549`, `apps/plataforma/api/assinatura.py:529-560`, `apps/auditoria/services.py:85-88` e `:260-263`, a ADR 0032, `contas.md` ("Reconfirmar as 2 etapas"), `cancelamento.md`, `auditoria.md` (S-15) e as regras USR-02, USR-04, USR-06, PLT-06, PLT-07 e PLT-08. Nenhum arquivo de código mudou.
**Regras:** USR-02, USR-06, PLT-06, PLT-07, S-15.

## Recomendação: manter como está

A janela efetiva de 5 minutos fica. O `auth_time` **não** deve seguir pela rotação do refresh. Não precisa de ADR nova nem de tarefa de backend.

## Por quê

1. **O que o `2fa_recente` protege é a sessão roubada.** As duas ações (cancelar e o backup completo) já pedem uma sessão logada com 2 etapas. A checagem extra só tem valor contra quem tem a sessão e não tem o autenticador. Hoje, quem rouba o refresh (cookie) consegue renovar, mas o access renovado não traz `auth_time`: para cancelar ou gerar o ZIP, ainda precisa do código. Se o `auth_time` seguisse pela rotação, quem roubasse o refresh nos 15 minutos depois do login teria as 2 etapas recentes de graça. A checagem passaria a dizer "a dona da sessão fez login com código há pouco", e deixaria de dizer "quem está pedindo tem o autenticador agora".
2. **A revogação por reuso (P-07) chega tarde.** Com o refresh copiado, o primeiro a renovar ganha. A sessão só cai quando o outro lado tenta renovar com o refresh já trocado. Com o access de 5 minutos, isso leva até 5 minutos. Dá tempo de pedir o backup completo, e o ZIP é vazamento: não se desfaz. O cancelamento ainda tem o `DELETE cancelamento/`, mas tira o acesso de todos se for na `inadimplente` ou na `suspensa`.
3. **O suporte (PLT-07) não muda nada aqui.** O token de suporte recebe 403 `PLT-07` no `POST cancelamento/` (`suporte_proibido`, `assinatura.py:532`) e na própria reconfirmação (T-347). Ele não chega à ação nem com 5 nem com 15 minutos.
4. **O custo de usabilidade já está resolvido.** A ADR 0032 dá o caminho: a tela recebe o 403, pede o código, reconfirma e repete o pedido uma vez. O código é pedido no momento da ação, que é o ponto do step-up. Com 15 minutos pela rotação, o ganho seria poupar um código de quem cancela logo depois do login, o que é raro, e a troca é o risco do item 1.
5. **A regra não diz 15 minutos.** USR-02 obriga as 2 etapas para administrador e financeiro, PLT-06 diz quem cancela e S-15 trata dos links com prazo. Nenhuma dá número para "recente". O "no máximo 15 minutos" está só nos contratos (`cancelamento.md:21`, `cancelamento.md:300`, `auditoria.md:137`) e na constante. Os 5 minutos cumprem "no máximo 15". Não há divergência para o Produto resolver.

## Texto: o que mudar e o que não mudar

- **`docs/regras-de-negocio.md`:** não muda. Escrever "5 minutos" na regra prenderia a regra à vida do access, que é configuração técnica (ADR 0014).
- **`DOIS_FATORES_RECENTE` = 15 minutos:** fica. Ela é o teto: se a vida do access subir um dia, o `auth_time` continua valendo no máximo 15 minutos. Baixar para 5 não muda nada hoje e obriga a reescrever `test_t018` (900 e 901 segundos).
- **Sugestão baixa para o arquiteto (sem tarefa própria):** em `cancelamento.md:21`/`:300` e `auditoria.md:137`, acrescentar depois de "no máximo 15 minutos": "(na prática, enquanto vale o access que trouxe o código: 5 minutos; ADR 0032, item 3)". O `contas.md:98` já explica isso; os outros dois contratos ficam coerentes com ele.

## Para lembrar na fase 2 (backup completo)

`baixar` do ZIP também pede `2fa_recente` (`auditoria/services.py:262`). O link do e-mail vale 7 dias, então quem baixa quase sempre recebe o 403 antes. Isso está certo, porque baixar o ZIP é o momento do vazamento. Mas a tela de download precisa usar o mesmo diálogo da T-348. Vale pôr no critério da tarefa de frontend do backup quando ela for escrita.

**Próximo passo para quem recebe:**
- **Orquestrador:** fechar a pergunta como "mantém". Levar ao arquiteto a sugestão baixa de texto, se quiser.
- **Arquiteto:** nada obrigatório. A ADR 0032, item 3, já registra a decisão que esta análise confirma.
