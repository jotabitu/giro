"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import {
  ErroApi,
  veiculos,
  type CorrecaoDeIdentificacao,
  type VeiculoDetalhe,
} from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { placa as placaComHifen } from "@/lib/formatos";

type Erros = Partial<Record<"placa" | "chassi" | "motivo", string>>;

const limpaPlaca = (t: string) => t.replace(/[\s-]/g, "").toUpperCase();
const limpaChassi = (t: string) => t.replace(/\s/g, "").toUpperCase();

/**
 * Corrigir placa ou chassi (VEI-01), do administrador: para erro de digitação, com motivo e auditoria na API.
 * Só vai o que mudou. Placa e chassi únicos e o chassi de 17 caracteres são conferidos pela API; o erro volta no campo.
 * Sem tela de referência própria: monta o Dialogo do design system com os campos da ficha (pedir ao design-system se mudar).
 */
export function CorrigirIdentificacao({
  ficha,
  aoFechar,
  aoConcluir,
}: {
  ficha: VeiculoDetalhe;
  aoFechar: () => void;
  aoConcluir: (mensagem: string) => void;
}) {
  const cliente = useQueryClient();
  const [placa, setPlaca] = useState(placaComHifen(ficha.placa));
  const [chassi, setChassi] = useState(ficha.chassi);
  const [motivo, setMotivo] = useState("");
  const [erros, setErros] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  const corpo = (): CorrecaoDeIdentificacao => {
    const c: CorrecaoDeIdentificacao = { motivo: motivo.trim() };
    if (limpaPlaca(placa) !== ficha.placa) c.placa = limpaPlaca(placa);
    if (limpaChassi(chassi) !== ficha.chassi) c.chassi = limpaChassi(chassi);
    return c;
  };
  const mudou =
    limpaPlaca(placa) !== ficha.placa || limpaChassi(chassi) !== ficha.chassi;

  const gravar = useMutation({
    mutationFn: () => veiculos.corrigirIdentificacao(ficha.id, corpo()),
    onSuccess: async () => {
      await Promise.all([
        cliente.invalidateQueries({ queryKey: ["veiculo", ficha.id] }),
        cliente.invalidateQueries({ queryKey: ["veiculos"] }),
      ]);
      aoConcluir("Identificação corrigida. A mudança ficou na auditoria.");
      aoFechar();
    },
    onError: (e) => {
      setErros({});
      setErroGeral(null);
      if (e instanceof ErroApi && e.campos) {
        const novos: Erros = {};
        for (const [campo, mensagem] of Object.entries(e.campos))
          if (campo === "placa" || campo === "chassi" || campo === "motivo")
            novos[campo] = mensagem;
        setErros(novos);
        if (Object.keys(novos).length === 0) setErroGeral(e.message);
      } else if (e instanceof ErroApi && e.codigo === "VEI-01") {
        // Colisão: a API diz qual campo em `detalhes.campo`.
        const campo = e.detalhes?.campo === "chassi" ? "chassi" : "placa";
        setErros({ [campo]: e.message });
      } else {
        setErroGeral(mensagemDoErro(e));
      }
    },
  });

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Corrigir placa ou chassi"
      descricao="Use só para erro de digitação. A placa e o chassi antigos ficam na auditoria com o motivo."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button
            variante="solido"
            disabled={gravar.isPending || !mudou || motivo.trim() === ""}
            onClick={() => gravar.mutate()}
          >
            {gravar.isPending ? "Salvando…" : "Corrigir"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {erroGeral && (
          <p
            role="alert"
            className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink"
          >
            {erroGeral}
          </p>
        )}
        <TextField
          cheio
          mono
          rotulo="Placa"
          autoComplete="off"
          value={placa}
          onChange={(e) => setPlaca(e.target.value)}
          erro={erros.placa}
        />
        <TextField
          cheio
          mono
          rotulo="Chassi"
          autoComplete="off"
          maxLength={20}
          value={chassi}
          onChange={(e) => setChassi(e.target.value)}
          erro={erros.chassi}
        />
        <TextField
          cheio
          rotulo="Motivo"
          autoComplete="off"
          dica="Obrigatório. Por exemplo: erro de digitação no cadastro"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          erro={erros.motivo}
        />
      </div>
    </Dialogo>
  );
}
