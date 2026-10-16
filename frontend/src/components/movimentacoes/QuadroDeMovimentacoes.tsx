"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Aviso } from "@/components/acesso/Aviso";
import { Confirmacao } from "@/components/financeiro/Comuns";
import { Button, Dialogo, Icone, SearchField, TextField } from "@/design-system";
import { movimentacoes, type ColunaDoQuadro, type LinhaDaMovimentacao } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { COR_DA_COLUNA, MENSAGEM_DA_COLUNA_VAZIA, podeGerirMovimentacoes, ROTA_DA_NOVA_MOVIMENTACAO } from "@/lib/movimentacoes";
import { useSessao } from "@/lib/sessao";
import { CartaoDaMovimentacao } from "./CartaoDaMovimentacao";

// Referência: docs/telas/html/Movimentacoes-Desktop.dc.html e Movimentacoes-Mobile.dc.html (MOV-01 a MOV-06).
// O quadro, as colunas, o resumo de cada cartão e os botões vêm da API (GET /api/movimentacoes/quadro/).

function Coluna({ coluna, podeCriar, ocupado, aoIniciar, aoCancelar }: { coluna: ColunaDoQuadro; podeCriar: boolean; ocupado: boolean; aoIniciar: (m: LinhaDaMovimentacao) => void; aoCancelar: (m: LinhaDaMovimentacao) => void }) {
  return (
    <section aria-label={coluna.rotulo} className="flex min-w-0 flex-col gap-[10px] rounded-[28px] bg-surface p-[14px]">
      <div className="flex items-center gap-2 px-[6px] pt-1 pb-[6px] text-[16px] font-semibold">
        <span aria-hidden="true" className={`size-[10px] rounded-pill ${COR_DA_COLUNA[coluna.status]}`} />
        {coluna.rotulo}
        <span className="wl-count ml-auto">{coluna.total}</span>
      </div>
      {coluna.itens.length === 0 && <p className="m-0 px-1 py-3 text-body text-ink-muted">{MENSAGEM_DA_COLUNA_VAZIA[coluna.status]}</p>}
      {coluna.itens.map((m) => (
        <CartaoDaMovimentacao key={m.id} m={m} ocupado={ocupado} aoIniciar={aoIniciar} aoCancelar={aoCancelar} />
      ))}
      {coluna.status === "agendada" && podeCriar && (
        <Link href={ROTA_DA_NOVA_MOVIMENTACAO} className="flex h-[42px] items-center justify-center gap-[6px] rounded-[16px] border-[1.5px] border-dashed border-line text-body text-ink-muted">
          <Icone de={Plus} />
          Nova
        </Link>
      )}
    </section>
  );
}

