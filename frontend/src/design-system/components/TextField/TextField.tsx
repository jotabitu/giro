import { useId, type InputHTMLAttributes } from "react";
import { cx } from "../../cx";

export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "id"> & {
  rotulo: string;
  /** Dica curta. */
  dica?: string;
  /** Diz o problema e como resolver; troca a dica e pinta a borda de critical. */
  erro?: string;
  /** Placas, códigos e chassi (Geist Mono). */
  mono?: boolean;
  /** Ocupa a largura do contêiner em vez dos 280px padrão. */
  cheio?: boolean;
};

export function TextField({ rotulo, dica, erro, mono, cheio, ...resto }: TextFieldProps) {
  const id = useId();
  const apoio = erro ?? dica;
  return (
    <div className={cx("wl-field", erro && "wl-field--error", cheio && "wl-field--cheio")}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <input
        id={id}
        className={cx("wl-input", mono && "wl-mono")}
        aria-invalid={erro ? true : undefined}
        aria-describedby={apoio ? `${id}-dica` : undefined}
        {...resto}
      />
      {apoio && (
        <span id={`${id}-dica`} className="wl-field__hint">
          {apoio}
        </span>
      )}
    </div>
  );
}
