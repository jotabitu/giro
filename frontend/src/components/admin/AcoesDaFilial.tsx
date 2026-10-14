"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { filiais, ErroApi, type FilialDaLista, type ImpedimentosDaDesativacao } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";

type Modo = "menu" | "desativar" | "reativar";

/** Os impedimentos vêm juntos da API (`FIL-06`): a tela lista todos, não um de cada vez. */
function Impedimentos({ erro }: { erro: unknown }) {
  if (!(erro instanceof ErroApi) || erro.codigo !== "FIL-06") return null;
  const d = erro.detalhes as unknown as ImpedimentosDaDesativacao | undefined;
  if (!d) return null;
  const linhas = [
    d.matriz && "É a matriz. Escolha outra matriz antes.",
    d.ultima_filial && "É a última filial ativa. A empresa precisa de ao menos uma.",
    d.operacao.veiculos > 0 && `${d.operacao.veiculos} ${d.operacao.veiculos === 1 ? "veículo" : "veículos"} na filial. Transfira antes.`,
    d.operacao.locacoes > 0 && `${d.operacao.locacoes} ${d.operacao.locacoes === 1 ? "locação" : "locações"} em andamento.`,
    d.operacao.caixas > 0 && `${d.operacao.caixas} ${d.operacao.caixas === 1 ? "caixa aberto" : "caixas abertos"}.`,
  ].filter(Boolean) as string[];
  return (
    <ul className="flex list-disc flex-col gap-1 pl-5 text-caption" aria-label="O que impede">
      {linhas.map((l) => (
        <li key={l}>{l}</li>
      ))}
    </ul>
  );
}

/** Menu "Mais ações" do cartão: tornar matriz, desativar e reativar (docs/api/filiais.md). */
export function AcoesDaFilial({ filial, aoFechar, aoConcluir }: { filial: FilialDaLista; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const [modo, setModo] = useState<Modo>("menu");
  const [motivo, setMotivo] = useState("");

  const depois = async (mensagem: string) => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["filiais-admin"] }), cliente.invalidateQueries({ queryKey: ["filiais-minhas"] })]);
    aoConcluir(mensagem);
    aoFechar();
  };
  const matriz = useMutation({ mutationFn: () => filiais.tornarMatriz(filial.id), onSuccess: () => depois(`${filial.nome} agora é a matriz.`) });
  const desativar = useMutation({ mutationFn: () => filiais.desativar(filial.id, motivo.trim()), onSuccess: () => depois(`${filial.nome} foi desativada. Nada foi apagado.`) });
  const reativar = useMutation({ mutationFn: () => filiais.reativar(filial.id, motivo.trim()), onSuccess: () => depois(`${filial.nome} voltou a funcionar.`) });
  const confirmar = modo === "desativar" ? desativar : reativar;

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={modo === "menu"}
      tamanho="pequeno"
      titulo={filial.nome}
      descricao={modo === "menu" ? "O que você quer fazer com esta filial?" : modo === "desativar" ? "Ela sai do seletor de todos. Veículos, caixa e histórico continuam guardados." : "Ela volta ao seletor, se o plano permitir."}
      acoes={
        modo === "menu" ? (
          <Button variante="quieto" onClick={aoFechar}>
            Fechar
          </Button>
        ) : (
          <>
            <Button variante="quieto" onClick={() => (setModo("menu"), setMotivo(""))}>
              Voltar
            </Button>
            <Button variante="solido" disabled={motivo.trim() === "" || confirmar.isPending} onClick={() => confirmar.mutate()}>
              {modo === "desativar" ? "Desativar filial" : "Reativar filial"}
            </Button>
          </>
        )
      }
    >
      {modo === "menu" ? (
        <div className="flex flex-col gap-2">
          {filial.ativo && !filial.matriz && (
            <Button disabled={matriz.isPending} onClick={() => matriz.mutate()}>
              Tornar matriz
            </Button>
          )}
          {filial.ativo ? <Button onClick={() => setModo("desativar")}>Desativar filial</Button> : <Button onClick={() => setModo("reativar")}>Reativar filial</Button>}
          {matriz.isError && (
            <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
              {mensagemDoErro(matriz.error)}
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <TextField cheio data-autofocus rotulo="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(confirmar.error, "motivo")} />
          {confirmar.isError && !campoDoErro(confirmar.error, "motivo") && (
            <div role="alert" className="flex flex-col gap-2 rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
              <span>{mensagemDoErro(confirmar.error)}</span>
              <Impedimentos erro={confirmar.error} />
            </div>
          )}
        </div>
      )}
    </Dialogo>
  );
}
