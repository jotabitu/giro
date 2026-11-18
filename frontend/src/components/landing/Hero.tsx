import { ArrowRight, Bell, Check, MessageCircle } from "lucide-react";
import { Icone } from "@/design-system/Icone";
import { IrParaPlanos } from "./IrParaPlanos";
import { LINK_WHATSAPP } from "./links";

export function Hero() {
  return (
    <section className="hero dark" id="topo">
      <div className="wrap hero-grid" data-enter="">
        <div className="hero-copy">
          <span className="wl-badge wl-badge--brand" style={{ justifySelf: "start" }}>14 dias grátis, sem cartão</span>
          <h1 className="h1">Sua locadora de motos e carros fora do caderno.</h1>
          <p className="lead">O Giro junta frota, contratos, vistoria e cobrança num sistema só, com a cor, o logo e o nome da sua empresa.</p>
          <div className="actions">
            <IrParaPlanos className="wl-btn wl-btn--brand">Começar teste grátis <Icone de={ArrowRight} /></IrParaPlanos>
            <a className="wl-btn" href={LINK_WHATSAPP} rel="noopener"><Icone de={MessageCircle} /> Falar com a gente</a>
          </div>
          <div className="hero-note">
            <span><Icone de={Check} /> Cancele quando quiser</span>
            <span><Icone de={Check} /> Funciona no celular</span>
          </div>
        </div>

        <div className="app light" role="img" aria-label="Recorte do painel do Giro: 128 veículos na frota, 91 alugados, barra de status da frota e card com 7 contratos que precisam de ação hoje">
          <div className="app-top">
            <b>Bom dia, Mariana</b>
            <span className="wl-badge wl-badge--sm" style={{ background: "var(--surface)" }}><span className="wl-mono" style={{ fontSize: 13 }}>18 nov</span></span>
          </div>
          <div className="wl-kpis">
            <div className="wl-kpi wl-kpi--solid"><div className="wl-kpi__label">Frota</div><div className="wl-kpi__value">128</div><div className="wl-kpi__meta">veículos ativos</div></div>
            <div className="wl-kpi"><div className="wl-kpi__label">Alugados</div><div className="wl-kpi__value">71%</div><div className="wl-kpi__meta"><span className="wl-kpi__up">+4%</span> no mês</div></div>
            <div className="wl-kpi"><div className="wl-kpi__label">A receber hoje</div><div className="wl-kpi__value" style={{ fontSize: 26, lineHeight: "36px" }}>R$ 8.430</div><div className="wl-kpi__meta">23 cobranças</div></div>
          </div>
          <div className="app-grid">
            <div className="wl-panel">
              <div className="wl-pipe" style={{ padding: 0, background: "none" }}>
                <div className="wl-pipe__head"><span className="wl-pipe__title">Status da frota</span><span className="wl-pipe__note">128 veículos</span></div>
                <div className="wl-pipe__row">
                  <div className="wl-pipe__col wl-pipe__col--solid" style={{ flex: 91 }}><div className="wl-pipe__bar" /><div className="wl-pipe__num">91</div><div className="wl-pipe__label">Alugado</div></div>
                  <div className="wl-pipe__col wl-pipe__col--brand" style={{ flex: 18 }}><div className="wl-pipe__bar" /><div className="wl-pipe__num">18</div><div className="wl-pipe__label">Livre</div></div>
                  <div className="wl-pipe__col" style={{ flex: 19 }}><div className="wl-pipe__bar" /><div className="wl-pipe__num">19</div><div className="wl-pipe__label">Oficina</div></div>
                </div>
              </div>
              <table className="wl-table" style={{ marginTop: 16 }}>
                <tbody>
                  <tr><td><span className="wl-cell-main">Honda CG 160 Fan</span><span className="wl-cell-sub wl-mono">QXA-4B21</span></td><td style={{ textAlign: "right" }}><span className="wl-badge wl-badge--sm wl-badge--critical"><span className="wl-badge__dot" />Atrasado</span></td></tr>
                  <tr><td><span className="wl-cell-main">Yamaha Factor 150</span><span className="wl-cell-sub wl-mono">RTE-7C09</span></td><td style={{ textAlign: "right" }}><span className="wl-badge wl-badge--sm wl-badge--success"><span className="wl-badge__dot" />Disponível</span></td></tr>
                </tbody>
              </table>
            </div>
            <div className="wl-alert-card">
              <div className="wl-alert-card__head"><Icone de={Bell} /> Alertas <span className="wl-alert-card__time">08:12</span></div>
              <p className="wl-alert-card__title">7 contratos precisam de ação hoje</p>
              <ul>
                <li className="is-critical">3 devoluções atrasadas</li>
                <li className="is-warning">2 cauções a devolver</li>
                <li>2 renovações mensais</li>
              </ul>
              <span className="wl-btn wl-btn--brand wl-btn--sm" style={{ width: "100%" }}>Ver contratos</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
