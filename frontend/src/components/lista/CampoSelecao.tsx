import { useId, type SelectHTMLAttributes } from "react";

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "className" | "id"> & {
  rotulo: string;
  erro?: string;
  dica?: string;
  opcoes: { valor: string; rotulo: string }[];
  /** Texto da opção vazia; sem ele, o campo não tem opção em branco. */
  vazio?: string;
};

/** Campo de escolha com o visual dos campos do design system (que ainda não tem um select). */
export function CampoSelecao({ rotulo, erro, dica, opcoes, vazio, ...resto }: Props) {
  const id = useId();
  const apoio = erro ?? dica;
  return (
    <div className={`wl-field wl-field--cheio ${erro ? "wl-field--error" : ""}`}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <select id={id} className="wl-input" aria-invalid={erro ? true : undefined} {...resto}>
        {vazio !== undefined && <option value="">{vazio}</option>}
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </div>
  );
}
