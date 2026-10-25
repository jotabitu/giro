"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useReconfirmar2fa } from "@/components/acesso/useReconfirmar2fa";
import { Button, Icone } from "@/design-system";
import { assinatura as api, type MotivoCancelamento, type TelaDoCancelamento } from "@/lib/api";
import { nomeConfere } from "@/lib/assinatura";
import { mensagemDoErro } from "@/lib/erros";
import { ReconfirmacaoCancelada } from "@/lib/reconfirmar-2fa";
import { useSessao } from "@/lib/sessao";
import { DialogoPausarAssinatura } from "./DialogoPausarAssinatura";
import { PlanosDaAssinatura } from "./PlanosDaAssinatura";

// Referência: docs/telas/html/Admin-Cancelar-Desktop.dc.html e Admin-Cancelar-Mobile.dc.html.
// Tudo vem de GET /api/assinatura/cancelamento/ (docs/api/cancelamento.md): motivos, alternativas, "O que acontece" e nome da confirmação.

function Motivos({
  motivos,
  escolhido,
  aoEscolher,
  comentario,
  aoComentar,
}: {
  motivos: TelaDoCancelamento["motivos"];
  escolhido: MotivoCancelamento | null;
  aoEscolher: (m: MotivoCancelamento) => void;
  comentario: string;
  aoComentar: (c: string) => void;
}) {
  return (
    <section className="wl-panel" aria-label="Por que você quer cancelar?">
      <h2 className="mb-1 text-heading">Por que você quer cancelar?</h2>
      <p className="m-0 mb-4 text-caption text-ink-muted">Ajuda a gente a melhorar. Não muda nada no cancelamento.</p>
      <div role="radiogroup" aria-label="Por que você quer cancelar?" className="flex flex-col gap-2">
        {motivos.map((m) => {
          const ativo = escolhido === m.codigo;
          return (
            <button
              key={m.codigo}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => aoEscolher(m.codigo as MotivoCancelamento)}
              className={`flex items-center gap-2.5 rounded-[16px] bg-surface px-3.5 py-3 text-left text-body ${ativo ? "ring-2 ring-ink ring-inset" : "ring-1 ring-line ring-inset"}`}
            >
              <span
                aria-hidden="true"
                className={`size-[18px] shrink-0 rounded-full ${ativo ? "shadow-[inset_0_0_0_5px_var(--ink)]" : "shadow-[inset_0_0_0_1.5px_var(--ink)]"}`}
              />
              <span>{m.rotulo}</span>
            </button>
          );
        })}
      </div>
      <textarea
        className="wl-input mt-3 h-auto w-full resize-none pt-3"
        rows={2}
        maxLength={500}
        placeholder="Quer contar mais? (opcional)"
        aria-label="Quer contar mais? (opcional)"
        value={comentario}
        onChange={(e) => aoComentar(e.target.value)}
      />
    </section>
  );
}

