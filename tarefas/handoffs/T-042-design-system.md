# T-042 · Componente CodigoVerificacao · design-system → orquestrador, frontend (T-020)

**O que foi feito:** `CodigoVerificacao` em `frontend/src/design-system/components/CodigoVerificacao/` (componente, `logica.ts`, README, testes), exportado por `@/design-system`, com preview em `/design-system/codigo-verificacao` (código com erro simulado, e estado desabilitado). Segue a tela `Ativar-2FA` (6 caixas, erro em `critical`).
**Como usar:**
```tsx
<CodigoVerificacao rotulo="Código do aplicativo" valor={codigo} aoMudar={setCodigo}
  aoCompletar={(v) => verificar(v)} erro={erro} autoFocus />
```
Controlado (`valor` só de dígitos, sem buracos). Props: `rotulo`, `valor`, `aoMudar`, `aoCompletar?`, `erro?`, `tamanho?` (6), `disabled?`, `autoFocus?`. Com React Hook Form, use `Controller`.
**Comportamento:**
- Digitar avança; digitar sobre um dígito troca só ele; letras e símbolos são ignorados.
- Colar o código inteiro (aceita `481 029` e `481-029`) preenche tudo; colar no meio mantém o começo; o excesso é cortado.
- `autocomplete="one-time-code"` e `inputmode="numeric"` em todas as caixas: o preenchimento automático do celular cai na 1ª caixa e é distribuído.
- Backspace (apaga e, em caixa vazia, volta), Delete, setas, Home e End. O conteúdo da caixa fica selecionado ao focar.
- `aoCompletar` dispara quando o 6º dígito entra, por qualquer caminho (digitar, colar, preenchimento). Se a tela tiver botão "Ativar verificação" (como `Ativar-2FA`), ignore-o.
- Erro: `erro` pinta as caixas de `critical`, marca `aria-invalid`, mostra a mensagem em `role="alert"` e liga ao grupo por `aria-describedby`. Limpe o erro quando o código mudar (o preview faz isso). A mensagem vem da API (`codigo_invalido`).
- Acessível: grupo nomeado pelo `rotulo`, cada caixa com "Dígito n de 6", foco visível, alvos de 56 a 60px.
**Fora do escopo:** códigos de recuperação (`K7Q2-9XMD`, com letras e hífen) não usam este componente: use `TextField` com `mono`.
**Verificado:**
- lint, typecheck e 42 testes verdes (22 novos: lógica de digitar, colar, apagar, setas e tamanho; marcação, ARIA, erro, desabilitado) e build verde.
- Testei os eventos reais num Edge de verdade, dirigido por CDP, no preview em `next start`: digitar, avançar, Backspace (com e sem dígito), setas, Home, End, colar `123 456`, colar texto sem dígito, sobrescrever, colar no meio e `insertText` de 6 dígitos (simula o preenchimento automático). Todos passaram. O erro aparece ao completar um código errado e some ao editar.
- O preenchimento automático real do iOS e do Android (SMS e gerenciador de senhas) não foi testado em aparelho; só o equivalente por `insertText`.
**Detalhe:** em teclados de celular que não mandam `keydown` de Backspace em caixa vazia, o recuo só funciona ao apagar com o dígito ainda na caixa. O comportamento principal (digitar, colar, apagar o dígito) não depende disso.
**Branch:** `t-042-componente-otp`, criada a partir da `t-004-design-system-codigo`; não inclui as telas da T-026 (estão em outra branch).
**Próximo passo para quem recebe:** frontend (T-020) troca as caixas de código de `Ativar-2FA` e do login por este componente.
