"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { locacoes, veiculos, type FormaDevolucaoCancelamento, type LocacaoCompleta, type SimulacaoDoCancelamento } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCurta, diaDe, dinheiro, placa } from "@/lib/formatos";
import { dataEHora, textoDaEstimativa, textoDoPeriodo } from "@/lib/locacoes";

// Renovar, trocar o veículo e cancelar a locação. Os valores, a multa e as recusas vêm da API (docs/api/locacoes.md).

type Dialogos = "renovar" | "trocar" | "cancelar_troca" | "cancelar" | null;

function Erro({ erro }: { erro: unknown }) {
  return (
    <p role="alert" className="text-body text-critical">
      {mensagemDoErro(erro)}
    </p>
  );
}

function Resumo({ linhas }: { linhas: { rotulo: string; valor: string }[] }) {
  return (
    <dl className="rounded-md bg-surface-sunken px-4 py-1">
      {linhas.map((l) => (
        <div key={l.rotulo} className="flex justify-between gap-3 border-b border-line py-[10px] text-body last:border-b-0">
          <dt className="text-ink-muted">{l.rotulo}</dt>
          <dd className="text-right font-medium">{l.valor}</dd>
        </div>
      ))}
    </dl>
  );
}

function atualizar(cliente: ReturnType<typeof useQueryClient>, id: number) {
  return Promise.all([cliente.invalidateQueries({ queryKey: ["locacao", id] }), cliente.invalidateQueries({ queryKey: ["locacoes"] })]);
}

function Renovar({ l, aoFechar, aoConcluir }: { l: LocacaoCompleta; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const [periodos, setPeriodos] = useState("1");
  const n = Number(periodos);
  const valido = Number.isInteger(n) && n >= 1;
  const simulacao = useQuery({ queryKey: ["locacao", l.id, "renovar", n], queryFn: () => locacoes.simularRenovacao(l.id, { periodos: n }), enabled: valido, retry: false });
  const renovar = useMutation({
    mutationFn: () => locacoes.renovar(l.id, { periodos: n }),
    onSuccess: async () => {
      await atualizar(cliente, l.id);
      aoConcluir(`${l.codigo} renovada por ${textoDoPeriodo(n, l.periodicidade)}.`);
      aoFechar();
    },
  });
  const s = simulacao.data;
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={`Renovar ${l.codigo}`}
      descricao="As parcelas novas seguem o preço de hoje. O aditivo vai para assinatura do cliente."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!s || renovar.isPending} onClick={() => renovar.mutate()}>
            {renovar.isPending ? "Renovando…" : "Renovar"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField
          cheio
          data-autofocus
          rotulo={`Quantas ${l.periodicidade === "diaria" ? "diárias" : l.periodicidade === "semanal" ? "semanas" : "meses"} a mais`}
          type="number"
          inputMode="numeric"
          min={1}
          value={periodos}
          onChange={(e) => setPeriodos(e.target.value)}
          erro={periodos !== "" && !valido ? "Informe 1 ou mais" : (campoDoErro(simulacao.error, "periodos") ?? campoDoErro(renovar.error, "periodos"))}
        />
        {simulacao.isError && !campoDoErro(simulacao.error, "periodos") && <Erro erro={simulacao.error} />}
        {s && (
          <>
            <Resumo
              linhas={[
                { rotulo: "Fim previsto hoje", valor: s.fim_previsto_atual ? dataEHora(s.fim_previsto_atual) : "—" },
                { rotulo: "Novo fim previsto", valor: s.fim_previsto ? dataEHora(s.fim_previsto) : "—" },
                ...s.parcelas_novas.map((p) => ({ rotulo: `Parcela ${p.numero} · vence ${dataCurta(p.vencimento)}`, valor: dinheiro(p.valor_centavos) })),
                { rotulo: "Total a receber", valor: dinheiro(s.total_centavos) },
              ]}
            />
          </>
        )}
        {renovar.isError && <Erro erro={renovar.error} />}
      </div>
    </Dialogo>
  );
}

