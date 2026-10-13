"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, Panel, SearchField, StatusBadge } from "@/design-system";
import { financeiro, type CobrancaDaConta, type ContaReceber, type FormaDeRecebimento } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { composicaoDoValor, linhaDaConta, origemDaConta, situacaoDaConta } from "@/lib/financeiro";
import { Confirmacao, EscolhaDeOpcao, ErroDoFinanceiro } from "./Comuns";
import { PixGerado } from "./DetalheDaConta";

type Forma = "pix" | "cartao" | "dinheiro";
type Cartao = Extract<FormaDeRecebimento, "cartao_debito" | "cartao_credito">;

const FORMAS: { valor: Forma; rotulo: string }[] = [
  { valor: "pix", rotulo: "Pix" },
  { valor: "cartao", rotulo: "Cartão" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
];
const CARTOES: { valor: Cartao; rotulo: string }[] = [
  { valor: "cartao_debito", rotulo: "Débito" },
  { valor: "cartao_credito", rotulo: "Crédito" },
];

const EM_ABERTO = new Set(["aberta", "vence_hoje", "atrasada"]);

function Escolha({ conta, aoVoltar }: { conta: ContaReceber; aoVoltar: () => void }) {
  const cliente = useQueryClient();
  const [forma, setForma] = useState<Forma>("pix");
  const [cartao, setCartao] = useState<Cartao>("cartao_debito");
  const [pix, setPix] = useState<CobrancaDaConta | null>(null);
  const [pago, setPago] = useState<string | null>(null);
  const v = conta.valor_hoje;
  const s = situacaoDaConta(conta);

  const atualizar = () => Promise.all([cliente.invalidateQueries({ queryKey: ["caixa"] }), cliente.invalidateQueries({ queryKey: ["contas-receber"] })]);
  const gerar = useMutation({ mutationFn: () => financeiro.gerarCobranca(conta.id, { tipo: "pix", no_caixa: true }), onSuccess: (c) => setPix(c) });
  const receber = useMutation({
    mutationFn: () => financeiro.receber(conta.id, { forma: forma === "cartao" ? cartao : "dinheiro", valor_centavos: v.total_centavos }),
    onSuccess: async () => {
      setPago(`${dinheiro(v.total_centavos)} recebidos de ${conta.cliente.nome}.`);
      await atualizar();
    },
  });

  if (pago)
    return (
      <div className="flex flex-col gap-3">
        <Confirmacao>{pago}</Confirmacao>
        <Button onClick={aoVoltar}>Receber outro pagamento</Button>
      </div>
    );

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg bg-surface-sunken p-4">
        <div className="flex items-start justify-between gap-3 text-body">
          <span>{linhaDaConta(conta)}</span>
          <StatusBadge tom={s.tom} compacto>
            {conta.status === "atrasada" ? "Atrasada" : s.rotulo}
          </StatusBadge>
        </div>
        <div className="mt-1 text-title font-semibold">{dinheiro(v.total_centavos)}</div>
        <div className="mt-1 text-caption text-ink-muted">{composicaoDoValor(v)}</div>
      </div>
      <EscolhaDeOpcao
        rotulo="Forma"
        opcoes={FORMAS}
        valor={forma}
        aoMudar={(f) => {
          setForma(f);
          setPix(null);
        }}
      />
      {forma === "cartao" && <EscolhaDeOpcao rotulo="Cartão" colunas={2} opcoes={CARTOES} valor={cartao} aoMudar={setCartao} />}
      {pix && <PixGerado cobranca={pix} />}
      {forma === "pix" ? (
        <Button variante="solido" disabled={gerar.isPending} onClick={() => gerar.mutate()}>
          {gerar.isPending ? "Gerando…" : pix ? `Gerar outro Pix de ${dinheiro(v.total_centavos)}` : `Gerar Pix de ${dinheiro(v.total_centavos)}`}
        </Button>
      ) : (
        <Button variante="solido" disabled={receber.isPending} onClick={() => receber.mutate()}>
          {receber.isPending ? "Recebendo…" : `Receber ${dinheiro(v.total_centavos)}`}
        </Button>
      )}
      {pix && <p className="text-caption text-ink-muted">Quando o cliente pagar, a conta baixa sozinha e a entrada aparece no caixa.</p>}
      {(gerar.isError || receber.isError) && <ErroDoFinanceiro erro={gerar.error ?? receber.error} />}
      <Button variante="quieto" compacto onClick={aoVoltar}>
        Escolher outra conta
      </Button>
    </div>
  );
}

/** Receber pagamento no caixa: acha a conta pelo cliente ou contrato e recebe o valor do dia que a API calculou. */
export function ReceberNoCaixa() {
  const [texto, setTexto] = useState("");
  const [busca, setBusca] = useState("");
  const [conta, setConta] = useState<ContaReceber | null>(null);
  useEffect(() => {
    const t = setTimeout(() => setBusca(texto.trim()), 300);
    return () => clearTimeout(t);
  }, [texto]);

  const consulta = useQuery({ queryKey: ["contas-receber", "caixa", busca], queryFn: () => financeiro.listarContas({ busca }), enabled: busca.length >= 2 && conta === null });
  const achadas = (consulta.data?.resultados ?? []).filter((c) => EM_ABERTO.has(c.status) && c.acoes.receber);

  return (
    <Panel titulo="Receber pagamento">
      {conta ? (
        <Escolha
          key={conta.id}
          conta={conta}
          aoVoltar={() => {
            setConta(null);
            setTexto("");
          }}
        />
      ) : (
        <div className="flex flex-col gap-3">
          <SearchField placeholder="Cliente, contrato ou placa" aria-label="Buscar a conta a receber" value={texto} onChange={(e) => setTexto(e.target.value)} />
          {busca.length < 2 && <p className="text-caption text-ink-muted">Digite o nome do cliente, o contrato ou a placa.</p>}
          {consulta.isFetching && (
            <p className="text-caption text-ink-muted" aria-busy="true">
              Procurando…
            </p>
          )}
          {consulta.isError && (
            <p role="alert" className="text-body">
              {mensagemDoErro(consulta.error)}
            </p>
          )}
          {consulta.data && achadas.length === 0 && !consulta.isFetching && <p className="text-body text-ink-muted">Nenhuma conta em aberto para essa busca.</p>}
          <ul className="flex flex-col gap-2" aria-label="Contas em aberto">
            {achadas.map((c) => {
              const s = situacaoDaConta(c);
              return (
                <li key={c.id}>
                  <button type="button" onClick={() => setConta(c)} className="flex min-h-[56px] w-full items-center justify-between gap-3 rounded-md bg-surface-sunken px-4 py-2 text-left text-ink">
                    <span className="min-w-0">
                      <span className="block truncate text-body font-medium">{c.cliente.nome}</span>
                      <span className="wl-mono block text-caption text-ink-muted">{origemDaConta(c)}</span>
                    </span>
                    <span className="flex shrink-0 flex-col items-end gap-1">
                      <span className="text-body font-medium">{dinheiro(c.valor_hoje.total_centavos)}</span>
                      <StatusBadge tom={s.tom} compacto>
                        {s.rotulo}
                      </StatusBadge>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Panel>
  );
}
