"use client";

import { useQuery } from "@tanstack/react-query";
import { useDeferredValue } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";
import { CampoComSugestoes } from "@/design-system";
import { veiculos, type ModeloDoCatalogo, type TipoVeiculo } from "@/lib/api";

const chaveDe = (m: { marca: string; modelo: string }) => `${m.marca}|${m.modelo}`;

/**
 * O campo Modelo do cadastro e do editar (VEI-08, T-521): a lista FIPE de `GET /api/veiculos/modelos/` no `CampoComSugestoes`
 * do design system, e, depois da leitura do CRLV-e com várias versões, as versões logo abaixo para trocar, com a escolhida marcada.
 * Quem escolhe a versão que preenche é a API (`dicas.escolhido`); a tela só mostra. Digitar livre continua valendo.
 */
export function CampoDoModelo({
  tipo,
  marca,
  modelo,
  registro,
  dica,
  erro,
  versoes,
  aoEscolher,
}: {
  tipo: TipoVeiculo;
  marca: string;
  modelo: string;
  registro: UseFormRegisterReturn<"modelo">;
  /** A dica do formulário ("Lido do documento" enquanto o valor é o lido); sem ela, a dica da lista FIPE. */
  dica: (padrao: string) => string | undefined;
  erro?: string;
  /** As versões que a leitura achou (`dicas.candidatos`); com uma só ou nenhuma, não aparecem. */
  versoes: ReadonlyArray<ModeloDoCatalogo>;
  aoEscolher: (m: ModeloDoCatalogo) => void;
}) {
  const marcaAdiada = useDeferredValue(marca);
  const modeloAdiado = useDeferredValue(modelo);
  const filtro = { tipo, marca: marcaAdiada.trim(), busca: modeloAdiado.trim() };
  const modelos = useQuery({ queryKey: ["modelos", filtro], queryFn: () => veiculos.modelos(filtro), placeholderData: (anterior) => anterior });
  const lista = modelos.data ?? [];
  const daLista = lista.some((m) => m.modelo.toLowerCase() === modelo.trim().toLowerCase());
  const atual = chaveDe({ marca, modelo });

  return (
    <div className="flex min-w-0 flex-col gap-2">
      <CampoComSugestoes
        cheio
        rotulo="Modelo"
        rotuloDaLista="Da lista FIPE"
        dica={dica(daLista ? "Da lista FIPE" : "Escolha da lista ou digite")}
        erro={erro}
        opcoes={lista.map((m) => ({ valor: m.modelo, apoio: m.marca, chave: chaveDe(m) }))}
        escolhida={atual}
        aoEscolher={(o) => {
          const m = lista.find((x) => chaveDe(x) === o.chave);
          if (m) aoEscolher(m);
        }}
        {...registro}
      />
      {versoes.length > 1 && (
        <ul aria-label="Versões que batem com o documento" className="m-0 flex list-none flex-col gap-2 p-0">
          {versoes.map((c) => {
            const escolhida = chaveDe(c) === atual;
            return (
              <li key={chaveDe(c)}>
                <button type="button" aria-pressed={escolhida} onClick={() => aoEscolher(c)} className={`wl-btn min-h-[44px] w-full justify-start text-left ${escolhida ? "wl-btn--solid" : "wl-btn--quiet"}`}>
                  {c.modelo}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
