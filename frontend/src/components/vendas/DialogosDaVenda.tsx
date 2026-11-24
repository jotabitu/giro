"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Aviso, Button, Dialogo, TextField } from "@/design-system";
import { vendas, type VendaDetalhe } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { atualizarVendas } from "@/lib/vendas";

// Diálogos da tela Venda (VEN-13, VEN-19). Os textos são os da tela de referência e da VEN-19.

/** Proposta → negociação. A nota é opcional e vai só para a auditoria. */
export function RespostaDoCliente({ venda, aoFechar }: { venda: VendaDetalhe; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const [nota, setNota] = useState("");
  const registrar = useMutation({
    mutationFn: () => vendas.registrarResposta(venda.id, nota.trim()),
    onSuccess: async () => {
      await atualizarVendas(cliente);
      aoFechar();
    },
  });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Registrar resposta do cliente"
      descricao="A venda passa para negociação."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={registrar.isPending} onClick={() => registrar.mutate()}>
            {registrar.isPending ? "Registrando…" : "Registrar resposta"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <TextField cheio data-autofocus rotulo="O que o cliente respondeu" maxLength={300} value={nota} onChange={(e) => setNota(e.target.value)} dica="Até 300 caracteres. Fica no histórico da venda." erro={campoDoErro(registrar.error, "nota")} />
        {registrar.isError && !campoDoErro(registrar.error, "nota") && <Aviso tom="critico">{mensagemDoErro(registrar.error)}</Aviso>}
      </div>
    </Dialogo>
  );
}

const SAI_DAS_ABERTAS = "A venda sai das abertas e o veículo fica livre para outra proposta.";

/** Qualquer estado em andamento → perdida, com o motivo obrigatório. O pedido de desconto pendente é cancelado pela API. */
export function PerderVenda({ venda, aoFechar }: { venda: VendaDetalhe; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const perder = useMutation({
    mutationFn: () => vendas.perder(venda.id, motivo.trim()),
    onSuccess: async () => {
      await atualizarVendas(cliente);
      aoFechar();
    },
  });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Marcar como perdida"
      descricao={SAI_DAS_ABERTAS}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={motivo.trim() === "" || perder.isPending} onClick={() => perder.mutate()}>
            {perder.isPending ? "Marcando…" : "Marcar como perdida"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {/* VEN-19: com a entrada paga, a API manda o texto do reembolso; nos outros casos, a mesma frase de cima. */}
        {venda.perder_texto && venda.perder_texto !== SAI_DAS_ABERTAS && <Aviso tom="atencao">{venda.perder_texto}</Aviso>}
        <TextField cheio data-autofocus rotulo="Motivo" maxLength={200} value={motivo} onChange={(e) => setMotivo(e.target.value)} dica="Obrigatório." erro={campoDoErro(perder.error, "motivo")} />
        {perder.isError && !campoDoErro(perder.error, "motivo") && <Aviso tom="critico">{mensagemDoErro(perder.error)}</Aviso>}
      </div>
    </Dialogo>
  );
}
