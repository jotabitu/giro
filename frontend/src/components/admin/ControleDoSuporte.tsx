"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Contador, Dialogo, Icone, StatusBadge, TextField, type TomStatus } from "@/design-system";
import { suporte as api, type AcessoDoSuporte, type SituacaoDoSuporte } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCurta, iniciais } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Admin-Suporte-Desktop.dc.html e Admin-Suporte-Mobile.dc.html. Contrato: docs/api/contas.md, "Controle do administrador".
// Rótulos, contagens, filtro e `acoes` vêm da API (PLT-07); a tela só liga cada botão à rota.

const ABAS: { valor: SituacaoDoSuporte; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "ativos", rotulo: "Ativos" },
  { valor: "encerrados", rotulo: "Encerrados" },
];

const TOM: Record<AcessoDoSuporte["status"], TomStatus> = { ativo: "sucesso", encerrado: "neutro", revogado: "critico" };

const EXPLICACOES = [
  { titulo: "Dados pessoais protegidos", texto: "Mesmo no modo suporte, o operador nunca recebe CPF completo, CNH ou fotos de documentos sensíveis." },
  { titulo: "Tempo limitado e expiração", texto: "Todo acesso tem duração definida e expira sozinho, sem permissão para renovar." },
  { titulo: "Auditoria de todas as ações", texto: "Cada alteração entra na auditoria da sua empresa com o nome de quem fez, como Suporte Giro." },
];

