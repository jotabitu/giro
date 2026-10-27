"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { clientes, ErroApi, type ClienteCompleto, type PendenciaDoCliente } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";

// Bloquear, desbloquear, inativar e reativar o cliente (CLI-03, CLI-05, CLI-09; docs/api/clientes.md).
// A API decide: a tela só oferece o botão que cabe na situação e no perfil, e mostra o texto e os erros que ela devolve.

type Acao = "bloquear" | "desbloquear" | "inativar" | "reativar";

const TEXTOS: Record<Acao, { botao: string; titulo: string; descricao: string; confirmar: string; rotuloMotivo: string }> = {
  bloquear: {
    botao: "Bloquear cliente",
    titulo: "Bloquear cliente",
    descricao: "O cliente não poderá iniciar locação nem venda até ser desbloqueado. O motivo fica registrado.",
    confirmar: "Bloquear cliente",
    rotuloMotivo: "Motivo do bloqueio",
  },
  desbloquear: {
    botao: "Desbloquear cliente",
    titulo: "Desbloquear cliente",
    descricao: "O cliente volta a poder alugar. O motivo fica registrado.",
    confirmar: "Desbloquear cliente",
    rotuloMotivo: "Motivo do desbloqueio",
  },
  inativar: {
    botao: "Inativar cliente",
    titulo: "Inativar cliente",
    descricao: "O cliente some da lista padrão e da escolha em locação e venda. Nada é apagado, e você pode reativar depois.",
    confirmar: "Inativar cliente",
    rotuloMotivo: "Motivo da inativação",
  },
  reativar: {
    botao: "Reativar cliente",
    titulo: "Reativar cliente",
    descricao: "O cliente volta à lista e à escolha em locação e venda. Ele fica ativo ou incompleto, conforme as pendências do cadastro.",
    confirmar: "Reativar cliente",
    rotuloMotivo: "Motivo da reativação",
  },
};

/** Quais ações cabem: o perfil (administrador e gerente; o vendedor só pede o desbloqueio) e a situação do cliente. */
export function acoesDoCliente(perfil: string, status: ClienteCompleto["status"]): Acao[] {
  const gestor = perfil === "administrador" || perfil === "gerente";
  const lista: Acao[] = [];
  if (gestor && (status === "ativo" || status === "incompleto")) lista.push("bloquear");
  if ((gestor || perfil === "vendedor") && status === "bloqueado") lista.push("desbloquear");
  if (gestor && status !== "inativo") lista.push("inativar");
  if (gestor && status === "inativo") lista.push("reativar");
  return lista;
}

/** As linhas do 422 `cliente_com_pendencia`, na ordem do contrato. */
export function linhasDaPendencia(d: Partial<PendenciaDoCliente>): string[] {
  const linhas: string[] = [];
  if (d.locacao_aberta) linhas.push("Tem locação em andamento.");
  if ((d.em_aberto_centavos ?? 0) > 0) linhas.push(`Tem ${dinheiro(d.em_aberto_centavos!)} em aberto.`);
  if (d.venda_aberta) linhas.push("Tem venda em andamento.");
  return linhas;
}

function DialogoDaAcao({ acao, cliente, aoFechar, aoConcluir }: { acao: Acao; cliente: ClienteCompleto; aoFechar: () => void; aoConcluir: (aviso: string) => void }) {
  const cache = useQueryClient();
  const t = TEXTOS[acao];
  const [motivo, setMotivo] = useState("");
  const executar = useMutation({
    mutationFn: async (): Promise<{ aviso: string; cliente?: ClienteCompleto }> => {
      const m = motivo.trim();
      if (acao === "bloquear") return { aviso: "Cliente bloqueado.", cliente: await clientes.bloquear(cliente.id, m) };
      if (acao === "inativar") return { aviso: "Cliente inativado.", cliente: await clientes.inativar(cliente.id, m) };
      if (acao === "reativar") return { aviso: "Cliente reativado.", cliente: await clientes.reativar(cliente.id, m) };
      const r = await clientes.desbloquear(cliente.id, m);
      if (r.status === 202) return { aviso: "Pedido de desbloqueio enviado. Um gerente ou o administrador precisa aprovar." };
      return { aviso: "Cliente desbloqueado.", cliente: r.cliente };
    },
    onSuccess: async ({ aviso, cliente: novo }) => {
      if (novo) cache.setQueryData(["cliente", cliente.id], novo);
      await Promise.all([cache.invalidateQueries({ queryKey: ["cliente", cliente.id] }), cache.invalidateQueries({ queryKey: ["clientes"] }), cache.invalidateQueries({ queryKey: ["contadores"] })]);
      aoConcluir(aviso);
    },
  });

  const erro = executar.error;
  const pendencia = erro instanceof ErroApi && erro.codigo === "cliente_com_pendencia" ? linhasDaPendencia((erro.detalhes ?? {}) as Partial<PendenciaDoCliente>) : null;

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo={`${t.titulo} · ${cliente.nome}`}
      descricao={t.descricao}
      tamanho="pequeno"
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={executar.isPending || !motivo.trim()} onClick={() => executar.mutate()}>
            {executar.isPending ? "Enviando…" : t.confirmar}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (motivo.trim() && !executar.isPending) executar.mutate();
        }}
      >
        <TextField cheio data-autofocus rotulo={t.rotuloMotivo} value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(erro, "motivo")} />
        {executar.isError && !campoDoErro(erro, "motivo") && (
          <div role="alert" className="flex flex-col gap-1 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            <span>{mensagemDoErro(erro)}</span>
            {pendencia && pendencia.length > 0 && (
              <ul className="m-0 list-disc pl-5">
                {pendencia.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </form>
    </Dialogo>
  );
}

/** Painel "Situação do cadastro" do detalhe do cliente: só mostra o que o perfil e a situação permitem. */
export function AcoesDoCliente({ c }: { c: ClienteCompleto }) {
  const { eu } = useSessao();
  const [aberta, setAberta] = useState<Acao | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const acoes = acoesDoCliente(eu.perfil, c.status);

  if (acoes.length === 0 && !aviso) return null;
  return (
    <section className="wl-panel flex flex-col gap-3" aria-label="Situação do cadastro">
      {aviso && (
        <p role="status" className="m-0 rounded-lg bg-success-soft p-3 text-body text-success-ink">
          {aviso}
        </p>
      )}
      {acoes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {acoes.map((a) => (
            <Button key={a} compacto variante="quieto" onClick={() => (setAviso(null), setAberta(a))}>
              {TEXTOS[a].botao}
            </Button>
          ))}
        </div>
      )}
      {aberta && (
        <DialogoDaAcao
          acao={aberta}
          cliente={c}
          aoFechar={() => setAberta(null)}
          aoConcluir={(msg) => {
            setAberta(null);
            setAviso(msg);
          }}
        />
      )}
    </section>
  );
}
