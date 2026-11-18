import { Camera, Check } from "lucide-react";
import { Icone } from "@/design-system/Icone";

export function ComoFunciona() {
  return (
    <section id="como-funciona" style={{ background: "var(--surface-sunken)" }}>
      <div className="wrap">
        <div className="head">
          <p className="over">Como funciona</p>
          <h2 className="h2">Uma locação do começo ao fim, em 4 passos.</h2>
        </div>
        <ol className="steps">
          <li className="wl-panel step lift">
            <span className="n">01</span>
            <h3>Cadastre o cliente</h3>
            <p>CNH, documento e endereço uma vez só. Na próxima locação, ele já está lá.</p>
            <div className="frag">
              <div className="row"><span><b style={{ fontWeight: 500 }}>Carlos Menezes</b><br /><span className="wl-muted wl-mono">CNH cat. A</span></span><span className="wl-badge wl-badge--sm wl-badge--success">Aprovado</span></div>
            </div>
          </li>
          <li className="wl-panel step lift">
            <span className="n">02</span>
            <h3>Vistoria de saída pelo celular</h3>
            <p>Fotos de cada lado, quilometragem e combustível, salvos com data e hora.</p>
            <div className="frag">
              <div className="shots">
                <div className="ok"><Icone de={Check} /></div>
                <div className="ok"><Icone de={Check} /></div>
                <div className="ok"><Icone de={Check} /></div>
                <div><Icone de={Camera} /></div>
              </div>
              <div className="row"><span className="wl-muted">Fotos</span><span className="wl-mono">3 de 4</span></div>
              <div className="row"><span className="wl-muted">Hodômetro</span><span className="wl-mono">12.430 km</span></div>
            </div>
          </li>
          <li className="wl-panel step lift">
            <span className="n">03</span>
            <h3>Contrato assinado pelo link</h3>
            <p>O cliente recebe o link, lê no celular e assina. O PDF fica no histórico dele.</p>
            <div className="frag">
              <div className="row"><span className="wl-mono">LOC-2841</span><span className="wl-badge wl-badge--sm wl-badge--info">Aguardando assinatura</span></div>
              <div className="row"><span className="wl-muted">Semanal</span><span className="wl-mono">R$ 280,00</span></div>
            </div>
          </li>
          <li className="wl-panel step lift">
            <span className="n">04</span>
            <h3>Devolução com acerto automático</h3>
            <p>O Giro compara as vistorias, soma dias extras e avarias e calcula quanto da caução volta.</p>
            <div className="frag">
              <div className="row"><span className="wl-muted">Caução</span><span className="wl-mono">R$ 600,00</span></div>
              <div className="row"><span className="wl-muted">2 dias extras</span><span className="wl-mono">− R$ 80,00</span></div>
              <div className="row"><b style={{ fontWeight: 500 }}>A devolver</b><span className="wl-mono" style={{ fontWeight: 500 }}>R$ 520,00</span></div>
            </div>
          </li>
        </ol>
      </div>
    </section>
  );
}
