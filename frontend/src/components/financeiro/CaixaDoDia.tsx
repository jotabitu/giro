"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone, KpiGrid, KpiTile, Panel, SegmentedControl, StatusBadge, TextField } from "@/design-system";
import { caixaAberto, financeiro, type Caixa, type MovimentoDoCaixa } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { useFilial } from "@/lib/filial-escolhida";
import { dinheiro, horaCurta } from "@/lib/formatos";
import { diaDaSemanaEData, ROTULO_STATUS_DO_CAIXA, rotuloDaForma, TOM_STATUS_DO_CAIXA } from "@/lib/financeiro";
import { centavosDoTexto } from "@/lib/veiculos";
import { Confirmacao, ErroDoFinanceiro, LinhasDeValor } from "./Comuns";
import { ReceberNoCaixa } from "./ReceberNoCaixa";

// Referência: docs/telas/html/Caixa-Desktop.dc.html e Caixa-Mobile.dc.html.
// O resumo, a gaveta, a diferença e o status vêm da API (FIN-07, APR-04); a tela só mostra.

type Filtro = "todos" | "entradas" | "saidas";
const FILTROS = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "entradas", rotulo: "Entradas" },
  { valor: "saidas", rotulo: "Saídas" },
] as const;

const emReais = (centavos: number) => (centavos / 100).toFixed(2).replace(".", ",");

function Abrir({ aoConcluir }: { aoConcluir: () => void }) {
  const [troco, setTroco] = useState("");
  const centavos = centavosDoTexto(troco);
  const abrir = useMutation({ mutationFn: () => financeiro.abrirCaixa(centavos ?? 0), onSuccess: aoConcluir });
  return (
    <Panel titulo="Abrir o caixa de hoje" subtitulo="Informe o troco que está na gaveta. O caixa fica aberto até você fechar.">
      <form
        className="flex max-w-[420px] flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (centavos !== null) abrir.mutate();
        }}
      >
        <TextField cheio rotulo="Troco na gaveta (R$)" inputMode="decimal" placeholder="200,00" value={troco} onChange={(e) => setTroco(e.target.value)} erro={troco !== "" && centavos === null ? "Informe um valor, como 200,00" : campoDoErro(abrir.error, "troco_centavos")} />
        {abrir.isError && !campoDoErro(abrir.error, "troco_centavos") && <ErroDoFinanceiro erro={abrir.error} />}
        <div>
          <Button type="submit" variante="solido" disabled={centavos === null || abrir.isPending}>
            {abrir.isPending ? "Abrindo…" : "Abrir caixa"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function Sangria({ caixa, aoFechar, aoConcluir }: { caixa: Caixa; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const [valor, setValor] = useState("");
  const [descricao, setDescricao] = useState("");
  const centavos = centavosDoTexto(valor);
  const sangrar = useMutation({
    mutationFn: () => financeiro.sangria(caixa.id, { valor_centavos: centavos ?? 0, descricao: descricao.trim() }),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["caixa"] });
      aoConcluir(`Sangria de ${dinheiro(centavos ?? 0)} registrada.`);
      aoFechar();
    },
  });
  const campos = ["valor_centavos", "descricao"];
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Sangria"
      descricao={`Dinheiro que sai da gaveta, como um depósito no banco. Deve ter na gaveta: ${dinheiro(caixa.resumo.gaveta.esperado_centavos)}.`}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={centavos === null || descricao.trim() === "" || sangrar.isPending} onClick={() => sangrar.mutate()}>
            {sangrar.isPending ? "Registrando…" : "Registrar sangria"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField cheio data-autofocus rotulo="Valor (R$)" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} erro={valor !== "" && centavos === null ? "Informe um valor, como 500,00" : campoDoErro(sangrar.error, "valor_centavos")} />
        <TextField cheio rotulo="Descrição" placeholder="Depósito no banco" value={descricao} onChange={(e) => setDescricao(e.target.value)} erro={campoDoErro(sangrar.error, "descricao")} />
        {sangrar.isError && !campos.some((c) => campoDoErro(sangrar.error, c)) && <ErroDoFinanceiro erro={sangrar.error} />}
      </div>
    </Dialogo>
  );
}

