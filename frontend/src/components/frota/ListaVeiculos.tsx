"use client";

import { useQuery } from "@tanstack/react-query";
import { Bike, Car } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CelulaDupla, DataTable, Icone, SearchField, SegmentedControl, StatusBadge, type ColunaTabela } from "@/design-system";
import { FiltroChips, type OpcaoChip } from "@/components/lista/FiltroChips";
import { Paginacao } from "@/components/lista/Paginacao";
import { veiculos, type ListaVeiculos as Lista, type TipoVeiculo, type Veiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, km, placa } from "@/lib/formatos";
import { diaria, fatoDoVeiculo } from "@/lib/frota";
import { useBuscaNaUrl, useFiltrosNaUrl } from "@/lib/filtros-url";
import { tomDoStatus } from "@/lib/tom";
import { useSessao } from "@/lib/sessao";

const STATUS: { valor: string; rotulo: string; chave: keyof Lista["contagens"] }[] = [
  { valor: "todos", rotulo: "Todos", chave: "todos" },
  { valor: "disponivel", rotulo: "Disponível", chave: "disponivel" },
  { valor: "alugado", rotulo: "Alugado", chave: "alugado" },
  { valor: "reservado", rotulo: "Reservado", chave: "reservado" },
  { valor: "em_manutencao", rotulo: "Manutenção", chave: "em_manutencao" },
  { valor: "a_venda", rotulo: "À venda", chave: "a_venda" },
];

function Miniatura({ tipo }: { tipo: TipoVeiculo }) {
  return (
    <span className="grid h-12 w-12 shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted md:h-[52px] md:w-[52px]">
      <Icone de={tipo === "moto" ? Bike : Car} />
    </span>
  );
}

const COLUNAS: ColunaTabela<Veiculo>[] = [
  {
    chave: "veiculo",
    titulo: "Veículo",
    celula: (v) => (
      <span className="flex items-center gap-3">
        <Miniatura tipo={v.tipo_veiculo} />
        <span>
          <CelulaDupla principal={`${v.marca} ${v.modelo}`} secundaria={`${v.ano_modelo} · ${v.cor}`} />
        </span>
      </span>
    ),
  },
  { chave: "placa", titulo: "Placa", mono: true, celula: (v) => placa(v.placa) },
  {
    chave: "situacao",
    titulo: "Situação",
    celula: (v) => (
      <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
        {v.situacao.rotulo}
      </StatusBadge>
    ),
  },
  { chave: "km", titulo: "Quilometragem", mono: true, celula: (v) => km(v.km_atual) },
  { chave: "diaria", titulo: "Diária", mono: true, celula: diaria },
  {
    chave: "revisao",
    titulo: "Próxima revisão",
    mono: true,
    celula: (v) => (v.manutencao?.proxima ? km(v.manutencao.proxima.km) : "—"),
  },
  {
    chave: "contrato",
    titulo: "Contrato",
    celula: (v) =>
      v.locacao_atual ? (
        <CelulaDupla principal={<span className="wl-mono">{v.locacao_atual.codigo}</span>} secundaria={`devolve ${dataCurta(v.locacao_atual.fim_previsto)}`} />
      ) : (
        "—"
      ),
  },
];

function CartaoDoVeiculo({ v }: { v: Veiculo }) {
  const fato = fatoDoVeiculo(v);
  return (
    <Link href={`/veiculos/${v.id}`} className="flex flex-col gap-3 rounded-lg bg-surface p-4 text-ink no-underline">
      <span className="flex items-center gap-3">
        <Miniatura tipo={v.tipo_veiculo} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body font-medium">
            {v.marca} {v.modelo}
          </span>
          <span className="wl-mono block text-caption text-ink-muted">{placa(v.placa)}</span>
        </span>
        <StatusBadge tom={tomDoStatus(v.situacao.tom)} compacto>
          {v.situacao.rotulo}
        </StatusBadge>
      </span>
      <span className="grid grid-cols-3 border-t border-line pt-3 text-body">
        <span>
          <span className="block text-caption text-ink-muted">Km</span>
          {new Intl.NumberFormat("pt-BR").format(v.km_atual)}
        </span>
        <span>
          <span className="block text-caption text-ink-muted">Diária</span>
          {diaria(v)}
        </span>
        <span className="min-w-0">
          <span className="block text-caption text-ink-muted">{fato.rotulo}</span>
          <span className="block truncate">{fato.valor}</span>
        </span>
      </span>
    </Link>
  );
}

