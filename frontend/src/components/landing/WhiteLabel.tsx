import type { CSSProperties } from "react";
import { Globe, Image, Palette } from "lucide-react";
import { Icone } from "@/design-system/Icone";

// A mesma tela com três cores de cliente; on-brand grafite nas claras e branco no azul.
const TELAS = [
  { endereco: "motosbrisa.giro.ceo", sigla: "MB", nome: "Motos Brisa", cor: "#c8f04a", sobre: "#111114", rotulo: "Tela da locadora com cor verde-limão" },
  { endereco: "rotanorte.giro.ceo", sigla: "RN", nome: "Rota Norte", cor: "#ff7a45", sobre: "#111114", rotulo: "Tela da locadora com cor laranja" },
  { endereco: "alfacar.giro.ceo", sigla: "AC", nome: "Alfa Car", cor: "#2f6fed", sobre: "#ffffff", rotulo: "Tela da locadora com cor azul" },
];

export function WhiteLabel() {
  return (
    <section id="white-label" className="dark">
      <div className="wrap">
        <div className="head">
          <p className="over">White label</p>
          <h2 className="h2">O sistema sai com a cara da sua locadora.</h2>
          <p className="lead">Sua cor, seu logo e seu nome, no seu endereço. Seu cliente nunca vê a marca Giro.</p>
        </div>
        <div className="wl-shows">
          {TELAS.map((t) => (
            <div key={t.sigla} className="mini light" style={{ "--brand": t.cor, "--on-brand": t.sobre } as CSSProperties} role="img" aria-label={t.rotulo}>
              <div className="bar"><Icone de={Globe} /><span>{t.endereco}</span></div>
              <div className="brandrow"><span className="mark">{t.sigla}</span><b>{t.nome}</b><span className="hex">{t.cor}</span></div>
              <div className="wl-panel">
                <div className="menu"><span className="on">Locações <em>12</em></span><span>Frota</span></div>
                <span className="wl-btn wl-btn--brand wl-btn--sm">Nova locação</span>
              </div>
            </div>
          ))}
        </div>
        <ul className="wl-points">
          <li><Icone de={Palette} /><span><b>Sua cor</b>O texto sobre ela se ajusta sozinho para manter a leitura.</span></li>
          <li><Icone de={Image} /><span><b>Seu logo e seu nome</b>No menu, nos contratos e nos recibos.</span></li>
          <li><Icone de={Globe} /><span><b>Seu endereço</b><span className="wl-mono">suaempresa.giro.ceo</span></span></li>
        </ul>
      </div>
    </section>
  );
}