function Alternativas({
  alternativas,
  aoPausar,
  aoVerPlano,
}: {
  alternativas: TelaDoCancelamento["alternativas"];
  aoPausar: () => void;
  aoVerPlano: () => void;
}) {
  if (!alternativas.pausar && !alternativas.mudar_para_essencial) return null;
  return (
    <section className="wl-panel" aria-label="Antes de ir, que tal…">
      <h2 className="mb-4 text-heading">Antes de ir, que tal…</h2>
      <div className="flex flex-col gap-2.5">
        {alternativas.pausar && (
          <div className="flex flex-wrap items-center gap-3.5 rounded-[20px] bg-surface-sunken p-4">
            <div className="min-w-0 flex-1">
              <div className="font-semibold">Pausar por até 3 meses</div>
              <div className="text-caption text-ink-muted">{alternativas.pausar.texto}</div>
            </div>
            <Button compacto onClick={aoPausar}>
              Pausar assinatura
            </Button>
          </div>
        )}
        {alternativas.mudar_para_essencial && (
          <div className="flex flex-wrap items-center gap-3.5 rounded-[20px] bg-surface-sunken p-4">
            <div className="min-w-0 flex-1">
              <div className="font-semibold">Mudar para o {alternativas.mudar_para_essencial.plano.nome}</div>
              <div className="text-caption text-ink-muted">{alternativas.mudar_para_essencial.resumo}</div>
            </div>
            <Button compacto onClick={aoVerPlano}>
              Ver plano
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

/** Administração › Assinatura › Cancelar assinatura (T-198, PLT-06, PLT-07). */
export function CancelarAssinatura() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const router = useRouter();
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["assinatura", "cancelamento"], queryFn: () => api.telaCancelamento(), enabled: podeVer });
  const t = podeVer ? consulta.data : undefined;

  const [motivo, setMotivo] = useState<MotivoCancelamento | null>(null);
  const [comentario, setComentario] = useState("");
  const [nomeDigitado, setNomeDigitado] = useState("");
  const [pausaAberta, setPausaAberta] = useState(false);
  const [verPlanos, setVerPlanos] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  // 403 `2fa_recente` (PLT-06, USR-02): o diálogo reconfirma o código e repete o cancelamento uma vez, com o mesmo corpo.
  const { executar, dialogo } = useReconfirmar2fa();
  const cancelar = useMutation({
    mutationFn: () => {
      if (!motivo) throw new Error("Escolha um motivo.");
      const corpo = { motivo, nome_confirmacao: nomeDigitado };
      return executar(() => api.cancelar(corpo));
    },
    onSuccess: async (res) => {
      cliente.setQueryData(["assinatura"], res);
      await Promise.all([cliente.invalidateQueries({ queryKey: ["assinatura"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
      if (res.status !== "cancelada") {
        setAviso(res.cancelamento?.rotulo ?? "Cancelamento marcado.");
        router.push("/admin/assinatura");
      }
    },
  });

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa a Assinatura.
      </p>
    );

  if (cancelar.data?.status === "cancelada") {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-title md:text-display">Cancelar assinatura</h1>
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Esta assinatura foi cancelada. Para pedir seus dados ou voltar, fale com a equipe Giro.
        </p>
      </div>
    );
  }

  const podeConfirmar = Boolean(t && motivo && nomeConfere(nomeDigitado, t.confirmacao.nome));

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-4">
        <Link href="/admin/assinatura" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Cancelar assinatura</h1>
          {t && <p className="m-0 mt-1.5 text-body text-ink-muted">{t.plano_resumo}</p>}
        </div>
        <Link href="/admin/assinatura" className="wl-btn ml-auto hidden no-underline md:inline-flex">
          Voltar
        </Link>
      </header>

      {consulta.isError && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      )}
      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}

      {t && (
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_520px]">
            <Motivos motivos={t.motivos} escolhido={motivo} aoEscolher={setMotivo} comentario={comentario} aoComentar={setComentario} />
            <Alternativas alternativas={t.alternativas} aoPausar={() => setPausaAberta(true)} aoVerPlano={() => setVerPlanos(true)} />
          </div>

          <aside className="flex min-w-0 flex-col gap-6 md:flex-[1_1_340px]" aria-label="O que acontece e confirmação">
            <section className="wl-panel" aria-label="O que acontece">
              <h2 className="mb-1 text-heading">O que acontece</h2>
              {t.o_que_acontece.map((l) => (
                <div key={l.codigo} className="flex justify-between gap-3 border-b border-line py-2.5 text-body last:border-b-0">
                  <span className="text-ink-muted">{l.rotulo}</span>
                  <span className="text-right font-medium">{l.valor}</span>
                </div>
              ))}
            </section>

            <section className="wl-panel ring-2 ring-critical-soft ring-inset" aria-label="Confirmar">
              <h2 className="mb-2 text-heading md:hidden">Confirmar</h2>
              <label className="wl-field">
                <span className="wl-field__label">Para confirmar, digite o nome da empresa</span>
                <input
                  className="wl-input"
                  placeholder={t.confirmacao.nome}
                  value={nomeDigitado}
                  onChange={(e) => setNomeDigitado(e.target.value)}
                />
              </label>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href="/admin/exportar" className="wl-btn no-underline">
                  <Icone de={Download} />
                  Exportar dados antes
                </Link>
                <button
                  type="button"
                  className="wl-btn bg-critical text-white"
                  disabled={!podeConfirmar || cancelar.isPending}
                  onClick={() => cancelar.mutate()}
                >
                  {cancelar.isPending ? "Cancelando…" : "Cancelar assinatura"}
                </button>
              </div>
              <p className="m-0 mt-3 text-caption text-ink-muted">{t.exportar.texto}</p>
              {cancelar.isError && !(cancelar.error instanceof ReconfirmacaoCancelada) && (
                <p role="alert" className="m-0 mt-3 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
                  {mensagemDoErro(cancelar.error)}
                </p>
              )}
            </section>
          </aside>
        </div>
      )}

      {dialogo}

      {t?.alternativas.pausar && (
        <DialogoPausarAssinatura
          aberto={pausaAberta}
          mesesDisponiveis={t.alternativas.pausar.meses}
          inicio={t.alternativas.pausar.inicio}
          texto={t.alternativas.pausar.texto}
          aoFechar={() => setPausaAberta(false)}
          aoConcluir={(res) => {
            setPausaAberta(false);
            setAviso(res.pausa?.rotulo ?? "Pausa agendada.");
            router.push("/admin/assinatura");
          }}
        />
      )}
      {verPlanos && (
        <PlanosDaAssinatura
          podeMudar
          aoFechar={() => setVerPlanos(false)}
          aoConcluir={(msg) => {
            setVerPlanos(false);
            setAviso(msg);
            router.push("/admin/assinatura");
          }}
        />
      )}
    </div>
  );
}