function Cancelar({ l, aoFechar, aoConcluir }: { l: LocacaoCompleta; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const pedir = l.acoes.cancelar === "pedir";
  const [data, setData] = useState(() => diaDe(new Date().toISOString()));
  const [motivo, setMotivo] = useState("");
  const [forma, setForma] = useState<FormaDevolucaoCancelamento>("pix");
  const simulacao = useQuery<SimulacaoDoCancelamento>({ queryKey: ["locacao", l.id, "cancelamento", data], queryFn: () => locacoes.simularCancelamento(l.id, { data: data || null }), retry: false });
  const s = simulacao.data;
  const cancelar = useMutation({
    mutationFn: () => locacoes.cancelar(l.id, { motivo, data: data || null, forma_devolucao: forma }),
    onSuccess: async (r) => {
      await atualizar(cliente, l.id);
      aoConcluir(r.status === 202 ? "Pedido enviado ao gerente. A locação continua até a decisão." : `${l.codigo} ${s?.antes_da_retirada ? "cancelada" : "com encerramento aprovado. Registre a devolução para fechar a conta"}.`);
      aoFechar();
    },
  });
  const linhas = s
    ? s.antes_da_retirada
      ? [{ rotulo: "Devolvido ao cliente", valor: dinheiro(s.devolver_centavos) }]
      : [
          { rotulo: "Dias restantes", valor: String(s.dias_restantes) },
          { rotulo: "Valor dos dias restantes", valor: dinheiro(s.valor_restante_centavos) },
          { rotulo: "Multa de encerramento", valor: dinheiro(s.multa_centavos) },
          ...(s.credito_semanas.valor_centavos > 0 ? [{ rotulo: `${s.credito_semanas.semanas} semana${s.credito_semanas.semanas === 1 ? "" : "s"} não usada${s.credito_semanas.semanas === 1 ? "" : "s"}`, valor: dinheiro(s.credito_semanas.valor_centavos) }] : []),
          ...(s.devolver_centavos > 0 ? [{ rotulo: "A devolver", valor: dinheiro(s.devolver_centavos) }] : []),
          ...(s.cobrar_centavos > 0 ? [{ rotulo: "A cobrar", valor: dinheiro(s.cobrar_centavos) }] : []),
        ]
    : [];
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo={pedir ? `Pedir cancelamento da ${l.codigo}` : `Cancelar a ${l.codigo}`}
      descricao={pedir ? "O gerente vai analisar o pedido. A locação continua até a decisão." : "A API calcula a multa e o valor a devolver. O que foi pago antes da retirada volta para o cliente."}
      acoes={
        <>
          <Button variante="quieto" data-autofocus onClick={aoFechar}>
            Continuar aqui
          </Button>
          <Button variante="solido" disabled={!motivo.trim() || cancelar.isPending || simulacao.isError} onClick={() => cancelar.mutate()}>
            {cancelar.isPending ? "Enviando…" : pedir ? "Enviar pedido" : "Cancelar locação"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {l.status !== "aguardando_retirada" && <TextField cheio rotulo="Data do encerramento" type="date" value={data} onChange={(e) => setData(e.target.value)} erro={campoDoErro(simulacao.error, "data")} />}
        <TextField cheio rotulo="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(cancelar.error, "motivo")} />
        {s && (s.devolver_centavos > 0 || s.antes_da_retirada) && (
          <CampoSelecao
            rotulo="Forma de devolução"
            value={forma}
            onChange={(e) => setForma(e.target.value as FormaDevolucaoCancelamento)}
            opcoes={[
              { valor: "pix", rotulo: "Pix" },
              { valor: "estorno_cartao", rotulo: "Estorno no cartão" },
            ]}
          />
        )}
        {simulacao.isError && !campoDoErro(simulacao.error, "data") && <Erro erro={simulacao.error} />}
        {s && (
          <>
            <Resumo linhas={linhas} />
            {!s.antes_da_retirada && <p className="text-caption text-ink-muted">{textoDaEstimativa(data)}</p>}
            {s.avisos.map((a) => (
              <p key={a.codigo} className="text-caption text-ink-muted">
                {a.mensagem}
              </p>
            ))}
          </>
        )}
        {cancelar.isError && <Erro erro={cancelar.error} />}
      </div>
    </Dialogo>
  );
}

function Trocar({ l, aoFechar, aoConcluir }: { l: LocacaoCompleta; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const [novo, setNovo] = useState("");
  const [motivo, setMotivo] = useState("");
  const frota = useQuery({ queryKey: ["veiculos", "disponiveis-para-troca"], queryFn: () => veiculos.listar({ status: "disponivel" }) });
  const trocar = useMutation({
    mutationFn: () => locacoes.trocarVeiculo(l.id, { veiculo_novo_id: Number(novo), motivo }),
    onSuccess: async () => {
      await atualizar(cliente, l.id);
      aoConcluir("Troca pedida. Faça a vistoria de chegada do veículo atual e a de saída do novo.");
    },
  });
  if (trocar.isSuccess) {
    return (
      <Dialogo
        aberto
        aoFechar={aoFechar}
        titulo="Troca de veículo pedida"
        descricao="A locação continua no veículo atual até as duas vistorias serem concluídas. O veículo novo ficou reservado."
        acoes={
          <Button variante="solido" onClick={aoFechar}>
            Fechar
          </Button>
        }
      >
        <ul className="flex flex-col gap-3">
          <li>
            <Link href={`/locacoes/${l.id}/devolucao`} className="wl-btn">
              Vistoria de chegada do veículo atual
            </Link>
          </li>
          <li>
            <Link href={`/locacoes/${l.id}/vistoria`} className="wl-btn">
              Vistoria de saída do veículo novo
            </Link>
          </li>
        </ul>
      </Dialogo>
    );
  }
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo={`Trocar o veículo da ${l.codigo}`}
      descricao="O preço e a caução passam a ser os da categoria do veículo novo. O acerto da devolução continua um só."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!novo || !motivo.trim() || trocar.isPending} onClick={() => trocar.mutate()}>
            {trocar.isPending ? "Enviando…" : "Pedir troca"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <CampoSelecao
          rotulo="Veículo novo"
          value={novo}
          onChange={(e) => setNovo(e.target.value)}
          vazio={frota.isPending ? "Carregando…" : "Escolha um veículo disponível"}
          opcoes={(frota.data?.resultados ?? []).map((v) => ({ valor: String(v.id), rotulo: `${v.modelo} · ${placa(v.placa)}` }))}
          erro={frota.isError ? mensagemDoErro(frota.error) : campoDoErro(trocar.error, "veiculo_novo_id")}
        />
        <TextField cheio rotulo="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(trocar.error, "motivo")} />
        {trocar.isError && !campoDoErro(trocar.error, "motivo") && <Erro erro={trocar.error} />}
      </div>
    </Dialogo>
  );
}

function CancelarTroca({ l, aoFechar, aoConcluir }: { l: LocacaoCompleta; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const cancelar = useMutation({
    mutationFn: () => locacoes.cancelarTroca(l.id, { motivo }),
    onSuccess: async () => {
      await Promise.all([atualizar(cliente, l.id), cliente.invalidateQueries({ queryKey: ["veiculos"] }), cliente.invalidateQueries({ queryKey: ["devolucao"] })]);
      aoConcluir(`Troca cancelada. A ${l.codigo} segue com ${l.troca?.veiculo_antigo.modelo ?? "o veículo atual"}.`);
      aoFechar();
    },
  });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo={`Cancelar a troca da ${l.codigo}`}
      descricao="As vistorias da troca são descartadas e o veículo novo volta a ficar disponível. A locação continua com o veículo atual."
      acoes={
        <>
          <Button variante="quieto" data-autofocus onClick={aoFechar}>
            Manter a troca
          </Button>
          <Button variante="solido" disabled={!motivo.trim() || cancelar.isPending} onClick={() => cancelar.mutate()}>
            {cancelar.isPending ? "Cancelando…" : "Cancelar troca"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField cheio rotulo="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(cancelar.error, "motivo")} />
        {cancelar.isError && !campoDoErro(cancelar.error, "motivo") && <Erro erro={cancelar.error} />}
      </div>
    </Dialogo>
  );
}

/** Botões da locação (só o que `acoes` da API permite) e as janelas de cada ação. */
export function AcoesDaLocacao({ l, variante, aoConcluir }: { l: LocacaoCompleta; variante: "desktop" | "celular"; aoConcluir: (mensagem: string) => void }) {
  const [aberto, setAberto] = useState<Dialogos>(null);
  const fechar = () => setAberto(null);
  const a = l.acoes;
  const saida = l.status === "aguardando_retirada" && !l.condicoes.vistoria_saida_ok_em;

  const continuarRascunho = l.status === "rascunho" && (a.editar || a.confirmar) && (
    <Link key="rasc" href={`/locacoes/nova?rascunho=${l.id}`} className="wl-btn wl-btn--solid">
      Continuar a locação
    </Link>
  );
  const devolucao = a.registrar_devolucao && (
    <Link key="dev" href={`/locacoes/${l.id}/devolucao`} className="wl-btn wl-btn--solid">
      Registrar devolução
    </Link>
  );
  const renovar = a.renovar && (
    <Button key="ren" onClick={() => setAberto("renovar")}>
      Renovar
    </Button>
  );
  const vistoria = saida && (
    <Link key="vis" href={`/locacoes/${l.id}/vistoria`} className="wl-btn wl-btn--solid">
      Fazer vistoria de saída
    </Link>
  );
  const continuar = a.continuar_vistoria && (
    <Link key="cont" href={`/locacoes/${l.id}/vistoria`} className="wl-btn wl-btn--solid">
      Continuar vistoria
    </Link>
  );
  const trocar = a.trocar_veiculo && (
    <Button key="tro" variante="quieto" onClick={() => setAberto("trocar")}>
      Trocar veículo
    </Button>
  );
  const cancelarTroca = a.cancelar_troca && (
    <Button key="ctr" variante="quieto" onClick={() => setAberto("cancelar_troca")}>
      Cancelar troca
    </Button>
  );
  const cancelar = a.cancelar && (
    <Button key="can" variante="quieto" onClick={() => setAberto("cancelar")}>
      {a.cancelar === "pedir" ? "Pedir cancelamento" : "Cancelar locação"}
    </Button>
  );

  return (
    <>
      {variante === "desktop" ? (
        <div className="flex flex-wrap items-center gap-2">{[renovar, trocar, cancelarTroca, cancelar, continuarRascunho, vistoria, continuar, devolucao]}</div>
      ) : (
        <div className="flex flex-col gap-2 [&_.wl-btn]:justify-center">
          <div className="flex gap-2 [&>*:first-child]:flex-1 [&>*:last-child]:flex-[2]">{[renovar, continuarRascunho, vistoria, continuar, devolucao]}</div>
          {trocar}
          {cancelarTroca}
          {cancelar}
        </div>
      )}
      {aberto === "renovar" && <Renovar l={l} aoFechar={fechar} aoConcluir={aoConcluir} />}
      {aberto === "cancelar" && <Cancelar l={l} aoFechar={fechar} aoConcluir={aoConcluir} />}
      {aberto === "cancelar_troca" && <CancelarTroca l={l} aoFechar={fechar} aoConcluir={aoConcluir} />}
      {aberto === "trocar" && <Trocar l={l} aoFechar={fechar} aoConcluir={aoConcluir} />}
    </>
  );
}
