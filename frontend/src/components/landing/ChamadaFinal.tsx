import { ArrowRight, MessageCircle } from "lucide-react";
import { Icone } from "@/design-system/Icone";
import { LINK_PRIVACIDADE, LINK_TERMOS, LINK_TESTE_GRATIS, LINK_WHATSAPP } from "./links";
import { LogoGiro } from "./Logo";

export function ChamadaFinal() {
  return (
    <footer className="dark close">
      <div className="wrap">
        <div className="close-grid">
          <h2 className="big">Feche o caderno. Abra o Giro.</h2>
          <p className="lead">14 dias grátis, sem cartão. Cancele quando quiser.</p>
          <div className="actions">
            <a className="wl-btn wl-btn--brand" href={LINK_TESTE_GRATIS}>Começar teste grátis <Icone de={ArrowRight} /></a>
            <a className="wl-btn" href={LINK_WHATSAPP} rel="noopener"><Icone de={MessageCircle} /> Falar com a gente</a>
          </div>
        </div>
        <div className="foot">
          <div style={{ display: "grid", gap: 12, alignContent: "start" }}>
            <span className="logo" role="img" aria-label="Giro"><LogoGiro /></span>
            <span className="wl-mono wl-muted">giro.ceo</span>
          </div>
          <div><h4>Produto</h4><ul><li><a className="ulink" href="#modulos">Módulos</a></li><li><a className="ulink" href="#white-label">White label</a></li><li><a className="ulink" href="#planos">Planos</a></li></ul></div>
          <div><h4>Ajuda</h4><ul><li><a className="ulink" href="#perguntas">Perguntas frequentes</a></li><li><a className="ulink" href={LINK_WHATSAPP} rel="noopener">Falar com a gente</a></li></ul></div>
          <div><h4>Legal</h4><ul><li><a className="ulink" href={LINK_TERMOS}>Termos de uso</a></li><li><a className="ulink" href={LINK_PRIVACIDADE}>Privacidade</a></li></ul></div>
        </div>
        <div className="legal"><span>© 2026 Giro</span><span>Feito para locadoras de motos e carros</span></div>
      </div>
    </footer>
  );
}
