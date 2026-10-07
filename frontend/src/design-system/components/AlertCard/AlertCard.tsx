import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Icone } from "../../Icone";

export type ItemAlerta = {
  /** Frase completa com número ("3 devoluções estão atrasadas"). A cor do ponto só reforça. */
  texto: string;
  gravidade?: "critica" | "atencao";
};

/** Único card escuro da tela (solid; no tema escuro ele inverte e fica claro). */
export function AlertCard({
  cabecalho = "Pendências do dia",
  atualizadoHa,
  titulo,
  itens,
  acao,
}: {
  cabecalho?: string;
  /** "há 6 min", em mono à direita. */
  atualizadoHa?: string;
  /** Diz o número e a ação: "7 contratos precisam de ação hoje". */
  titulo: string;
  /** Até quatro itens. */
  itens: ReadonlyArray<ItemAlerta>;
  /** Normalmente <Button variante="marca">. */
  acao?: ReactNode;
}) {
  return (
    <section className="wl-alert-card">
      <div className="wl-alert-card__head">
        <Icone de={TriangleAlert} />
        {cabecalho}
        {atualizadoHa && <span className="wl-alert-card__time">{atualizadoHa}</span>}
      </div>
      <h3 className="wl-alert-card__title">{titulo}</h3>
      <ul>
        {itens.slice(0, 4).map((item) => (
          <li key={item.texto} className={item.gravidade === "critica" ? "is-critical" : item.gravidade === "atencao" ? "is-warning" : undefined}>
            {item.texto}
          </li>
        ))}
      </ul>
      {acao}
    </section>
  );
}
