export type LinhaDeValor = { rotulo: string; valor: string };

/** Lista de rótulo e valor com linha fina entre as linhas: o resumo da venda. O valor vem formatado da API. */
export function Valores({ linhas }: { linhas: LinhaDeValor[] }) {
  return (
    <div>
      {linhas.map((l) => (
        <div key={l.rotulo} className="wl-kv">
          <span>{l.rotulo}</span>
          <span>{l.valor}</span>
        </div>
      ))}
    </div>
  );
}
