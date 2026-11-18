// TODO(landing): fora da página por decisão do dono (T-490) até haver depoimentos reais, com nome, cidade e
// autorização de uso. Fica no código para voltar em Landing.tsx.
export function QuemUsa() {
  return (
    <section id="clientes">
      <div className="wrap">
        <div className="head">
          <p className="over">Quem usa</p>
          <h2 className="h2">Locadoras que já saíram do caderno.</h2>
        </div>
        {/* TODO(landing): depoimentos reais, com nome, cidade e autorização de uso. Não inventar. */}
        <div className="todo">
          <span className="wl-badge wl-badge--sm">A preencher</span>
          <p>Depoimentos reais de locadoras, com nome, cidade e autorização de uso.</p>
        </div>
      </div>
    </section>
  );
}
