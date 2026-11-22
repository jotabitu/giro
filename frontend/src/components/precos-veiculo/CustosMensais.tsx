"use client";

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button, Dialogo, Gaveta } from "@/design-system";
import { ErroApi, veiculos, type CustosDoVeiculo, type PrecosDoVeiculo } from "@/lib/api";
import { useAtrasado } from "@/lib/atrasado";
import { aparelhoAtual, mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { custosParaCorpo, custosParaRascunho, errosDaApi, textoDaOcupacao, type CustosRascunho } from "@/lib/precos-veiculo";

// Referência: "Modal 'Editar custos mensais'" (desktop) e a gaveta de baixo (celular) de Veiculo-Precos-*.dc.html.
// O "Custos por mês" é o que a API devolve no `simular`; a tela não soma nem divide o IPVA.

function Campo({ rotulo, dica, erro, valor, aoMudar, id }: { rotulo: string; dica?: string; erro?: string; valor: string; aoMudar: (v: string) => void; id: string }) {
  const apoio = erro ?? dica;
  return (
    <div className={`wl-field wl-field--cheio ${erro ? "wl-field--error" : ""}`}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <input id={id} className="wl-input" inputMode="decimal" autoComplete="off" value={valor} aria-invalid={erro ? true : undefined} onChange={(e) => aoMudar(e.target.value)} />
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </div>
  );
}

function Formulario({ veiculoId, atual, ocupacaoReal, aoSalvar, aoFechar }: { veiculoId: number; atual: CustosDoVeiculo; ocupacaoReal: string; aoSalvar: (d: PrecosDoVeiculo) => void; aoFechar: () => void }) {
  const [r, setR] = useState<CustosRascunho>(() => custosParaRascunho(atual));
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const montado = useMemo(() => custosParaCorpo(r, atual), [r, atual]);
  const semErro = Object.keys(montado.erros).length === 0;
  const chave = useAtrasado(semErro ? JSON.stringify(montado.custos) : null);
  const simulado = useQuery({
    queryKey: ["veiculo-precos-custos", veiculoId, chave],
    queryFn: () => veiculos.simularPrecos(veiculoId, { custos: JSON.parse(chave as string), confirmar_juros: false }),
    enabled: chave !== null,
    placeholderData: keepPreviousData,
    retry: false,
  });
  const custoMes = simulado.data?.custos?.custo_mes_centavos ?? atual.custo_mes_centavos;

  const salvar = useMutation({ mutationFn: () => veiculos.salvarPrecos(veiculoId, { custos: montado.custos, confirmar_juros: false }) });
  async function enviar() {
    setErroGeral(null);
    if (!semErro) return setErros(montado.erros);
    try {
      const resposta = await salvar.mutateAsync();
      aoSalvar(resposta);
      aoFechar();
    } catch (e) {
      if (e instanceof ErroApi && e.campos) setErros(errosDaApi(e.campos, []));
      else setErroGeral(mensagemDoErro(e));
    }
  }
  const campo = (nome: keyof CustosRascunho) => (v: string) => {
    setR((x) => ({ ...x, [nome]: v }));
    setErros({});
  };

  return (
    <>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Campo id="c-manutencao" rotulo="Manutenção por mês" valor={r.manutencao} aoMudar={campo("manutencao")} erro={erros["custos.manutencao_mes_centavos"]} />
        <Campo id="c-seguro" rotulo="Seguro por mês" valor={r.seguro} aoMudar={campo("seguro")} erro={erros["custos.seguro_mes_centavos"]} />
        <Campo id="c-ipva" rotulo="IPVA do ano" valor={r.ipvaAno} aoMudar={campo("ipvaAno")} erro={erros["custos.ipva_ano_centavos"]} dica={`Entra como ${dinheiro(simulado.data?.custos?.ipva_mes_centavos ?? atual.ipva_mes_centavos)} por mês no custo`} />
        <Campo id="c-rastreador" rotulo="Rastreador por mês" valor={r.rastreador} aoMudar={campo("rastreador")} erro={erros["custos.rastreador_mes_centavos"]} />
      </div>
      <Campo id="c-ocupacao" rotulo="Ocupação esperada" valor={r.ocupacao} aoMudar={campo("ocupacao")} erro={erros["custos.ocupacao_esperada_pct"]} dica={`Frota nos últimos 90 dias: ${textoDaOcupacao(ocupacaoReal)}`} />
      <div className="flex justify-between gap-3 border-b border-line py-[9px] text-[14px]">
        <span className="text-ink-muted">Custos por mês</span>
        <span className="font-medium">{dinheiro(custoMes)}</span>
      </div>
      {erroGeral && (
        <p role="alert" className="text-body text-critical-ink">
          {erroGeral}
        </p>
      )}
      <div className="flex flex-col-reverse gap-3 md:flex-row md:justify-end">
        <Button variante="quieto" onClick={aoFechar}>
          Cancelar
        </Button>
        <Button variante="solido" disabled={salvar.isPending} onClick={() => void enviar()}>
          Salvar custos
        </Button>
      </div>
    </>
  );
}

export function CustosMensais({ aberto, aoFechar, veiculoId, atual, ocupacaoReal, aoSalvar }: { aberto: boolean; aoFechar: () => void; veiculoId: number; atual: CustosDoVeiculo; ocupacaoReal: string; aoSalvar: (d: PrecosDoVeiculo) => void }) {
  const descricao = "Base das margens desta moto. O IPVA se digita pelo valor do ano e entra dividido por 12.";
  // O formulário só existe com a caixa aberta: cada abertura começa dos valores gravados.
  const corpo = aberto ? <Formulario veiculoId={veiculoId} atual={atual} ocupacaoReal={ocupacaoReal} aoSalvar={aoSalvar} aoFechar={aoFechar} /> : null;
  return aparelhoAtual() === "celular" ? (
    <Gaveta lado="baixo" aberto={aberto} aoFechar={aoFechar} titulo="Custos mensais" descricao={descricao}>
      <div className="flex flex-col gap-3">{corpo}</div>
    </Gaveta>
  ) : (
    <Dialogo aberto={aberto} aoFechar={aoFechar} titulo="Custos mensais" descricao={descricao}>
      <div className="flex flex-col gap-3">{corpo}</div>
    </Dialogo>
  );
}