/** Frota: lista de veículos com filtro por tipo e situação. Contagens e situação vêm da API. */
export function ListaVeiculos() {
  const router = useRouter();
  const { eu } = useSessao();
  const { valor, definir } = useFiltrosNaUrl();
  const status = valor("status") ?? "todos";
  const tipo = (valor("tipo") ?? "todos") as TipoVeiculo | "todos";
  const cursor = valor("cursor") ?? undefined;
  const buscaNaUrl = valor("busca") ?? "";

  const [busca, setBusca] = useBuscaNaUrl(definir, buscaNaUrl);

  const consulta = useQuery({
    queryKey: ["veiculos", { status, tipo, busca: buscaNaUrl, cursor }],
    queryFn: () => veiculos.listar({ status, tipo_veiculo: tipo === "todos" ? undefined : tipo, busca: buscaNaUrl || undefined, cursor }),
    placeholderData: (anterior) => anterior,
  });
  const d = consulta.data;

  const opcoes: OpcaoChip[] = STATUS.map((s) => ({ valor: s.valor, rotulo: s.rotulo, contagem: d?.contagens[s.chave] }));
  const filial = eu.filiais[0]?.nome;
  const total = d?.contagens[STATUS.find((s) => s.valor === status)?.chave ?? "todos"] ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <h1 className="text-title md:text-display">Veículos</h1>
          {d && (
            <p className="mt-1 text-body text-ink-muted">
              {d.contagens.todos} {d.contagens.todos === 1 ? "veículo" : "veículos"}
              {filial ? ` na ${filial}` : ""} · {d.contagens.motos} motos e {d.contagens.carros} carros
            </p>
          )}
        </div>
        <div className="w-full md:ml-auto md:w-auto">
          <SearchField placeholder="Buscar placa, modelo ou chassi" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
      </header>

      <section className="wl-panel">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <SegmentedControl
            rotulo="Tipo de veículo"
            valor={tipo}
            aoMudar={(v) => definir({ tipo: v === "todos" ? null : v })}
            opcoes={[
              { valor: "todos", rotulo: "Todos" },
              { valor: "moto", rotulo: "Motos" },
              { valor: "carro", rotulo: "Carros" },
            ]}
          />
          <div className="min-w-0 flex-1">
            <FiltroChips rotulo="Situação" opcoes={opcoes} valor={status} aoMudar={(v) => definir({ status: v === "todos" ? null : v })} />
          </div>
        </div>

        {consulta.isError && (
          <p role="alert" className="text-body">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isPending && (
          <p className="text-body text-ink-muted" aria-busy="true">
            Carregando os veículos…
          </p>
        )}
        {d && d.resultados.length === 0 && (
          <p className="py-6 text-center text-body text-ink-muted">Nenhum veículo com esses filtros. Tire um filtro ou mude a busca.</p>
        )}
        {d && d.resultados.length > 0 && (
          <>
            <div className="hidden overflow-x-auto md:block">
              <DataTable colunas={COLUNAS} linhas={d.resultados} chaveDaLinha={(v) => String(v.id)} aoAbrir={(v) => router.push(`/veiculos/${v.id}`)} legenda="Veículos" />
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {d.resultados.map((v) => (
                <CartaoDoVeiculo key={v.id} v={v} />
              ))}
            </div>
            <Paginacao
              texto={`Mostrando ${d.resultados.length} de ${total} veículos`}
              anterior={d.anterior}
              proximo={d.proximo}
              aoIr={(c) => definir({ cursor: c })}
            />
          </>
        )}
      </section>
    </div>
  );
}
