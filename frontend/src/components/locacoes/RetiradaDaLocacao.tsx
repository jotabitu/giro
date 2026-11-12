"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";
import { Button, Dialogo, Icone, Panel, TextField } from "@/design-system";
import { financeiro, locacoes, type ContaReceber, type LocacaoCompleta, type ParcelaDaLocacao, type PassoDaRetirada, type RegistrarRetirada } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { LinkCopiado, useCopiarLink } from "@/components/comum/LinkParaCopiar";
import { BaixaDaConta } from "@/components/financeiro/BaixaDaConta";

// LOC-17 e FIN-18 (T-451, T-452): o "Para retirar", as "Pendências da retirada", o "Registrar retirada" e o "Registrar pagamento".
// Os passos, os textos, o que falta e quem pode cada ação vêm da API (docs/api/locacoes.md); a tela não decide nada disso.

type AoConcluir = (mensagem: string) => void;
type Variante = "desktop" | "celular";

/** O `id` do painel Pagamentos de cada árvore (desktop e celular estão as duas no DOM), para o "Ver pagamentos". */
export const idDosPagamentos = (variante: Variante) => `pagamentos-${variante}`;

/** Há conta com "Registrar pagamento" (FIN-18)? Então o painel Pagamentos aparece nas duas árvores. */
export const temPagamentoARegistrar = (l: LocacaoCompleta) => l.parcelas?.some((p) => p.acoes.receber) ?? false;

function atualizarFicha(cliente: ReturnType<typeof useQueryClient>, id: number) {
  return Promise.all([cliente.invalidateQueries({ queryKey: ["locacao", id] }), cliente.invalidateQueries({ queryKey: ["locacoes"] })]);
}

/** As ações de um passo: o `codigo` é a mesma chave de `acoes` da locação, que a tela já sabe executar. */
function AcoesDoPasso({ l, passo, ancora, aoConcluir }: { l: LocacaoCompleta; passo: PassoDaRetirada; ancora?: string; aoConcluir: AoConcluir }) {
  const cliente = useQueryClient();
  const enviar = useMutation({
    mutationFn: () => locacoes.gerarContrato(l.id),
    onSuccess: async () => {
      await atualizarFicha(cliente, l.id);
      aoConcluir("Contrato enviado. O cliente recebe o link de assinatura por WhatsApp.");
    },
  });
  const reenviar = useMutation({ mutationFn: () => locacoes.reenviarContrato(l.id), onSuccess: () => aoConcluir("Link de assinatura reenviado por WhatsApp.") });
  const link = useCopiarLink(() => locacoes.copiarLinkDoContrato(l.id));
  // O passo do pagamento não tem ação na API: cada conta tem "Registrar pagamento" na seção Pagamentos. A tela só leva até lá.
  const verPagamentos = passo.codigo === "pagamento" && !passo.feito && ancora;
  if (passo.acoes.length === 0 && !verPagamentos) return null;
  const erro = link.erro ?? (enviar.isError ? mensagemDoErro(enviar.error) : reenviar.isError ? mensagemDoErro(reenviar.error) : null);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {passo.acoes.map((a) => {
          switch (a.codigo) {
            case "continuar_vistoria":
              return (
                <Link key={a.codigo} href={`/locacoes/${l.id}/vistoria`} className="wl-btn wl-btn--sm">
                  {a.rotulo}
                </Link>
              );
            case "gerar_contrato":
              return (
                <Button key={a.codigo} compacto disabled={enviar.isPending} onClick={() => enviar.mutate()}>
                  {enviar.isPending ? "Enviando…" : a.rotulo}
                </Button>
              );
            case "reenviar_contrato":
              return (
                <Button key={a.codigo} compacto disabled={reenviar.isPending} onClick={() => reenviar.mutate()}>
                  {reenviar.isPending ? "Enviando…" : a.rotulo}
                </Button>
              );
            case "copiar_link_contrato":
              return (
                <Button key={a.codigo} compacto disabled={link.pendente} onClick={link.copiar}>
                  {link.pendente ? "Copiando…" : a.rotulo}
                </Button>
              );
            default:
              return null;
          }
        })}
        {verPagamentos && (
          <a href={ancora} className="wl-btn wl-btn--sm">
            Ver pagamentos
          </a>
        )}
      </div>
      {link.resultado && <LinkCopiado resultado={link.resultado} copiado={!link.falhouACopia} aviso="Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." aoFechar={link.limpar} />}
      {erro && (
        <p role="alert" className="text-caption text-critical">
          {erro}
        </p>
      )}
    </div>
  );
}

function Passos({ l, passos, variante, aoConcluir }: { l: LocacaoCompleta; passos: PassoDaRetirada[]; variante: Variante; aoConcluir: AoConcluir }) {
  const ancora = temPagamentoARegistrar(l) ? `#${idDosPagamentos(variante)}` : undefined;
  return (
    <ol className="flex flex-col">
      {passos.map((p) => (
        <li key={p.codigo} className="flex flex-col gap-2 border-b border-line py-3 first:pt-0 last:border-b-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-2 text-body">
            <span aria-hidden="true" className={`mt-[2px] grid h-5 w-5 shrink-0 place-items-center rounded-pill ${p.feito ? "bg-solid text-on-solid" : "shadow-[inset_0_0_0_2px_var(--ink-muted)]"}`}>
              {p.feito && <Icone de={Check} />}
            </span>
            <span className={p.feito ? "text-ink-muted" : "font-medium"}>{p.texto}</span>
            {p.feito && <span className="sr-only">(feito)</span>}
          </div>
          <AcoesDoPasso l={l} passo={p} ancora={ancora} aoConcluir={aoConcluir} />
        </li>
      ))}
    </ol>
  );
}