/** Administração › Configurações › Controle do suporte: bloquear, liberar e revogar o acesso da equipe Giro (PLT-07). */
export function ControleDoSuporte() {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const [situacao, setSituacao] = useState<SituacaoDoSuporte>("todos");
  const [bloqueando, setBloqueando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [revogando, setRevogando] = useState<AcessoDoSuporte | null>(null);
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["suporte", situacao], queryFn: () => api.listar(situacao), enabled: podeVer });

  const atualizar = async () => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["suporte"] }), cliente.invalidateQueries({ queryKey: ["configuracoes"] })]);
  };
  const bloquear = useMutation({
    mutationFn: () => api.bloquear(motivo.trim() || undefined),
    onSuccess: async () => {
      setBloqueando(false);
      setMotivo("");
      await atualizar();
    },
  });
  const liberar = useMutation({ mutationFn: () => api.liberar(), onSuccess: atualizar });
  const revogar = useMutation({
    mutationFn: (id: number) => api.revogar(id),
    onSuccess: async () => {
      setRevogando(null);
      await atualizar();
    },
  });

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa o controle do suporte.
      </p>
    );

  const d = consulta.data;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-3 md:items-end md:gap-4">
        <Link href="/admin/configuracoes" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 shrink-0 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1 text-caption text-ink-muted md:text-body">
            <Icone de={Lock} />
            Configurações › Controle do suporte
          </div>
          <h1 className="text-title md:mt-1.5 md:text-display">Controle do suporte</h1>
          <p className="mt-1.5 hidden text-body text-ink-muted md:block">Acesso da equipe técnica Giro à conta da sua empresa</p>
        </div>
      </header>

      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando o controle do suporte…
        </p>
      )}

      {d && (
        <section className="wl-panel flex flex-col gap-4" aria-label="Situação do suporte">
          <div className="flex flex-wrap items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-[14px] bg-surface-sunken" aria-hidden="true">
              <Icone de={ShieldCheck} />
            </span>
            <h2 className="min-w-0 flex-1 text-heading">{d.situacao_rotulo}</h2>
            <StatusBadge tom={d.bloqueado ? "critico" : "sucesso"}>{d.bloqueado ? "Bloqueado" : "Liberado"}</StatusBadge>
          </div>
          <p className="m-0 text-body text-ink-muted">
            Quando liberado, técnicos autorizados do Giro podem entrar na sua empresa, por tempo limitado, para ajudar em chamados. Toda entrada é auditada com o nome de quem entrou.
          </p>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-4">
            {d.bloqueado ? (
              <Button variante="solido" disabled={liberar.isPending} onClick={() => liberar.mutate()}>
                {liberar.isPending ? "Liberando…" : "Liberar suporte Giro"}
              </Button>
            ) : (
              <>
                <Button variante="solido" onClick={() => setBloqueando(true)}>
                  Bloquear suporte Giro
                </Button>
                <span className="text-caption text-ink-muted">Revoga na hora qualquer acesso ativo</span>
              </>
            )}
          </div>
          {liberar.isError && (
            <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
              {mensagemDoErro(liberar.error)}
            </p>
          )}
        </section>
      )}

      <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-3">
        {EXPLICACOES.map((e) => (
          <li key={e.titulo} className="rounded-[22px] bg-surface p-4">
            <div className="font-semibold">{e.titulo}</div>
            <p className="m-0 mt-1 text-caption text-ink-muted">{e.texto}</p>
          </li>
        ))}
      </ul>

      {d && (
        <section className="flex flex-col gap-3" aria-label="Acessos da equipe Giro">
          <div>
            <h2 className="text-heading">Acessos da equipe Giro</h2>
            <p className="m-0 text-caption text-ink-muted">Histórico dos últimos 90 dias</p>
          </div>
          <div role="group" aria-label="Situação" className="flex gap-2 overflow-x-auto pb-1">
            {ABAS.map((a) => {
              const ativo = a.valor === situacao;
              return (
                <button
                  key={a.valor}
                  type="button"
                  aria-pressed={ativo}
                  onClick={() => setSituacao(a.valor)}
                  className={`inline-flex h-[44px] shrink-0 items-center gap-2 rounded-pill py-0 pr-[6px] pl-4 text-body whitespace-nowrap md:h-10 ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
                >
                  {a.rotulo}
                  <span className={ativo ? "[&_.wl-count]:!bg-brand [&_.wl-count]:!text-on-brand" : "[&_.wl-count]:!bg-surface"}>
                    <Contador>{d.contagens[a.valor]}</Contador>
                  </span>
                </button>
              );
            })}
          </div>

          {d.acessos.length === 0 ? (
            <p className="m-0 rounded-lg bg-surface p-4 text-body text-ink-muted">Nenhum acesso do suporte neste filtro.</p>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {d.acessos.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-3 rounded-[22px] bg-surface p-4">
                  <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-full bg-surface-sunken text-caption font-semibold">
                    {iniciais(a.nome)}
                  </span>
                  <div className="min-w-[180px] flex-1">
                    <div className="font-semibold">{a.nome}</div>
                    <div className="text-caption text-ink-muted">{a.motivo}</div>
                  </div>
                  <div className="text-caption text-ink-muted">
                    <div>{dataHoraCurta(a.inicio)}</div>
                    <div>{a.permissao_rotulo}</div>
                  </div>
                  <StatusBadge tom={TOM[a.status]}>{a.status_rotulo}</StatusBadge>
                  {a.acoes.revogar && (
                    <Button compacto variante="quieto" onClick={() => setRevogando(a)}>
                      Revogar acesso
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <Dialogo
        aberto={bloqueando}
        aoFechar={() => setBloqueando(false)}
        titulo="Bloquear suporte Giro"
        descricao="Revoga na hora qualquer acesso ativo. A equipe Giro só volta a entrar quando você liberar."
        tamanho="pequeno"
        acoes={
          <>
            <Button variante="quieto" onClick={() => setBloqueando(false)}>
              Voltar
            </Button>
            <Button variante="solido" disabled={bloquear.isPending} onClick={() => bloquear.mutate()}>
              {bloquear.isPending ? "Bloqueando…" : "Bloquear suporte"}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <TextField cheio rotulo="Motivo (opcional)" value={motivo} maxLength={200} onChange={(e) => setMotivo(e.target.value)} />
          {bloquear.isError && (
            <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
              {mensagemDoErro(bloquear.error)}
            </p>
          )}
        </div>
      </Dialogo>

      <Dialogo
        aberto={revogando !== null}
        aoFechar={() => setRevogando(null)}
        titulo="Revogar acesso"
        descricao={revogando ? `${revogando.nome} perde o acesso agora. ${revogando.motivo}` : undefined}
        tamanho="pequeno"
        acoes={
          <>
            <Button variante="quieto" onClick={() => setRevogando(null)}>
              Voltar
            </Button>
            <Button variante="solido" disabled={revogar.isPending} onClick={() => revogando && revogar.mutate(revogando.id)}>
              {revogar.isPending ? "Revogando…" : "Revogar acesso"}
            </Button>
          </>
        }
      >
        {revogar.isError && (
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            {mensagemDoErro(revogar.error)}
          </p>
        )}
      </Dialogo>
    </div>
  );
}