/** Movimentações: quadro por estado. Cada cartão muda de coluna pelo botão dele (Iniciar, Registrar chegada); só a agendada se cancela. */
export function QuadroDeMovimentacoes() {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const { valor, definir } = useFiltrosNaUrl();
  const filtro = valor("busca") ?? "";
  const [busca, setBusca] = useBuscaNaUrl(definir, filtro);
  const [colunaDoCelular, setColunaDoCelular] = useState<ColunaDoQuadro["status"]>("em_transito");
  const [cancelando, setCancelando] = useState<LinhaDaMovimentacao | null>(null);
  const [motivo, setMotivo] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const podeCriar = podeGerirMovimentacoes(eu);

  const quadro = useQuery({ queryKey: ["movimentacoes", "quadro", { busca: filtro }], queryFn: () => movimentacoes.quadro({ busca: filtro || undefined }), placeholderData: (a) => a });
  const atualizar = () => cliente.invalidateQueries({ queryKey: ["movimentacoes"] });
  const iniciar = useMutation({
    mutationFn: (m: LinhaDaMovimentacao) => movimentacoes.iniciar(m.id),
    onSuccess: async (m) => (await atualizar(), setAviso(`${m.codigo} saiu. Registre a chegada quando o veículo chegar.`)),
  });
  const cancelar = useMutation({
    mutationFn: () => movimentacoes.cancelar(cancelando?.id ?? 0, motivo.trim()),
    onSuccess: async (m) => {
      setCancelando(null);
      setMotivo("");
      await atualizar();
      setAviso(`${m.codigo} cancelada.`);
    },
  });
  const ocupado = iniciar.isPending || cancelar.isPending;
  const colunas = quadro.data?.colunas ?? [];
  const erro = iniciar.error ?? cancelar.error ?? quadro.error;

  return (
    <div className="flex flex-col gap-5">
      <nav aria-label="Você está em" className="hidden text-body text-ink-muted md:block">
        <Link href="/veiculos" className="text-ink-muted no-underline">
          Veículos
        </Link>{" "}
        / Movimentações
      </nav>
      <header className="flex flex-wrap items-center gap-3 md:gap-4">
        <Link href="/veiculos" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-[44px] md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1 md:flex-none">
          <h1 className="text-title md:text-display">Movimentações</h1>
          <p className="mt-[6px] mb-0 text-body text-ink-muted">
            <span className="hidden md:inline">Levar veículos entre filiais, lava-jato, oficina e despachante</span>
            <span className="md:hidden">escolha a coluna</span>
          </p>
        </div>
        <div className="flex items-center gap-2 md:ml-auto">
          <div className="hidden w-[260px] md:block">
            <SearchField placeholder="Placa ou modelo" atalho={false} cheio value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
          {podeCriar && (
            <Link href={ROTA_DA_NOVA_MOVIMENTACAO} aria-label="Nova movimentação" className="wl-btn wl-btn--solid max-md:size-[44px] max-md:!min-w-0 max-md:!p-0 md:h-[56px] md:px-[28px]">
              <Icone de={Plus} />
              <span className="hidden md:inline">Nova movimentação</span>
            </Link>
          )}
        </div>
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}
      {erro && <Aviso tipo="erro">{mensagemDoErro(erro)}</Aviso>}
      {quadro.isPending && (
        <p role="status" className="m-0 text-body text-ink-muted">
          Carregando as movimentações…
        </p>
      )}

      {colunas.length > 0 && (
        <>
          <div role="group" aria-label="Coluna" className="flex gap-2 overflow-x-auto md:hidden">
            {colunas.map((c) => (
              <button
                key={c.status}
                type="button"
                aria-pressed={c.status === colunaDoCelular}
                onClick={() => setColunaDoCelular(c.status)}
                className={`inline-flex h-[44px] shrink-0 items-center gap-[6px] rounded-pill px-[14px] text-body whitespace-nowrap ${c.status === colunaDoCelular ? "bg-solid text-on-solid" : "bg-surface text-ink"}`}
              >
                {c.rotulo} {c.total}
              </button>
            ))}
          </div>
          <div className="grid items-start gap-4 md:grid-cols-4">
            {colunas.map((c) => (
              <div key={c.status} className={c.status === colunaDoCelular ? "" : "max-md:hidden"}>
                <Coluna coluna={c} podeCriar={podeCriar} ocupado={ocupado} aoIniciar={(m) => iniciar.mutate(m)} aoCancelar={(m) => setCancelando(m)} />
              </div>
            ))}
          </div>
        </>
      )}

      <p className="m-0 hidden text-caption text-ink-muted md:block">
        Cada cartão muda de coluna pelo botão dele: Iniciar e Registrar chegada. Veículo alugado, reservado, vendido ou baixado não pode ser movimentado. Depois de sair, a movimentação termina com a chegada; só a agendada se cancela. Em movimentação, o veículo disponível some da Nova locação e da reserva. Na chegada, o km é atualizado e, se o destino for outra filial, o veículo passa a ser dela.
      </p>

      <Dialogo
        aberto={cancelando !== null}
        aoFechar={() => setCancelando(null)}
        titulo={`Cancelar ${cancelando?.codigo ?? "movimentação"}`}
        descricao="Só a movimentação agendada se cancela. O veículo continua onde está."
        fecharAoClicarFora={false}
        acoes={
          <>
            <Button variante="quieto" onClick={() => setCancelando(null)}>
              Voltar
            </Button>
            <Button variante="solido" disabled={cancelar.isPending || motivo.trim() === ""} onClick={() => cancelar.mutate()}>
              Cancelar movimentação
            </Button>
          </>
        }
      >
        <TextField rotulo="Motivo" cheio value={motivo} onChange={(e) => setMotivo(e.target.value)} />
      </Dialogo>
    </div>
  );
}