/** A confirmação "Registrar retirada?": o que falta e o motivo, obrigatório. Os textos são os da API. */
export function ConfirmarRetirada({ l, r, aoFechar, aoConcluir }: { l: LocacaoCompleta; r: RegistrarRetirada; aoFechar: () => void; aoConcluir: AoConcluir }) {
  const cliente = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const [faltouMotivo, setFaltouMotivo] = useState(false);
  const registrar = useMutation({
    mutationFn: () => locacoes.registrarRetirada(l.id, { motivo: motivo.trim() }),
    onSuccess: async (locacao) => {
      cliente.setQueryData(["locacao", l.id], locacao);
      await Promise.all([atualizarFicha(cliente, l.id), cliente.invalidateQueries({ queryKey: ["veiculos"] })]);
      aoConcluir(`Retirada da ${l.codigo} registrada.`);
      aoFechar();
    },
  });
  const confirmar = () => {
    if (!motivo.trim()) {
      setFaltouMotivo(true);
      return;
    }
    registrar.mutate();
  };
  const erroDoMotivo = faltouMotivo && !motivo.trim() ? r.motivo_obrigatorio : campoDoErro(registrar.error, "motivo");
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo={r.titulo}
      acoes={
        <>
          <Button variante="quieto" data-autofocus onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={registrar.isPending} onClick={confirmar}>
            {registrar.isPending ? "Registrando…" : r.rotulo}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {r.faltas.length > 0 && (
          <ul className="flex flex-col gap-1 rounded-md bg-surface-sunken px-4 py-3 text-body">
            {r.faltas.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        )}
        <TextField cheio rotulo="Motivo" maxLength={200} value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={erroDoMotivo} />
        {registrar.isError && !campoDoErro(registrar.error, "motivo") && (
          <p role="alert" className="text-body text-critical">
            {mensagemDoErro(registrar.error)}
          </p>
        )}
      </div>
    </Dialogo>
  );
}

/** "Para retirar" (LOC-17): só na locação `aguardando_retirada`, com os três passos, o prazo e, para quem pode, o "Registrar retirada". */
export function ParaRetirar({ l, variante, aoConcluir }: { l: LocacaoCompleta; variante: Variante; aoConcluir: AoConcluir }) {
  const [confirmando, setConfirmando] = useState(false);
  const idDoAviso = useId();
  const p = l.para_retirar;
  if (!p) return null;
  const r = p.registrar_retirada;
  return (
    <Panel titulo="Para retirar" subtitulo={p.prazo}>
      <Passos l={l} passos={p.passos} variante={variante} aoConcluir={aoConcluir} />
      {r && (
        // No celular, o "Registrar retirada" é a ação principal do painel: largura cheia.
        <div className={`mt-4 flex gap-2 border-t border-line pt-4 ${variante === "celular" ? "flex-col [&_.wl-btn]:w-full" : "items-center justify-between"}`}>
          {r.aviso ? (
            <p id={idDoAviso} className="text-caption text-ink-muted">
              {r.aviso}
            </p>
          ) : (
            <span />
          )}
          <Button variante="solido" disabled={!r.disponivel} aria-describedby={r.aviso ? idDoAviso : undefined} onClick={() => setConfirmando(true)}>
            {r.rotulo}
          </Button>
        </div>
      )}
      {confirmando && r && <ConfirmarRetirada l={l} r={r} aoFechar={() => setConfirmando(false)} aoConcluir={aoConcluir} />}
    </Panel>
  );
}

/** "Pendências da retirada" (LOC-17): depois da retirada à mão, só o que ainda falta; some quando a API manda `null`. */
export function PendenciasDaRetirada({ l, variante, aoConcluir }: { l: LocacaoCompleta; variante: Variante; aoConcluir: AoConcluir }) {
  const p = l.pendencias_retirada;
  if (!p || p.passos.length === 0) return null;
  return (
    <Panel titulo="Pendências da retirada">
      <Passos l={l} passos={p.passos} variante={variante} aoConcluir={aoConcluir} />
    </Panel>
  );
}

/** "Registrar pagamento" de uma conta da locação (FIN-18): a mesma baixa do Receber, sem sair da ficha. Só aparece por `acoes.receber`. */
export function RegistrarPagamento({ l, parcela, aoConcluir }: { l: LocacaoCompleta; parcela: ParcelaDaLocacao; aoConcluir: AoConcluir }) {
  const cliente = useQueryClient();
  const [conta, setConta] = useState<ContaReceber | null>(null);
  const abrir = useMutation({ mutationFn: () => financeiro.obterConta(parcela.conta_id), onSuccess: setConta });
  if (!parcela.acoes.receber) return null;
  return (
    <>
      <Button compacto aria-label={`Registrar pagamento: ${parcela.rotulo}`} disabled={abrir.isPending} onClick={() => abrir.mutate()}>
        {abrir.isPending ? "Abrindo…" : "Registrar pagamento"}
      </Button>
      {abrir.isError && (
        <p role="alert" className="mt-1 text-caption text-critical">
          {mensagemDoErro(abrir.error)}
        </p>
      )}
      {conta && (
        <BaixaDaConta
          conta={conta}
          aoFechar={() => setConta(null)}
          aoConcluir={(m) => {
            void Promise.all([atualizarFicha(cliente, l.id), cliente.invalidateQueries({ queryKey: ["locacao", l.id, "historico"] })]);
            aoConcluir(m);
          }}
        />
      )}
    </>
  );
}
