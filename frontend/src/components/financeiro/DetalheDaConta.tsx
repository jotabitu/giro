"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone, StatusBadge, TextField } from "@/design-system";
import { financeiro, type CobrancaDaConta } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dataHoraCurta, dinheiro } from "@/lib/formatos";
import { composicaoDoValor, linhaDaConta, origemDaConta, rotuloDaForma, situacaoDaConta, textoDoEvento } from "@/lib/financeiro";
import { ErroDoFinanceiro, LinhasDeValor } from "./Comuns";

type Motivo = "cancelar" | "estornar" | null;

export function PixGerado({ cobranca }: { cobranca: CobrancaDaConta }) {
  const [copiado, setCopiado] = useState(false);
  const codigo = cobranca.pix_copia_e_cola ?? cobranca.linha_digitavel;
  if (!codigo) return null;
  return (
    <div className="flex flex-col gap-2 rounded-md bg-surface-sunken p-4">
      <span className="text-caption text-ink-muted">
        {cobranca.tipo === "pix" ? "Pix copia e cola" : "Linha digitável do boleto"} · {dinheiro(cobranca.valor_centavos)} · vence {dataCompleta(cobranca.vence_em)}
      </span>
      <code className="wl-mono break-all text-caption">{codigo}</code>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          compacto
          icone={<Icone de={Copy} />}
          onClick={() => {
            void navigator.clipboard?.writeText(codigo).then(() => setCopiado(true));
          }}
        >
          Copiar
        </Button>
        {copiado && <span role="status" className="text-caption text-ink-muted">Copiado.</span>}
        {cobranca.boleto_url && (
          <a href={cobranca.boleto_url} target="_blank" rel="noreferrer" className="wl-btn wl-btn--sm">
            Abrir boleto
          </a>
        )}
      </div>
    </div>
  );
}

