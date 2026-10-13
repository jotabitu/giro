"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Dialogo, StatusBadge, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { aprovacoes, financeiro, type Despesa, type Eu, type FormaDaDespesa } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { pagoEmDoDia, TAMANHO_MAXIMO_DA_NOTA } from "@/lib/despesas";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { FORMAS_DE_PAGAR_DESPESA, origemDaDespesa, rotuloDaCategoria, TOM_DA_DESPESA } from "@/lib/financeiro";
import { dataCompleta, diaDe, dinheiro, placa } from "@/lib/formatos";
import { ErroDoFinanceiro, LinhasDeValor } from "./Comuns";

type Modo = "ver" | "pagar" | "recusar";

/**
 * Detalhe da despesa: dados, nota e as ações do perfil. Pagar é do administrador e do financeiro (só `a_pagar`);
 * aprovar e recusar são de quem aprova (APR-03) e nunca do próprio pedido (APR-09). A API confere tudo de novo.
 */
export function DetalheDaDespesa({ id, inicial, eu, aoFechar, aoConcluir }: { id: number; inicial?: Despesa; eu: Eu; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const agora = useAgora();
  const consulta = useQuery({ queryKey: ["despesas", "detalhe", id], queryFn: () => financeiro.obterDespesa(id), initialData: inicial });
  const [modo, setModo] = useState<Modo>("ver");
  const [forma, setForma] = useState<FormaDaDespesa>("pix");
  const [dia, setDia] = useState("");
  const [comprovante, setComprovante] = useState<File | null>(null);
  const [erroDoArquivo, setErroDoArquivo] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");
  const arquivo = useRef<HTMLInputElement>(null);
  const d = consulta.data;

  const depois = async (mensagem: string) => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["despesas"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
    aoConcluir(mensagem);
    aoFechar();
  };

  const pagar = useMutation({
    mutationFn: () => financeiro.pagarDespesa(id, { forma, pago_em: pagoEmDoDia(dia || diaDe(agora.toISOString()), agora), comprovante }),
    onSuccess: () => depois("Despesa paga."),
  });
  const aprovar = useMutation({
    mutationFn: () => aprovacoes.aprovar(d?.pedido_aprovacao_id ?? 0),
    onSuccess: () => depois("Despesa aprovada. Ela segue para pagamento."),
  });
  const recusar = useMutation({
    mutationFn: () => aprovacoes.recusar(d?.pedido_aprovacao_id ?? 0, motivo.trim()),
    onSuccess: () => depois("Despesa recusada."),
  });

  const podePagar = d?.status === "a_pagar" && eu.pode.financeiro_pagar;
  const podeDecidir = d?.status === "aguardando_aprovacao" && d.pedido_aprovacao_id !== null && eu.pode.despesas_aprovar && d.lancada_por.id !== eu.id;
  const ocupado = pagar.isPending || aprovar.isPending || recusar.isPending;

  function escolherComprovante(f: File | null) {
    if (f && f.size > TAMANHO_MAXIMO_DA_NOTA) {
      setErroDoArquivo("O comprovante pode ter até 10 MB. Escolha um arquivo menor.");
      setComprovante(null);
      if (arquivo.current) arquivo.current.value = "";
      return;
    }
    setErroDoArquivo(null);
    setComprovante(f);
  }

  const voltar = () => {
    setModo("ver");
    setMotivo("");
  };

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={modo === "ver"}
      titulo={d ? d.descricao : "Despesa"}
      descricao={d ? `${origemDaDespesa(d, eu.filiais)} · lançada em ${dataCompleta(d.data)}` : undefined}
      acoes={
        modo === "pagar" ? (
          <>
            <Button variante="quieto" onClick={voltar}>
              Voltar
            </Button>
            <Button variante="solido" disabled={ocupado} onClick={() => pagar.mutate()}>
              {pagar.isPending ? "Pagando…" : "Confirmar pagamento"}
            </Button>
          </>
        ) : modo === "recusar" ? (
          <>
            <Button variante="quieto" onClick={voltar}>
              Voltar
            </Button>
            <Button variante="solido" disabled={ocupado || motivo.trim() === ""} onClick={() => recusar.mutate()}>
              {recusar.isPending ? "Recusando…" : "Recusar despesa"}
            </Button>
          </>
        ) : (
          <>
            <Button variante="quieto" onClick={aoFechar}>
              Fechar
            </Button>
            {podeDecidir && (
              <Button variante="quieto" onClick={() => setModo("recusar")}>
                Recusar
              </Button>
            )}
            {podeDecidir && (
              <Button variante="solido" disabled={ocupado} onClick={() => aprovar.mutate()}>
                {aprovar.isPending ? "Aprovando…" : "Aprovar"}
              </Button>
            )}
            {podePagar && (
              <Button variante="solido" onClick={() => setModo("pagar")}>
                Pagar
              </Button>
            )}
          </>
        )
      }
    >
      <div className="flex flex-col gap-4">
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando a despesa…
          </p>
        )}
        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {d && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tom={TOM_DA_DESPESA[d.status]} compacto>
                {d.rotulo_situacao}
              </StatusBadge>
              <span className="text-caption text-ink-muted">Lançada por {d.lancada_por.nome}</span>
            </div>
            <div className="rounded-md bg-surface-sunken px-4 py-1">
              <LinhasDeValor
                linhas={[
                  { rotulo: "Valor", valor: dinheiro(d.valor_centavos), forte: true },
                  { rotulo: "Categoria", valor: rotuloDaCategoria(d.categoria) },
                  { rotulo: "Vencimento", valor: dataCompleta(d.vencimento) },
                  ...(d.veiculo ? [{ rotulo: "Veículo", valor: placa(d.veiculo.placa) }] : []),
                  ...(d.pago_em ? [{ rotulo: "Pago em", valor: dataCompleta(d.pago_em) }] : []),
                ]}
              />
            </div>
            {d.nota ? (
              <a href={d.nota.url} target="_blank" rel="noreferrer" className="wl-btn wl-btn--sm self-start">
                Ver a nota
              </a>
            ) : (
              <p className="text-caption text-ink-muted">Sem foto da nota.</p>
            )}

            {modo === "pagar" && (
              <div className="flex flex-col gap-3">
                <CampoSelecao rotulo="Forma de pagamento" value={forma} onChange={(e) => setForma(e.target.value as FormaDaDespesa)} opcoes={FORMAS_DE_PAGAR_DESPESA} erro={campoDoErro(pagar.error, "forma")} />
                <TextField cheio rotulo="Pago em" type="date" value={dia || diaDe(agora.toISOString())} onChange={(e) => setDia(e.target.value)} erro={campoDoErro(pagar.error, "pago_em")} />
                <div className="flex flex-col gap-1">
                  <span className="wl-field__label">Comprovante (opcional)</span>
                  <input ref={arquivo} type="file" accept="image/*,application/pdf" aria-label="Comprovante" onChange={(e) => escolherComprovante(e.target.files?.[0] ?? null)} className="min-h-[44px] text-body" />
                  {(erroDoArquivo || campoDoErro(pagar.error, "comprovante")) && (
                    <span role="alert" className="text-caption text-critical-ink">
                      {erroDoArquivo ?? campoDoErro(pagar.error, "comprovante")}
                    </span>
                  )}
                </div>
                {forma === "dinheiro" && <p className="text-caption text-ink-muted">Em dinheiro, o valor sai do caixa aberto da filial.</p>}
                {pagar.isError && !["forma", "pago_em", "comprovante"].some((c) => campoDoErro(pagar.error, c)) && <ErroDoFinanceiro erro={pagar.error} />}
              </div>
            )}

            {modo === "recusar" && (
              <div className="flex flex-col gap-3">
                <TextField cheio data-autofocus rotulo="Motivo da recusa" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(recusar.error, "motivo")} dica="Quem lançou recebe o motivo." />
                {recusar.isError && !campoDoErro(recusar.error, "motivo") && <ErroDoFinanceiro erro={recusar.error} />}
              </div>
            )}

            {modo === "ver" && aprovar.isError && <ErroDoFinanceiro erro={aprovar.error} />}
          </>
        )}
      </div>
    </Dialogo>
  );
}
