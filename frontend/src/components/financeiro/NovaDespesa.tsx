"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Icone, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { financeiro, veiculos, type Despesa, type Eu, type Veiculo } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { corpoDaDespesa, TAMANHO_MAXIMO_DA_NOTA, type ValoresDaDespesa } from "@/lib/despesas";
import { campoDoErro } from "@/lib/erros";
import { CATEGORIAS_DA_DESPESA } from "@/lib/financeiro";
import { diaDe, placa } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";
import { ErroDoFinanceiro } from "./Comuns";

// Referência: painel "Nova despesa" de docs/telas/html/Despesas-Desktop.dc.html e card de Despesas-Mobile.dc.html.

const CAMPOS_COM_ERRO = ["descricao", "valor_centavos", "data", "vencimento", "categoria", "veiculo_id", "nota", "pago_no_caixa"];

/** Veículo pela placa: digitou três letras ou mais, escolhe na lista. A API guarda o id, não a placa. */
function CampoVeiculo({ escolhido, aoEscolher, erro }: { escolhido: Veiculo | null; aoEscolher: (v: Veiculo | null) => void; erro?: string }) {
  const [texto, setTexto] = useState("");
  const [busca, setBusca] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setBusca(texto.replace(/[\s-]/g, "").toUpperCase()), 250);
    return () => clearTimeout(t);
  }, [texto]);
  const achados = useQuery({ queryKey: ["veiculos", "busca-despesa", busca], queryFn: () => veiculos.listar({ busca }), enabled: !escolhido && busca.length >= 3 });
  const lista = achados.data?.resultados.slice(0, 5) ?? [];

  if (escolhido)
    return (
      <div className="flex flex-col gap-1">
        <span className="wl-field__label">Veículo (opcional)</span>
        <div className="flex min-h-[44px] items-center justify-between gap-3 rounded-md bg-surface-sunken px-4">
          <span className="min-w-0 truncate text-body">
            <span className="wl-mono">{placa(escolhido.placa)}</span> · {escolhido.modelo}
          </span>
          <Button compacto variante="quieto" onClick={() => aoEscolher(null)}>
            Tirar
          </Button>
        </div>
      </div>
    );

  return (
    <div className="flex flex-col gap-2">
      <TextField cheio mono rotulo="Veículo (opcional)" placeholder="Placa" autoComplete="off" value={texto} onChange={(e) => setTexto(e.target.value)} erro={erro} />
      {busca.length >= 3 && achados.isSuccess && lista.length === 0 && <p className="text-caption text-ink-muted">Nenhum veículo com essa placa.</p>}
      {lista.length > 0 && (
        <ul className="flex flex-col gap-1" aria-label="Veículos encontrados">
          {lista.map((v) => (
            <li key={v.id}>
              <button
                type="button"
                onClick={() => {
                  aoEscolher(v);
                  setTexto("");
                }}
                className="flex min-h-[44px] w-full items-center gap-2 rounded-md bg-surface-sunken px-4 text-left text-body"
              >
                <span className="wl-mono">{placa(v.placa)}</span>
                <span className="min-w-0 truncate text-ink-muted">{v.modelo}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Lançar despesa. Até R$ 500 nasce a pagar; acima disso vai para o gerente aprovar (FIN-05, APR-03): quem decide é a API. */
export function NovaDespesa({ eu, aoLancar }: { eu: Eu; aoLancar: (d: Despesa) => void }) {
  const cliente = useQueryClient();
  const agora = useAgora();
  const hoje = diaDe(agora.toISOString());
  const soManutencao = eu.pode.despesas_lancar === "manutencao";
  const categorias = soManutencao ? CATEGORIAS_DA_DESPESA.filter((c) => c.valor === "manutencao") : CATEGORIAS_DA_DESPESA;

  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  const [data, setData] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [categoria, setCategoria] = useState<ValoresDaDespesa["categoria"]>("manutencao");
  const [veiculo, setVeiculo] = useState<Veiculo | null>(null);
  const [nota, setNota] = useState<File | null>(null);
  const [erroDaNota, setErroDaNota] = useState<string | null>(null);
  const [pagoNoCaixa, setPagoNoCaixa] = useState(false);
  const arquivo = useRef<HTMLInputElement>(null);

  const dia = data || hoje;
  const valores: ValoresDaDespesa = { descricao, valor, data: dia, vencimento: vencimento || dia, categoria, veiculoId: veiculo?.id ?? null, nota, pagoNoCaixa };
  const corpo = corpoDaDespesa(valores);

  const lancar = useMutation({
    mutationFn: () => {
      if (!corpo) throw new Error("incompleto");
      return financeiro.lancarDespesa(corpo);
    },
    onSuccess: async (d) => {
      setDescricao("");
      setValor("");
      setData("");
      setVencimento("");
      setVeiculo(null);
      setNota(null);
      setPagoNoCaixa(false);
      if (arquivo.current) arquivo.current.value = "";
      await Promise.all([cliente.invalidateQueries({ queryKey: ["despesas"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
      aoLancar(d);
    },
  });

  function escolherNota(f: File | null) {
    if (f && f.size > TAMANHO_MAXIMO_DA_NOTA) {
      setErroDaNota("A nota pode ter até 10 MB. Escolha um arquivo menor.");
      setNota(null);
      if (arquivo.current) arquivo.current.value = "";
      return;
    }
    setErroDaNota(null);
    setNota(f);
  }

  const erroDeCampo = CAMPOS_COM_ERRO.some((c) => campoDoErro(lancar.error, c));
  const valorInvalido = valor !== "" && centavosDoTexto(valor) === null;

  return (
    <form
      className="flex flex-col gap-[14px]"
      onSubmit={(e) => {
        e.preventDefault();
        if (corpo && !lancar.isPending) lancar.mutate();
      }}
    >
      <TextField cheio rotulo="Descrição" placeholder="Ex.: troca de pneu" value={descricao} onChange={(e) => setDescricao(e.target.value)} erro={campoDoErro(lancar.error, "descricao")} />
      <div className="grid grid-cols-2 gap-[10px]">
        <TextField
          cheio
          rotulo="Valor"
          inputMode="decimal"
          placeholder="R$ 0,00"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          erro={valorInvalido ? "Informe um valor, como 150,00" : campoDoErro(lancar.error, "valor_centavos")}
        />
        <TextField cheio rotulo="Data" type="date" value={dia} onChange={(e) => setData(e.target.value)} erro={campoDoErro(lancar.error, "data")} />
      </div>
      <CampoSelecao
        rotulo="Categoria"
        value={categoria}
        onChange={(e) => setCategoria(e.target.value as ValoresDaDespesa["categoria"])}
        opcoes={categorias.map((c) => ({ valor: c.valor, rotulo: c.rotulo }))}
        erro={campoDoErro(lancar.error, "categoria")}
      />
      {/* A API pede o vencimento e a tela de referência não tem o campo: ele nasce igual à data (decisão em aberto no quadro). */}
      <TextField cheio rotulo="Vencimento" type="date" value={vencimento || dia} onChange={(e) => setVencimento(e.target.value)} erro={campoDoErro(lancar.error, "vencimento")} />
      <CampoVeiculo escolhido={veiculo} aoEscolher={setVeiculo} erro={campoDoErro(lancar.error, "veiculo_id")} />

      <div className="flex flex-col gap-1">
        <label className="flex h-[72px] cursor-pointer items-center justify-center gap-2 rounded-[18px] border-[1.5px] border-dashed border-line px-4 text-caption text-ink-muted has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2">
          <Icone de={Camera} />
          <span className="min-w-0 truncate">{nota ? nota.name : "Foto da nota (obrigatória)"}</span>
          <input ref={arquivo} type="file" accept="image/*,application/pdf" className="sr-only" aria-label="Foto da nota" aria-required="true" required onChange={(e) => escolherNota(e.target.files?.[0] ?? null)} />
        </label>
        {nota && (
          <button
            type="button"
            className="min-h-[44px] self-start text-caption underline"
            onClick={() => {
              escolherNota(null);
              if (arquivo.current) arquivo.current.value = "";
            }}
          >
            Tirar a nota
          </button>
        )}
        {(erroDaNota || campoDoErro(lancar.error, "nota")) && (
          <span role="alert" className="text-caption text-critical-ink">
            {erroDaNota ?? campoDoErro(lancar.error, "nota")}
          </span>
        )}
      </div>

      {eu.pode.caixa_abrir_fechar && (
        <label className="flex min-h-[44px] items-center gap-3 text-body">
          <input type="checkbox" checked={pagoNoCaixa} onChange={(e) => setPagoNoCaixa(e.target.checked)} className="size-5 accent-[var(--solid)]" />
          Já paguei em dinheiro, pelo caixa
        </label>
      )}

      {lancar.isError && !erroDeCampo && <ErroDoFinanceiro erro={lancar.error} />}
      <Button type="submit" variante="solido" disabled={!corpo || lancar.isPending}>
        <span className="mx-auto">{lancar.isPending ? "Lançando…" : "Lançar despesa"}</span>
      </Button>
      <p className="m-0 text-caption leading-[18px] text-ink-muted">
        Acima de R$ 500 vai para o gerente aprovar antes de pagar.
        {soManutencao && " Seu perfil lança só despesas de manutenção."}
      </p>
    </form>
  );
}
