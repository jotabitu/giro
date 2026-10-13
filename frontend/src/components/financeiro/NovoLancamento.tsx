"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { EscolherCliente } from "@/components/locacoes/SeletoresDaLocacao";
import { financeiro, type ClienteResumo, type LancamentoAvulso } from "@/lib/api";
import { campoDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";
import { EscolhaDeOpcao, ErroDoFinanceiro } from "./Comuns";

const TIPOS: { valor: LancamentoAvulso["tipo"]; rotulo: string }[] = [
  { valor: "multa", rotulo: "Multa" },
  { valor: "avaria", rotulo: "Avaria" },
  { valor: "outro", rotulo: "Outro" },
];

/** Lançamento avulso (multa, avaria ou outro). Parcelas e caução de locação nascem na locação, não aqui. */
export function NovoLancamento({ aoFechar, aoConcluir }: { aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const [escolhendo, setEscolhendo] = useState(false);
  const [quem, setQuem] = useState<ClienteResumo | null>(null);
  const [tipo, setTipo] = useState<LancamentoAvulso["tipo"]>("multa");
  const [descricao, setDescricao] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [valor, setValor] = useState("");
  const centavos = centavosDoTexto(valor);

  const lancar = useMutation({
    mutationFn: () => {
      if (!quem || centavos === null) throw new Error("incompleto");
      return financeiro.lancar({ cliente_id: quem.id, tipo, descricao: descricao.trim(), vencimento, valor_centavos: centavos });
    },
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["contas-receber"] });
      aoConcluir(`Lançamento de ${dinheiro(centavos ?? 0)} criado para ${quem?.nome}.`);
      aoFechar();
    },
  });
  const completo = quem !== null && centavos !== null && descricao.trim() !== "" && vencimento !== "";

  if (escolhendo)
    return (
      <EscolherCliente
        aoFechar={() => setEscolhendo(false)}
        aoEscolher={(c) => {
          setQuem(c);
          setEscolhendo(false);
        }}
      />
    );

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Novo lançamento"
      descricao="Cobrança avulsa de um cliente. A API confere o valor e o vencimento."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!completo || lancar.isPending} onClick={() => lancar.mutate()}>
            {lancar.isPending ? "Lançando…" : "Lançar"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3 rounded-md bg-surface-sunken px-4 py-3">
          <span className="min-w-0 truncate text-body">{quem ? quem.nome : "Nenhum cliente escolhido"}</span>
          <Button compacto onClick={() => setEscolhendo(true)}>
            {quem ? "Trocar" : "Escolher cliente"}
          </Button>
        </div>
        <EscolhaDeOpcao rotulo="Tipo" opcoes={TIPOS} valor={tipo} aoMudar={setTipo} />
        <TextField cheio rotulo="Descrição" value={descricao} onChange={(e) => setDescricao(e.target.value)} erro={campoDoErro(lancar.error, "descricao")} />
        <div className="grid gap-4 md:grid-cols-2">
          <TextField cheio rotulo="Valor (R$)" inputMode="decimal" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} erro={valor !== "" && centavos === null ? "Informe um valor, como 150,00" : campoDoErro(lancar.error, "valor_centavos")} />
          <TextField cheio rotulo="Vencimento" type="date" value={vencimento} onChange={(e) => setVencimento(e.target.value)} erro={campoDoErro(lancar.error, "vencimento")} />
        </div>
        {lancar.isError && !["descricao", "valor_centavos", "vencimento"].some((c) => campoDoErro(lancar.error, c)) && <ErroDoFinanceiro erro={lancar.error} />}
      </div>
    </Dialogo>
  );
}