/** Detalhe de uma conta: valor do dia, cobrança aberta, histórico e as ações que a API liberou (`acoes`). */
export function DetalheDaConta({ id, aoFechar, aoDarBaixa, aoConcluir }: { id: number; aoFechar: () => void; aoDarBaixa: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["contas-receber", "detalhe", id], queryFn: () => financeiro.obterConta(id) });
  const [motivoPara, setMotivoPara] = useState<Motivo>(null);
  const [motivo, setMotivo] = useState("");
  const [gerada, setGerada] = useState<CobrancaDaConta | null>(null);
  const c = consulta.data;

  const depois = async (mensagem?: string) => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["contas-receber"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
    if (mensagem) {
      aoConcluir(mensagem);
      aoFechar();
    }
  };
  const gerar = useMutation({ mutationFn: (tipo: "pix" | "boleto") => financeiro.gerarCobranca(id, { tipo }), onSuccess: (cobranca) => (setGerada(cobranca), depois()) });
  const confirmar = useMutation({
    mutationFn: () => (motivoPara === "cancelar" ? financeiro.cancelarConta(id, motivo.trim()) : financeiro.estornarConta(id, motivo.trim())),
    onSuccess: () => depois(motivoPara === "cancelar" ? "Conta cancelada." : "Pagamento estornado. Nasceu uma conta em aberto no lugar."),
  });

  const aberta = gerada ?? c?.cobranca_aberta ?? null;
  const situacao = c ? situacaoDaConta(c) : null;
  const v = c?.valor_hoje;
  const paga = c?.status === "paga";

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={motivoPara === null}
      titulo={c ? `${c.cliente.nome} · ${origemDaConta(c)}` : "Conta a receber"}
      descricao={c ? linhaDaConta(c) : undefined}
      acoes={
        motivoPara ? (
          <>
            <Button variante="quieto" onClick={() => (setMotivoPara(null), setMotivo(""))}>
              Voltar
            </Button>
            <Button variante="solido" disabled={confirmar.isPending} onClick={() => confirmar.mutate()}>
              {motivoPara === "cancelar" ? "Cancelar a conta" : "Estornar o pagamento"}
            </Button>
          </>
        ) : (
          <>
            <Button variante="quieto" onClick={aoFechar}>
              Fechar
            </Button>
            {c?.acoes.receber && (
              <Button variante="solido" onClick={aoDarBaixa}>
                Dar baixa
              </Button>
            )}
          </>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {consulta.isPending && <p className="text-body text-ink-muted" aria-busy="true">Carregando a conta…</p>}
        {consulta.isError && <p role="alert" className="text-body">{mensagemDoErro(consulta.error)}</p>}
        {c && v && situacao && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tom={situacao.tom} compacto>
                {situacao.rotulo}
              </StatusBadge>
              <span className="text-caption text-ink-muted">
                {paga ? `Paga em ${dataCompleta(c.pago_em ?? c.vencimento)} · ${rotuloDaForma(c.forma)}` : `Forma prevista: ${rotuloDaForma(c.forma_prevista)}`}
              </span>
            </div>
            {c.observacao && <p className="text-body text-ink-muted">{c.observacao}</p>}
            <div className="rounded-md bg-surface-sunken px-4 py-1">
              <LinhasDeValor
                linhas={
                  paga
                    ? [
                        { rotulo: "Valor da parcela", valor: dinheiro(c.valor_centavos) },
                        ...(c.multa_centavos > 0 ? [{ rotulo: "Multa", valor: dinheiro(c.multa_centavos) }] : []),
                        ...(c.juros_centavos > 0 ? [{ rotulo: "Juros", valor: dinheiro(c.juros_centavos) }] : []),
                      ]
                    : [
                        { rotulo: "Valor hoje", valor: dinheiro(v.total_centavos), forte: true },
                        { rotulo: "Composição", valor: composicaoDoValor(v) },
                      ]
                }
              />
            </div>

            {aberta && <PixGerado cobranca={aberta} />}
            {!paga && (c.acoes.gerar_pix || c.acoes.gerar_boleto) && (
              <div className="flex flex-wrap gap-2">
                {c.acoes.gerar_pix && (
                  <Button compacto disabled={gerar.isPending} onClick={() => gerar.mutate("pix")}>
                    Gerar Pix
                  </Button>
                )}
                {c.acoes.gerar_boleto && (
                  <Button compacto disabled={gerar.isPending} onClick={() => gerar.mutate("boleto")}>
                    Gerar boleto
                  </Button>
                )}
              </div>
            )}
            {gerar.isError && <ErroDoFinanceiro erro={gerar.error} />}

            {motivoPara ? (
              <div className="flex flex-col gap-3">
                <TextField
                  cheio
                  data-autofocus
                  rotulo={motivoPara === "cancelar" ? "Motivo do cancelamento" : "Motivo do estorno"}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  erro={campoDoErro(confirmar.error, "motivo")}
                />
                {confirmar.isError && !campoDoErro(confirmar.error, "motivo") && <ErroDoFinanceiro erro={confirmar.error} />}
              </div>
            ) : (
              (c.acoes.cancelar || c.acoes.estornar) && (
                <div className="flex flex-wrap gap-2">
                  {c.acoes.cancelar && (
                    <Button compacto variante="quieto" onClick={() => setMotivoPara("cancelar")}>
                      Cancelar conta
                    </Button>
                  )}
                  {c.acoes.estornar && (
                    <Button compacto variante="quieto" onClick={() => setMotivoPara("estornar")}>
                      Estornar pagamento
                    </Button>
                  )}
                </div>
              )
            )}

            {c.historico.length > 0 && (
              <section aria-label="Histórico">
                <h3 className="text-body-strong mb-1">Histórico</h3>
                <ul className="flex flex-col">
                  {c.historico.map((h, i) => (
                    <li key={`${h.em}-${i}`} className="flex flex-col gap-0.5 border-b border-line py-2 text-body last:border-b-0">
                      <span>{textoDoEvento(h.acao)}</span>
                      <span className="text-caption text-ink-muted">
                        {dataHoraCurta(h.em)} · {h.por ?? "Sistema"}
                        {h.motivo ? ` · ${h.motivo}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </Dialogo>
  );
}
