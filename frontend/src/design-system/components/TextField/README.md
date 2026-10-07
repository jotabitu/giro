# TextField

Campo de formulário de 48px com rótulo acima, borda `line` e `radius-md`, usado em cadastros, contratos e vistoria.

O consumidor fornece rótulo, valor ou placeholder de exemplo e uma dica curta. Erro: adicione `wl-field--error` e `aria-invalid="true"`; a borda vai para `critical` e a dica diz o problema e como resolver. Placas, códigos e chassi usam `wl-mono`. Valores em formato brasileiro: `R$ 1.250,00`, `12.430 km`, `03/09/2026`.

## Em React

Código em `frontend/src/design-system/components/TextField/TextField.tsx`; preview em `/design-system/text-field`.

```tsx
import { TextField } from "@/design-system";

<TextField rotulo="Placa" mono dica="Formato Mercosul ou antigo" {...register("placa")} />
<TextField rotulo="CNH" erro="CNH vencida: renove antes de alugar" />
```

`erro` troca a dica pela mensagem, pinta a borda de `critical` e liga `aria-invalid` e `aria-describedby`. O rótulo é um `<label>` ligado ao campo. No React 19 o `ref` passa pelos atributos de `<input>`, então funciona com React Hook Form.
