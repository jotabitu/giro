import { useId, type SelectHTMLAttributes } from "react";
import { cx } from "../../cx";

export type OpcaoSelect = { valor: string; rotulo: string };

export type SelectFieldProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "className" | "id"> & {
  rotulo: string;
  opcoes: OpcaoSelect[];
  /** Texto da opção em branco ("Escolha a categoria"); sem ele, o campo não tem opção vazia. */
  vazio?: string;
  /** Dica curta. */
  dica?: string;
  /** Diz o problema e como resolver; troca a dica e pinta a borda de critical. */
  erro?: string;
  /** Ocupa a largura do contêiner em vez dos 280px padrão. */
  cheio?: boolean;
  /** Esconde o rótulo só da vista (continua para o leitor de tela). Use em linha de lista, onde o título da linha já diz o que é. */
  rotuloOculto?: boolean;
};

export function SelectField({ rotulo, opcoes, vazio, dica, erro, cheio, rotuloOculto, ...resto }: SelectFieldProps) {
  const id = useId();
  const apoio = erro ?? dica;
  return (
    <div className={cx("wl-field", erro && "wl-field--error", cheio && "wl-field--cheio")}>
      <label className={cx("wl-field__label", rotuloOculto && "wl-sr-only")} htmlFor={id}>
        {rotulo}
      </label>
      <select
        id={id}
        className="wl-input"
        aria-invalid={erro ? true : undefined}
        aria-describedby={apoio ? `${id}-dica` : undefined}
        {...resto}
      >
        {vazio !== undefined && <option value="">{vazio}</option>}
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
      {apoio && (
        <span id={`${id}-dica`} className="wl-field__hint">
          {apoio}
        </span>
      )}
    </div>
  );
}
