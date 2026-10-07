/**
 * Capa do design system: faixa de painéis desiguais nas cores dos tokens (marca, solid, surface, warning)
 * sobre o canvas. Serve de abertura da página de preview; troca com o tema e com a marca da empresa.
 */
export function Cover({
  titulo = "Design System White Label",
  descricao = "Painéis claros, pílulas pretas e a cor de cada cliente para gestão de motos e carros.",
}: {
  titulo?: string;
  descricao?: string;
}) {
  return (
    <div className="wl-cover">
      <div className="wl-cover__band" aria-hidden="true">
        <svg viewBox="0 0 960 120" preserveAspectRatio="xMidYMin slice" width="100%" height="100%">
          <rect fill="var(--brand)" x="24" y="-32" width="352" height="136" rx="24" />
          <rect fill="var(--solid)" x="392" y="24" width="208" height="80" rx="24" />
          <rect fill="var(--surface)" x="616" y="-24" width="368" height="128" rx="24" />
          <rect fill="var(--solid)" x="48" y="40" width="136" height="40" rx="20" />
          <rect fill="var(--solid)" x="200" y="40" width="88" height="40" rx="20" />
          <rect fill="var(--surface)" x="304" y="40" width="40" height="40" rx="20" />
          <rect fill="var(--brand)" x="416" y="44" width="112" height="40" rx="20" />
          <rect fill="var(--surface)" x="544" y="44" width="40" height="40" rx="20" />
          <rect fill="var(--canvas)" x="640" y="16" width="296" height="40" rx="20" />
          <rect fill="var(--warning)" x="640" y="68" width="96" height="24" rx="12" />
          <rect fill="var(--solid)" x="752" y="68" width="72" height="24" rx="12" />
        </svg>
      </div>
      <div className="wl-cover__words">
        <h1 className="wl-cover__name">{titulo}</h1>
        <p className="wl-cover__tag">{descricao}</p>
      </div>
    </div>
  );
}