function Fechar({ caixa, aoFechar, aoConcluir }: { caixa: Caixa; aoFechar: () => void; aoConcluir: (m: string) => void }) {
  const cliente = useQueryClient();
  const [contado, setContado] = useState("");
  const [motivo, setMotivo] = useState("");
  const centavos = centavosDoTexto(contado);
  const fechar = useMutation({
    mutationFn: () => financeiro.fecharCaixa(caixa.id, { contado_centavos: centavos ?? 0, motivo_diferenca: motivo.trim() || null }),
    onSuccess: async (r) => {
      await cliente.invalidateQueries({ queryKey: ["caixa"] });
      aoConcluir(r.status === "aguardando_aprovacao" ? "Fechamento enviado ao gerente. O caixa fecha quando ele aprovar a diferença." : "Caixa fechado.");
      aoFechar();
    },
  });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Fechar caixa"
      descricao="Conte o dinheiro da gaveta. Se der diferença, o sistema pede o motivo e avisa o gerente."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={centavos === null || fechar.isPending} onClick={() => fechar.mutate()}>
            {fechar.isPending ? "Fechando…" : "Fechar caixa"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="rounded-md bg-surface-sunken px-4 py-1">
          <LinhasDeValor linhas={[{ rotulo: "Deve ter na gaveta", valor: dinheiro(caixa.resumo.gaveta.esperado_centavos), forte: true }]} />
        </div>
        <TextField cheio data-autofocus rotulo="Dinheiro contado (R$)" inputMode="decimal" placeholder={emReais(caixa.resumo.gaveta.esperado_centavos)} value={contado} onChange={(e) => setContado(e.target.value)} erro={contado !== "" && centavos === null ? "Informe um valor, como 281,00" : campoDoErro(fechar.error, "contado_centavos")} />
        <TextField cheio rotulo="Motivo da diferença, se houver" value={motivo} onChange={(e) => setMotivo(e.target.value)} erro={campoDoErro(fechar.error, "motivo_diferenca")} />
        {fechar.isError && !["contado_centavos", "motivo_diferenca"].some((c) => campoDoErro(fechar.error, c)) && <ErroDoFinanceiro erro={fechar.error} />}
      </div>
    </Dialogo>
  );
}

