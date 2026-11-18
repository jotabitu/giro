import { LINK_TESTE_GRATIS } from "./links";
import { LogoGiro } from "./Logo";

export function Nav() {
  return (
    <header className="nav dark">
      <div className="wrap">
        <a href="#topo" className="logo" aria-label="Giro, página inicial">
          <LogoGiro />
        </a>
        <nav aria-label="Principal">
          <ul>
            <li><a className="ulink" href="#como-funciona">Como funciona</a></li>
            <li><a className="ulink" href="#modulos">Módulos</a></li>
            <li><a className="ulink" href="#white-label">White label</a></li>
            <li><a className="ulink" href="#planos">Planos</a></li>
            <li><a className="ulink" href="#perguntas">Perguntas</a></li>
          </ul>
        </nav>
        <a className="wl-btn wl-btn--brand wl-btn--sm" href={LINK_TESTE_GRATIS}>Começar teste grátis</a>
      </div>
    </header>
  );
}
