# T-026 · Telas de acesso que faltavam · design-system → orquestrador, frontend (T-020)

**O que foi feito:** quatro telas novas em `docs/telas/html/` e no índice `docs/telas/README.md` (seção Login), no padrão de `Acesso-Senha` (cabeçalho com logo da empresa, painéis `surface`, passos numerados, marca trocável por `brand`):
- `Esqueci-Senha-Desktop|Mobile`: 4 estados em painéis, cada um com a legenda de quando aparece. (1) pedir o link, (2) "Confira seu e-mail", (3) criar a nova senha, (4) "Link vencido".
- `Ativar-2FA-Desktop|Mobile`: (1) adicionar a conta ao aplicativo (QR, chave para digitar, no celular botão "Abrir no autenticador"), (2) código de 6 dígitos com o erro "Código incorreto…", (3) 8 códigos de recuperação, com copiar, baixar e a confirmação "Guardei os códigos".
**Segue `contas.md` (arquiteto) e regras:**
- `senha/esqueci/` responde 202 sempre: a mensagem do estado 2 é igual exista ou não o e-mail ("Se este e-mail tiver acesso…"). Link de 1 hora e uso único, 3 pedidos por e-mail por hora.
- `senha/redefinir/`: regras da senha (12+, letras e números, diferente do e-mail e do nome da empresa, fora da lista de comuns), aviso de que todas as sessões saem e de que as 2 etapas continuam valendo, 410 `link_expirado` = "Este link venceu. Peça outro.". "Repita a senha" é validação só do frontend (a API recebe só `senha_nova`, como em `Acesso-Senha`).
- 2 etapas: aviso "Seu perfil exige…" aparece só quando `exige_2fa` (USR-02: administrador e financeiro, ou exigido pela empresa); o nome da conta no aplicativo é o da locadora (`issuer`), nunca Giro; códigos de recuperação mostrados uma única vez (`2fa/verificar/` ou `2fa/ativar/`); erro com a mensagem exata de `codigo_invalido`; 5 erros somados bloqueiam 15 min (USR-06).
- Sem "Manter conectado" (decisão do dono).
**Ajustes em telas existentes (divergências que achei):**
- `Login-Desktop` tinha "Manter conectado neste computador": removido (contradiz USR-06 e a decisão do dono).
- `Login-Desktop` dizia que "gerente e financeiro" pedem o código; a USR-02 diz administrador e financeiro: corrigido.
- "Esqueci a senha" do Login (desktop e celular) agora leva às telas novas.
**Observações para o frontend (T-020):**
- Os 4 estados de `Esqueci-Senha` viram rotas/estados: `entrar/esqueci` (1 e 2) e `entrar/redefinir?token=` (3 e 4). O QR é só ilustração: gerar a partir de `otpauth_uri` da API (pede uma lib de QR, dependência nova a registrar no PR) e nunca mandar a chave a terceiros.
- Quem chega por `etapa: configurar_2fa` usa `token_pre_2fa`; quem ativa por conta própria usa o access e `2fa/ativar/`. A tela é a mesma.
- Sem componente de campo de 6 dígitos no design system ainda: o OTP (6 caixas) e a lista de códigos são markup das telas. Se a T-020 precisar, peço ao design-system que vire componente (`OtpField`).
**Verificado:** abri as 4 telas no Edge headless (desktop 1440 e celular 390); sem sobra de conteúdo cortado. Os links entre Login e as telas novas funcionam. Não rodei contraste automático; só usei tokens e classes já existentes.
**Próximo passo:** frontend (T-020) recria as telas com `@/design-system`; orquestrador decide o PR.
