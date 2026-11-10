"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Icone, Panel } from "@/design-system";
import type { VeiculoDetalhe } from "@/lib/api";
import { VisualizadorDeFotos } from "./VisualizadorDeFotos";

// VEI-10, CA-414-10, 13. Referência: Veiculo-Desktop|Mobile, "Galeria de fotos". A galeria do cadastro e as fotos da
// vistoria são origens separadas: aqui só a galeria (`galeria`), na ordem da API (capa primeiro).

function Grade({ v }: { v: VeiculoDetalhe }) {
  const cliente = useQueryClient();
  const [aberta, setAberta] = useState<number | null>(null);
  const { fotos, total } = v.galeria;
  return (
    <>
      <ul className="grid grid-cols-3 gap-2 md:grid-cols-4">
        {fotos.map((f, i) => (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => setAberta(i)}
              aria-label={`Ampliar a foto ${f.numero} de ${total}${f.capa ? ", capa" : ""}`}
              className="relative block h-[96px] w-full overflow-hidden rounded-md bg-surface-sunken"
            >
              {f.url ? (
                // A URL é assinada e vale 15 minutos (AUD-05): só enquanto a ficha está aberta.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={f.url} alt="" className="size-full object-cover" />
              ) : (
                <span aria-hidden="true" className="absolute inset-0 grid place-items-center text-ink-muted opacity-[.55]">
                  <Icone de={Camera} className="size-[18px]" />
                </span>
              )}
              {f.capa && <span className="absolute left-2 top-2 rounded-pill bg-surface px-2 py-[2px] text-[12px] font-medium">Capa</span>}
            </button>
          </li>
        ))}
      </ul>
      <VisualizadorDeFotos
        aberto={aberta !== null}
        aoFechar={() => setAberta(null)}
        origem={`Galeria do veículo · ${v.placa}`}
        legenda={(f, _i, t) => `Foto ${f.numero} de ${t}${"capa" in f && f.capa ? " · capa" : ""}`}
        fotos={fotos}
        inicial={aberta ?? 0}
        aoAtualizarLinks={() => void cliente.invalidateQueries({ queryKey: ["veiculo", v.id] })}
      />
    </>
  );
}

function Conteudo({ v }: { v: VeiculoDetalhe }) {
  const editar = v.acoes.editar_fotos;
  if (v.galeria.fotos.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2">
        <p className="text-body text-ink-muted">Nenhuma foto do veículo.</p>
        {editar && (
          <Link href={`/veiculos/${v.id}/editar`} className="wl-btn wl-btn--sm no-underline">
            Adicionar fotos
          </Link>
        )}
      </div>
    );
  }
  return <Grade v={v} />;
}

function Gerenciar({ v }: { v: VeiculoDetalhe }) {
  if (!v.acoes.editar_fotos || v.galeria.fotos.length === 0) return null;
  return (
    <Link href={`/veiculos/${v.id}/editar`} className="wl-btn wl-btn--sm no-underline">
      Gerenciar fotos
    </Link>
  );
}

/** Desktop: painel "Galeria de fotos" com a contagem. */
export function GaleriaNaFicha({ v }: { v: VeiculoDetalhe }) {
  return (
    <Panel titulo="Galeria de fotos" subtitulo={`${v.galeria.total} de ${v.galeria.limite} fotos`} acao={<Gerenciar v={v} />}>
      <Conteudo v={v} />
    </Panel>
  );
}

/** Celular: cartão da ficha, com o mesmo conteúdo. */
export function GaleriaNaFichaCelular({ v }: { v: VeiculoDetalhe }) {
  return (
    <section className="rounded-lg bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-heading">Galeria de fotos</h2>
        <span className="text-[13px] text-ink-muted">
          {v.galeria.total} de {v.galeria.limite}
        </span>
      </div>
      <Conteudo v={v} />
      <div className="mt-3">
        <Gerenciar v={v} />
      </div>
    </section>
  );
}
