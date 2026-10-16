"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo } from "@/design-system";
import { assinatura as api, type FormaDaAssinatura, type FormaDePagamento, type ProximoPasso } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCurta } from "@/lib/formatos";
import { CodigoDePagamento } from "./ComunsDaAssinatura";

// Referência: "Forma de pagamento" das telas Admin-Assinatura. Nenhum dado de cartão passa pelo Giro (ADR 0023):
// o cartão é digitado na página do parceiro. A API diz qual é o próximo passo de cada forma.
export const OPCOES_DE_FORMA: { valor: FormaDaAssinatura; rotulo: string; texto: string; curto: string }[] = [
  { valor: "cartao", rotulo: "Cartão de crédito", texto: "Cobrança automática todo mês", curto: "Cobrança automática" },
  { valor: "pix_automatico", rotulo: "Pix automático", texto: "Autoriza uma vez no app do banco", curto: "Autoriza uma vez no banco" },
  { valor: "boleto", rotulo: "Boleto", texto: "Enviado por e-mail 5 dias antes", curto: "Por e-mail 5 dias antes" },
];

const TEXTO_DO_TOM: Record<string, string> = { perigo: "text-critical-ink", alerta: "text-warning-ink", sucesso: "text-success-ink", info: "text-ink", neutro: "text-ink-muted" };

/** Forma de pagamento da assinatura: a situação vem da API, e escolher outra forma leva ao passo seguinte dela. */
export function FormaDePagamentoDaAssinatura({ forma, pode }: { forma: FormaDePagamento; pode: boolean }) {
  const cliente = useQueryClient();
  const [passo, setPasso] = useState<ProximoPasso | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const escolher = useMutation({
    mutationFn: (f: FormaDaAssinatura) => api.escolherForma(f),
    onSuccess: async (r) => {
      setAviso(r.proximo_passo ? null : "Forma de pagamento salva.");
      setPasso(r.proximo_passo);
      await Promise.all([cliente.invalidateQueries({ queryKey: ["assinatura"] }), cliente.invalidateQueries({ queryKey: ["assinatura", "faturas"] })]);
    },
  });

  return (
    <section className="wl-panel" aria-label="Forma de pagamento">
      <h2 className="mb-2 text-heading">Forma de pagamento</h2>
      <p className={`mb-4 text-body ${TEXTO_DO_TOM[forma.situacao.tom] ?? "text-ink-muted"}`}>{forma.situacao.rotulo}</p>

      <div className="grid gap-2 md:grid-cols-3 md:gap-3" role="group" aria-label="Escolher a forma de pagamento">
        {OPCOES_DE_FORMA.map((o) => {
          const emUso = forma.forma === o.valor;
          return (
            <button
              key={o.valor}
              type="button"
              disabled={!pode || escolher.isPending}
              aria-pressed={emUso}
              onClick={() => escolher.mutate(o.valor)}
              className={`flex min-h-[56px] flex-col items-start gap-0.5 rounded-lg p-4 text-left disabled:opacity-60 ${emUso ? "bg-surface-sunken ring-2 ring-line-strong" : "border border-line bg-surface"}`}
            >
              <span className="text-body font-medium">{o.rotulo}</span>
              <span className="text-caption text-ink-muted">
                <span className="md:hidden">{o.curto}</span>
                <span className="hidden md:inline">{o.texto}</span>
              </span>
              {emUso && <span className="text-caption font-medium">Em uso</span>}
            </button>
          );
        })}
      </div>

      {aviso && (
        <p role="status" className="mt-3 text-caption text-ink-muted">
          {aviso}
        </p>
      )}
      {escolher.isError && (
        <p role="alert" className="mt-3 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(escolher.error)}
        </p>
      )}

      {passo?.tipo === "autorizar_pix" && passo.pix_copia_e_cola && (
        <Dialogo
          aberto
          aoFechar={() => setPasso(null)}
          titulo="Autorize o Pix automático"
          descricao={passo.expira_em ? `Abra o app do seu banco e use o Pix copia e cola. Vale até ${dataHoraCurta(passo.expira_em)}.` : "Abra o app do seu banco e use o Pix copia e cola."}
          acoes={
            <Button variante="solido" onClick={() => setPasso(null)}>
              Fechar
            </Button>
          }
        >
          <CodigoDePagamento rotulo="Pix copia e cola" codigo={passo.pix_copia_e_cola} comQr />
          <p className="mt-3 text-caption text-ink-muted">Depois que o banco confirmar, a situação muda para ativa.</p>
        </Dialogo>
      )}

      {passo?.tipo === "pagina_parceiro" && passo.url && (
        <Dialogo
          aberto
          aoFechar={() => setPasso(null)}
          titulo="Cadastre o cartão"
          descricao="Você digita o cartão na página do nosso parceiro de pagamento, nunca aqui. Ao terminar, volte para esta tela."
          acoes={
            <>
              <Button variante="quieto" onClick={() => setPasso(null)}>
                Agora não
              </Button>
              <Button variante="solido" onClick={() => window.location.assign(passo.url ?? "/admin/assinatura")}>
                Ir para a página do cartão
              </Button>
            </>
          }
        >
          <p className="text-body">{passo.fatura ? `A cobrança da ${passo.fatura} abre na página do parceiro.` : "Você cadastra o cartão ao pagar a primeira fatura."}</p>
        </Dialogo>
      )}
    </section>
  );
}
