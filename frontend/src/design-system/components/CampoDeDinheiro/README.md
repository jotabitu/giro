# CampoDeDinheiro

Campo de valor em reais com a pontuação aparecendo enquanto a pessoa digita. É o único campo de dinheiro do sistema (T-509).

Os dígitos entram pela direita como centavos: "5", "0", "0", "0", "0", "0" mostram `0,05`, `0,50`, `5,00`, `50,00`, `500,00` e `5.000,00`. Apagar volta um dígito; campo vazio fica vazio. Colar "5.000,00" ou "5000" dá `5.000,00` (sem vírgula, o número colado é em reais). Teto de R$ 999.999.999,99; a API confere o limite de cada campo.

`prefixo` põe "R$ " na frente, só onde a tela de referência já mostra. Sem ele o campo mostra `5.000,00`. O resto é o `TextField`: rótulo, `dica`, `erro`, `mono`, `cheio`.

## Em React

Código em `frontend/src/design-system/components/CampoDeDinheiro/CampoDeDinheiro.tsx`; preview em `/design-system/campo-de-dinheiro`.

```tsx
import { CampoDeDinheiro, InputDeDinheiro } from "@/design-system";

<CampoDeDinheiro cheio rotulo="Entrada" prefixo value={entrada} onChange={(e) => setEntrada(e.target.value)} />
<CampoDeDinheiro cheio rotulo="Valor de compra" prefixo {...register("valor_compra")} />
<InputDeDinheiro value={valor} onChange={(e) => setValor(e.target.value)} />
```

A máscara é aplicada no próprio evento, antes de `onChange` ler `e.target.value`; por isso serve a campo controlado e a `register` do React Hook Form sem adaptador. O texto do campo ("5.000,00" ou "R$ 5.000,00") é o que `centavosDoTexto` e `centavosDoCampo` convertem em centavos; o valor enviado à API continua sendo `valor_centavos`, e a validação final é da API. `InputDeDinheiro` é o mesmo comportamento num `<input>` solto, para linhas de tabela que montam o próprio rótulo. `mascaraDinheiro` e `centavosDoColado` ficam exportadas para quem formata fora de um campo.
