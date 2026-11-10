"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone } from "@/design-system";
import { Confirmacao } from "@/components/financeiro/Comuns";
import { CartaoDaDespesa } from "@/components/financeiro/ListaDespesas";
import { DetalheDaDespesa } from "@/components/financeiro/DetalheDaDespesa";
import { NovaDespesa } from "@/components/financeiro/NovaDespesa";
import { Paginacao } from "@/components/lista/Paginacao";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { financeiro, type Despesa, type VeiculoDetalhe } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { diaDe, dinheiro } from "@/lib/formatos";
import { mensagemDoErro } from "@/lib/erros";
import { rotuloDaCategoria } from "@/lib/financeiro";
import { useSessao } from "@/lib/sessao";

// FIN-17 (T-417). Sem tela de referência própria: a seção usa o painel da ficha e as linhas da tela Despesas.
// A lista e o total vêm da API; a tela não soma nada. A lista só aparece quando a ficha traz `indicadores_financeiros`
// (administrador, gerente e financeiro); o "Lançar despesa" segue `acoes.lancar_despesa`.

const ANOS_PARA_TRAS = 4;

/** A linha diz a filial só quando a despesa é de outra que a do veículo (veículo transferido, VEI-04). */
const origemNaFicha = (d: Despesa, v: VeiculoDetalhe) => [rotuloDaCategoria(d.categoria), d.filial.id !== v.filial.id ? d.filial.nome : null].filter(Boolean).join(" · ");

function ListaDoAno({ v, aoAbrir }: { v: VeiculoDetalhe; aoAbrir: (d: Despesa) => void }) {
  const anoDeHoje = Number(diaDe(useAgora().toISOString()).slice(0, 4));
  const [ano, setAno] = useState(anoDeHoje);
  const [cursor, setCursor] = useState<string | null>(null);
  const consulta = useQuery({
    queryKey: ["despesas", "veiculo", v.id, { ano, cursor }],
    queryFn: () => financeiro.despesasDoVeiculo(v.id, { ano, cursor: cursor ?? undefined }),
    placeholderData: (anterior) => anterior,
  });
  const d = consulta.data;
  const anos = Array.from({ length: ANOS_PARA_TRAS + 1 }, (_, i) => String(anoDeHoje - i));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="w-[140px]">
          <CampoSelecao
            rotulo="Ano"
            value={String(ano)}
            onChange={(e) => {
              setAno(Number(e.target.value));
              setCursor(null);
            }}
            opcoes={anos.map((a) => ({ valor: a, rotulo: a }))}
          />
        </div>
        {d && (
          <p className="m-0 text-right text-body">
            <span className="block text-caption text-ink-muted">Despesas no ano</span>
            <span className="text-heading">{dinheiro(d.total_ano_centavos)}</span>
          </p>
        )}
      </div>
      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as despesas…
        </p>
      )}
      {d && d.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhuma despesa deste veículo em {ano}.</p>}
      {d && d.resultados.length > 0 && (
        <>
          <div className="flex flex-col" aria-label={`Despesas do veículo em ${ano}`}>
            {d.resultados.map((x) => (
              <CartaoDaDespesa key={x.id} d={x} origem={origemNaFicha(x, v)} aoAbrir={aoAbrir} />
            ))}
          </div>
          {(d.proximo !== null || d.anterior !== null) && <Paginacao texto={`Mostrando ${d.resultados.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={setCursor} />}
        </>
      )}
    </div>
  );
}

/** A seção "Despesas do veículo" da ficha, no desktop (painel) e no celular (cartão). */
export function DespesasDoVeiculo({ v, celular = false }: { v: VeiculoDetalhe; celular?: boolean }) {
  const { eu } = useSessao();
  const veLista = v.indicadores_financeiros !== undefined;
  const podeLancar = v.acoes.lancar_despesa === true;
  const [lancando, setLancando] = useState(false);
  const [detalhe, setDetalhe] = useState<Despesa | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  if (!veLista && !podeLancar) return null;

  const botao = podeLancar && (
    // "quieto" (wl-btn--quiet, fundo sunken): o mesmo das ações em cartão branco da ficha, como "Ver o histórico".
    <Button variante="quieto" compacto={!celular} onClick={() => setLancando(true)} icone={<Icone de={Plus} />}>
      Lançar despesa
    </Button>
  );

  // Sem a lista (vendedor e vistoriador), fica só o botão, sem espaço para ela (CA-417-09, CA-417-12).
  const corpo = (
    <>
      {aviso && (
        <div className="mt-3">
          <Confirmacao>{aviso}</Confirmacao>
        </div>
      )}
      {veLista && (
        <div className="mt-3">
          <ListaDoAno v={v} aoAbrir={setDetalhe} />
        </div>
      )}
    </>
  );

  return (
    <>
      {celular ? (
        <section className="rounded-lg bg-surface p-4" aria-label="Despesas do veículo">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-heading">Despesas do veículo</h2>
          </div>
          {corpo}
          {botao && <div className="mt-3 grid">{botao}</div>}
        </section>
      ) : (
        <section className="wl-panel" aria-label="Despesas do veículo">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-[20px] font-semibold leading-[26px]">Despesas do veículo</h2>
            {botao}
          </div>
          {corpo}
        </section>
      )}

      {lancando && (
        <Dialogo aberto aoFechar={() => setLancando(false)} fecharAoClicarFora={false} titulo="Lançar despesa" descricao={`${v.marca} ${v.modelo} · ${v.filial.nome}`}>
          <NovaDespesa
            eu={eu}
            veiculoFixo={v}
            aoLancar={(nova) => {
              setLancando(false);
              setAviso(nova.status === "aguardando_aprovacao" ? `Despesa de ${dinheiro(nova.valor_centavos)} enviada ao gerente para aprovar antes de pagar.` : "Despesa lançada.");
            }}
          />
        </Dialogo>
      )}
      {/* A despesa pode ser de outra filial que a escolhida no topo: o detalhe usa a linha que veio da lista (FIN-17). */}
      {detalhe && <DetalheDaDespesa id={detalhe.id} inicial={detalhe} semReler eu={eu} aoFechar={() => setDetalhe(null)} aoConcluir={setAviso} />}
    </>
  );
}
