"use client";

import { cx } from "../../cx";

export type SegmentoFrota = {
  chave: string;
  rotulo: string;
  contagem: number;
  /** Um único segmento em marca (o que gera receita) e um em solid (fim do ciclo); os demais ficam neutros. */
  destaque?: "marca" | "solido";
};

export function FleetBar({
  titulo = "Frota por status",
  nota,
  segmentos,
  selecionado,
  aoSelecionar,
}: {
  titulo?: string;
  /** Total e contexto, já formatados: "86 veículos · ocupação de 71%". */
  nota?: string;
  /** Na ordem do ciclo: Disponível, Alugado, Reservado, Manutenção, À venda. */
  segmentos: ReadonlyArray<SegmentoFrota>;
  /** Chave do segmento que filtra a lista abaixo. */
  selecionado?: string;
  aoSelecionar?: (chave: string) => void;
}) {
  return (
    <div className="wl-pipe">
      <div className="wl-pipe__head">
        <span className="wl-pipe__title">{titulo}</span>
        {nota && <span className="wl-pipe__note">{nota}</span>}
      </div>
      <div className="wl-pipe__row">
        {segmentos.map((s) => {
          const classe = cx("wl-pipe__col", s.destaque === "marca" && "wl-pipe__col--brand", s.destaque === "solido" && "wl-pipe__col--solid");
          const corpo = (
            <>
              <div className="wl-pipe__bar" />
              <div className="wl-pipe__num">{s.contagem}</div>
              <div className="wl-pipe__label">{s.rotulo}</div>
            </>
          );
          return aoSelecionar ? (
            <button
              key={s.chave}
              type="button"
              className={classe}
              style={{ flex: s.contagem }}
              aria-pressed={s.chave === selecionado}
              onClick={() => aoSelecionar(s.chave)}
            >
              {corpo}
            </button>
          ) : (
            <div key={s.chave} className={classe} style={{ flex: s.contagem }}>
              {corpo}
            </div>
          );
        })}
      </div>
    </div>
  );
}