function Movimentos({ caixaId }: { caixaId: number }) {
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const consulta = useQuery({ queryKey: ["caixa", "movimentos", caixaId], queryFn: () => financeiro.movimentos(caixaId) });
  const todos = consulta.data?.resultados ?? [];
  // Entradas e saídas (inclui sangria) só separam o que a API já classificou por `tipo`.
  const linhas = todos.filter((m) => (filtro === "entradas" ? m.tipo === "entrada" : filtro === "saidas" ? m.tipo !== "entrada" : true));
  const sinal = (m: MovimentoDoCaixa) => (m.tipo === "entrada" ? "" : "− ");

  return (
    <Panel
      titulo="Movimentos"
      acao={
        <div className="hidden md:block">
          <SegmentedControl rotulo="Filtro" opcoes={FILTROS} valor={filtro} aoMudar={setFiltro} />
        </div>
      }
    >
      <div className="mb-3 md:hidden">
        <SegmentedControl rotulo="Filtro" opcoes={FILTROS} valor={filtro} aoMudar={setFiltro} />
      </div>
      {consulta.isPending && <p className="text-body text-ink-muted" aria-busy="true">Carregando os movimentos…</p>}
      {consulta.isError && <p role="alert" className="text-body">{mensagemDoErro(consulta.error)}</p>}
      {consulta.data && linhas.length === 0 && <p className="py-4 text-body text-ink-muted">Nenhum movimento ainda. Os recebimentos de hoje aparecem aqui.</p>}
      {linhas.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="wl-table" aria-label="Movimentos do caixa">
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Forma</th>
                  <th>Descrição</th>
                  <th style={{ textAlign: "right" }}>Valor</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <span className="wl-mono">{horaCurta(m.hora)}</span>
                    </td>
                    <td>
                      <StatusBadge tom="neutro" compacto>
                        {rotuloDaForma(m.forma)}
                      </StatusBadge>
                    </td>
                    <td>{m.tipo === "sangria" ? `Sangria · ${m.descricao}` : m.descricao}</td>
                    <td style={{ textAlign: "right", fontWeight: 500 }}>
                      {sinal(m)}
                      {dinheiro(m.valor_centavos)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="md:hidden" aria-label="Movimentos do caixa">
            {linhas.map((m) => (
              <li key={m.id} className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
                <span className="min-w-0">
                  <span className="wl-mono">{horaCurta(m.hora)}</span> · {m.tipo === "sangria" ? `Sangria · ${m.descricao}` : m.descricao}
                </span>
                <span className={`shrink-0 font-medium ${m.tipo === "entrada" ? "" : "text-critical-ink"}`}>
                  {sinal(m)}
                  {dinheiro(m.valor_centavos)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}

function Gaveta({ caixa }: { caixa: Caixa }) {
  const g = caixa.resumo.gaveta;
  return (
    <Panel titulo="Gaveta">
      <LinhasDeValor
        linhas={[
          { rotulo: "Abertura (troco)", valor: dinheiro(g.troco_centavos) },
          { rotulo: "Entradas em dinheiro", valor: dinheiro(g.entradas_dinheiro_centavos) },
          { rotulo: "Saídas em dinheiro", valor: `− ${dinheiro(g.saidas_dinheiro_centavos)}` },
          { rotulo: "Deve ter na gaveta", valor: dinheiro(g.esperado_centavos), forte: true },
        ]}
      />
      {caixa.status === "aberto" && <p className="mt-3 text-caption text-ink-muted">No fechamento você conta o dinheiro. Se der diferença, o sistema pede o motivo e avisa o gerente.</p>}
    </Panel>
  );
}

/** O que aconteceu com um caixa que já não está aberto: aguardando o gerente, fechado ou fechado sozinho às 23:59. */
function SituacaoDoFechamento({ caixa }: { caixa: Caixa }) {
  const f = caixa.fechamento;
  if (caixa.status === "aberto") return null;
  const diferenca = f?.diferenca_centavos ?? null;
  const texto =
    caixa.status === "aguardando_aprovacao"
      ? `Fechamento aguardando a aprovação do gerente${diferenca ? ` · diferença de ${diferenca < 0 ? "− " : "+ "}${dinheiro(Math.abs(diferenca))}` : ""}${f?.motivo_diferenca ? ` · ${f.motivo_diferenca}` : ""}.`
      : caixa.status === "fechado_sem_conferencia"
        ? "Fechado automaticamente às 23:59, sem conferência do dinheiro. O gerente da filial foi avisado."
        : `Caixa fechado${f?.fechado_por ? ` por ${f.fechado_por.nome}` : ""}${f?.fechado_em ? ` às ${horaCurta(f.fechado_em)}` : ""}${f?.contado_centavos != null ? ` · contado ${dinheiro(f.contado_centavos)}` : ""}${diferenca ? ` · diferença de ${diferenca < 0 ? "− " : "+ "}${dinheiro(Math.abs(diferenca))}` : ""}.`;
  return (
    <p role="status" className="rounded-lg bg-surface-sunken px-4 py-3 text-body">
      {texto}
    </p>
  );
}

/** Caixa do dia da filial: resumo, movimentos, gaveta, recebimento e fechamento. */
export function CaixaDoDia() {
  const cliente = useQueryClient();
  // O caixa é de uma filial só: com "Todas as filiais" a API não soma caixas, então a tela pede a escolha (CA-023-16).
  const todas = useFilial()?.todas ?? false;
  const consulta = useQuery({ queryKey: ["caixa", "hoje"], queryFn: () => financeiro.caixaDeHoje(), enabled: !todas });
  const [dialogo, setDialogo] = useState<"sangria" | "fechar" | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const r = consulta.data;
  const caixa = r && caixaAberto(r) ? r : null;
  const atualizar = () => cliente.invalidateQueries({ queryKey: ["caixa"] });

  if (todas)
    return (
      <div className="flex flex-col gap-6">
        <header>
          <h1 className="text-title md:text-display">Caixa do dia</h1>
          <p className="mt-1 text-body text-ink-muted">O caixa é de uma filial. Escolha uma filial no menu para abrir, receber ou ver os movimentos.</p>
        </header>
      </div>
    );
  if (consulta.isPending)
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando o caixa…
      </p>
    );
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );

  if (!caixa)
    return (
      <div className="flex flex-col gap-6">
        <header>
          <h1 className="text-title md:text-display">Caixa do dia</h1>
          <p className="mt-1 text-body text-ink-muted">O caixa de hoje ainda não foi aberto. Abra o caixa do dia para receber.</p>
        </header>
        {aviso && <Confirmacao>{aviso}</Confirmacao>}
        {r && "pode_abrir" in r && !r.pode_abrir ? <p className="text-body text-ink-muted">Você não pode abrir o caixa desta filial.</p> : <Abrir aoConcluir={() => void atualizar()} />}
      </div>
    );

  const resumo = caixa.resumo;
  const p = resumo.por_forma;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-title md:text-display">Caixa do dia</h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 text-body text-ink-muted">
            <span>
              {diaDaSemanaEData(caixa.data)} · {caixa.filial.nome} · aberto por {caixa.aberto_por.nome} às {horaCurta(caixa.aberto_em)}
            </span>
            <StatusBadge tom={TOM_STATUS_DO_CAIXA[caixa.status]} compacto>
              {ROTULO_STATUS_DO_CAIXA[caixa.status]}
            </StatusBadge>
          </p>
        </div>
        {(caixa.acoes.sangria || caixa.acoes.fechar) && (
          <div className="order-last grid w-full grid-cols-2 gap-2 md:order-none md:flex md:w-auto">
            {caixa.acoes.sangria && (
              <Button icone={<Icone de={Wallet} />} onClick={() => setDialogo("sangria")}>
                Sangria
              </Button>
            )}
            {caixa.acoes.fechar && (
              <Button variante="solido" onClick={() => setDialogo("fechar")}>
                Fechar caixa
              </Button>
            )}
          </div>
        )}
      </header>

      {aviso && <Confirmacao>{aviso}</Confirmacao>}
      <SituacaoDoFechamento caixa={caixa} />

      <div className="hidden md:block">
        <KpiGrid>
          <KpiTile destaque rotulo="Entrou hoje" valor={dinheiro(resumo.entrou_hoje_centavos)} contexto={`${resumo.recebimentos} ${resumo.recebimentos === 1 ? "recebimento" : "recebimentos"}`} />
          <KpiTile rotulo="Pix" valor={dinheiro(p.pix.centavos)} contexto={p.pix.texto ?? `${p.pix.quantidade} ${p.pix.quantidade === 1 ? "recebimento" : "recebimentos"}`} />
          <KpiTile rotulo="Cartão" valor={dinheiro(p.cartao.centavos)} contexto={p.cartao.texto ?? `${p.cartao.quantidade} ${p.cartao.quantidade === 1 ? "recebimento" : "recebimentos"}`} />
          <KpiTile rotulo="Dinheiro na gaveta" valor={dinheiro(resumo.gaveta.esperado_centavos)} contexto={p.dinheiro.texto ?? "confere no fechamento"} />
        </KpiGrid>
      </div>
      <section className="rounded-xl bg-solid p-5 text-on-solid md:hidden" aria-label="Entrou hoje">
        <span className="block text-caption text-on-solid-muted">Entrou hoje</span>
        <span className="block text-display">{dinheiro(resumo.entrou_hoje_centavos)}</span>
        <span className="block text-caption text-on-solid-muted">
          Pix {dinheiro(p.pix.centavos)} · Cartão {dinheiro(p.cartao.centavos)} · Dinheiro {dinheiro(p.dinheiro.centavos)}
        </span>
      </section>

      <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
        <div className="order-2 xl:order-none xl:col-start-1 xl:row-span-2 xl:row-start-1">
          <Movimentos caixaId={caixa.id} />
        </div>
        <div className="order-1 xl:order-none xl:col-start-2 xl:row-start-1">{caixa.acoes.receber ? <ReceberNoCaixa /> : null}</div>
        <div className="order-3 xl:order-none xl:col-start-2 xl:row-start-2">
          <Gaveta caixa={caixa} />
        </div>
      </div>

      {dialogo === "sangria" && <Sangria caixa={caixa} aoFechar={() => setDialogo(null)} aoConcluir={setAviso} />}
      {dialogo === "fechar" && <Fechar caixa={caixa} aoFechar={() => setDialogo(null)} aoConcluir={setAviso} />}
    </div>
  );
}
