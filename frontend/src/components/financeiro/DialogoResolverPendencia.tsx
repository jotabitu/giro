"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { financeiro, type AcaoDaPendencia, type PendenciaPagamento } from "@/lib/api";
import { campoDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { EscolhaDeOpcao, ErroDoFinanceiro } from "./Comuns";

/**
 * Resolve uma pendência do pagamento (`POST pendencias-pagamento/{id}/resolver/`, AUT-05, FIN-04): baixar a conta ou ignorar o aviso.
 * Baixar só aparece quando a API diz que a conta ainda está aberta (`acoes.baixar`); o valor da baixa é o da própria API.
 */
export function DialogoResolverPendencia({ pendencia, aoFechar, aoConcluir }: { pendencia: PendenciaPagamento; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cliente = useQueryClient();
  const [acao, setAcao] = useState<AcaoDaPendencia>(pendencia.acoes.baixar ? "baixar" : "ignorar");
  const [motivo, setMotivo] = useState("");
  const resolver = useMutation({
    mutationFn: () => financeiro.resolverPendencia(pendencia.id, { acao, motivo: motivo.trim() }),
    onSuccess: async (resolvida) => {
      await cliente.invalidateQueries({ queryKey: ["pendencias-pagamento"] });
      await cliente.invalidateQueries({ queryKey: ["contas-receber"] });
      aoConcluir(`Pendência de ${pendencia.cliente.nome} resolvida. ${resolvida.resolucao?.texto ?? ""}`.trim());
    },
  });

  const opcoes: { valor: AcaoDaPendencia; rotulo: string }[] = pendencia.acoes.baixar
    ? [
        { valor: "baixar", rotulo: "Baixar a conta" },
        { valor: "ignorar", rotulo: "Ignorar o aviso" },
      ]
    : [{ valor: "ignorar", rotulo: "Ignorar o aviso" }];
  const pronto = motivo.trim() !== "" && !resolver.isPending;

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Resolver pendência"
      descricao={`${pendencia.cliente.nome} · ${pendencia.cobranca.id_no_parceiro}${pendencia.valor_pago_centavos !== null ? ` · ${dinheiro(pendencia.valor_pago_centavos)}` : ""}. ${pendencia.detalhe}`}
      tamanho="pequeno"
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!pronto} onClick={() => resolver.mutate()}>
            {resolver.isPending ? "Resolvendo…" : "Resolver"}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (pronto) resolver.mutate();
        }}
      >
        <EscolhaDeOpcao rotulo="O que fazer" opcoes={opcoes} valor={acao} aoMudar={setAcao} colunas={2} />
        {!pendencia.acoes.baixar && <p className="m-0 text-caption text-ink-muted">A conta não está mais aberta, por isso só dá para ignorar o aviso.</p>}
        <TextField cheio data-autofocus rotulo="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(resolver.error, "motivo")} dica="Fica registrado na auditoria." />
        {resolver.isError && !campoDoErro(resolver.error, "motivo") && <ErroDoFinanceiro erro={resolver.error} />}
      </form>
    </Dialogo>
  );
}
