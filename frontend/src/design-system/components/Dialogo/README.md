# Dialogo

Janela modal centralizada sobre o conteúdo, para confirmar uma ação ou preencher algo curto: "Pedir cancelamento do contrato LOC-2841", "Encerrar a sessão?". Painel `surface` com `radius-xl` e `shadow-pop` (modais são um dos três usos da sombra), fundo escurecido.

```tsx
import { Button, Dialogo, TextField } from "@/design-system";

<Dialogo
  aberto={aberto}
  aoFechar={() => setAberto(false)}
  titulo="Pedir cancelamento do contrato LOC-2841"
  descricao="O gerente vai analisar o pedido. O contrato continua ativo até a aprovação."
  acoes={
    <>
      <Button variante="quieto" onClick={() => setAberto(false)}>Voltar</Button>
      <Button variante="solido" onClick={enviar}>Enviar pedido</Button>
    </>
  }
>
  <TextField cheio data-autofocus rotulo="Motivo" />
</Dialogo>
```

- **Feito sobre o elemento nativo `<dialog>`** aberto com `showModal()`: o navegador prende o foco dentro, deixa o resto da página inerte, trata o Escape e devolve o foco a quem abriu. Sem biblioteca e sem dependência nova (decisão da T-046: shadcn/Radix seria uma camada a mais para o mesmo resultado).
- **Controlado:** `aberto` vem de quem usa. Escape, o botão Fechar e o clique fora só chamam `aoFechar`; feche o diálogo ali. O conteúdo só é montado enquanto está aberto, então campos e estado interno começam limpos a cada abertura.
- **Foco inicial:** o elemento com `data-autofocus` (um campo, ou o botão seguro de uma confirmação destrutiva). Sem ele, o foco vai para o painel e o leitor de tela lê título e descrição antes de o Tab chegar ao primeiro controle.
- **Nome acessível:** `titulo` (`aria-labelledby`) diz o que a pessoa vai fazer; `descricao` (`aria-describedby`) traz a consequência em uma frase.
- **Ações:** ação principal por último e à direita (`solido`), a de saída ao lado (`quieto`). Em confirmação destrutiva, o foco inicial vai para a opção segura ("Continuar aqui").
- **`tamanho`:** `medio` (560px, padrão) ou `pequeno` (400px). `fecharAoClicarFora={false}` em formulário preenchido.
- Em tela estreita o diálogo ocupa a largura menos 16px de cada lado. Para escolhas longas no celular, use `Gaveta` com `lado="baixo"`.
- Animação curta, desligada em `prefers-reduced-motion`.
- Sem texto de exclamação e sem emoji nos títulos: diga a ação.
