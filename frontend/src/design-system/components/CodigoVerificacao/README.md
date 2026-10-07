# CodigoVerificacao

Campo de código de verificação em 2 etapas: uma caixa por dígito (6 por padrão), como em `docs/telas/html/Ativar-2FA-*.dc.html` e no login com `etapa: verificar_2fa`.

```tsx
import { CodigoVerificacao } from "@/design-system";

const [codigo, setCodigo] = useState("");
<CodigoVerificacao
  rotulo="Código do aplicativo"
  valor={codigo}
  aoMudar={setCodigo}
  aoCompletar={(v) => verificar(v)}
  erro={erro ? "Código incorreto. Confira o horário do celular e tente de novo." : undefined}
  autoFocus
/>
```

- **Controlado:** `valor` é uma string só de dígitos, sem buracos (a caixa `i` mostra `valor[i]`). Com React Hook Form, use `Controller`.
- **Digitar:** o dígito entra e o foco avança. Digitar sobre um dígito troca só ele. Letras e símbolos são ignorados.
- **Colar o código inteiro** (com espaço ou hífen, como `481 029`): preenche todas as caixas. Colar numa caixa do meio mantém o começo e substitui dali em diante; o excesso é cortado.
- **Preenchimento automático do celular:** as caixas levam `autocomplete="one-time-code"` e `inputmode="numeric"`; o SMS ou o gerenciador de senhas preenche na primeira caixa e o componente distribui os dígitos.
- **Teclado:** Backspace apaga o dígito da caixa, ou o último e volta se ela estiver vazia; Delete apaga no lugar; setas, Home e End movem o foco. Ao focar, o conteúdo da caixa fica selecionado.
- **`aoCompletar`** é chamado quando o último dígito entra, por qualquer caminho. Não use se a tela preferir um botão de confirmar, como em `Ativar-2FA`.
- **Erro:** `erro` pinta as caixas de `critical`, marca `aria-invalid` e mostra a mensagem em `role="alert"`, ligada ao grupo por `aria-describedby`. A mensagem diz o problema e como resolver; ela vem da API (`codigo_invalido`). Limpe o erro quando o código mudar.
- **Acessibilidade:** o grupo (`role="group"`) é nomeado pelo `rotulo`; cada caixa diz "Dígito 3 de 6". Foco visível pelo anel padrão. Alvos de 56 a 60px de altura.
- **Tamanho:** `tamanho` muda a quantidade de caixas. Para os códigos de recuperação (`K7Q2-9XMD`, alfanumérico com hífen), use um `TextField` com `mono`: este componente só aceita dígitos.
- Estilos `wl-otp*` em `componentes.css`, só com tokens. Em telas estreitas as caixas dividem a largura.
- A lógica (sem DOM) fica em `logica.ts` e é testada à parte.
