import { Banknote, Car, ChartColumn, FileText, Smartphone, Tag, Wrench } from "lucide-react";
import { Icone } from "@/design-system/Icone";

export function Modulos() {
  return (
    <section id="modulos">
      <div className="wrap">
        <div className="head">
          <p className="over">Módulos</p>
          <h2 className="h2">Tudo o que a locadora usa no dia, no mesmo sistema.</h2>
        </div>
        <div className="mods">
          <article className="wl-panel mod wide lift">
            <h3><Icone de={Car} /> Frota com status</h3>
            <p>Cada moto e carro com status, quilometragem e histórico. Você vê o que está livre antes do cliente perguntar.</p>
            <div className="frag">
              <div className="row"><span><span className="wl-cell-main">Honda Biz 125</span><span className="wl-cell-sub wl-mono">PLK-2E14 · 8.912 km</span></span><span className="wl-badge wl-badge--sm wl-badge--solid">Alugado</span></div>
              <div className="row"><span><span className="wl-cell-main">Fiat Mobi Like</span><span className="wl-cell-sub wl-mono">SBD-9F33 · 41.207 km</span></span><span className="wl-badge wl-badge--sm wl-badge--info"><span className="wl-badge__dot" />Reservado</span></div>
            </div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={FileText} /> Locações e contratos</h3>
            <p>Diária, semanal ou mensal, com renovação e reajuste.</p>
            <div className="frag"><div className="row"><span className="wl-mono">LOC-2839</span><span className="wl-badge wl-badge--sm wl-badge--success">Ativo</span></div></div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={Smartphone} /> Vistoria pelo celular</h3>
            <p>Check-out e check-in em uma coluna, com fotos.</p>
            <div className="frag"><div className="row"><span className="wl-muted">Check-in</span><span className="wl-badge wl-badge--sm wl-badge--attention">Em vistoria</span></div></div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={Banknote} /> Contas a receber e caixa</h3>
            <p>Pix e boleto por contrato, e o caixa do dia fechado no fim do turno.</p>
            <div className="frag"><div className="row"><span className="wl-muted">Caixa de hoje</span><span className="wl-mono">R$ 3.715,00</span></div></div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={Tag} /> Vendas com aprovação</h3>
            <p>O vendedor monta a proposta e o gerente aprova o desconto.</p>
            <div className="frag"><div className="row"><span className="wl-mono">R$ 14.900,00</span><span className="wl-badge wl-badge--sm wl-badge--warning">Aguardando gerente</span></div></div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={Wrench} /> Manutenção</h3>
            <p>Revisão por quilometragem e custo por veículo.</p>
            <div className="frag"><div className="row"><span className="wl-muted">Troca de óleo</span><span className="wl-mono">em 420 km</span></div></div>
          </article>
          <article className="wl-panel mod lift">
            <h3><Icone de={ChartColumn} /> Relatórios</h3>
            <p>Ocupação, receita por veículo e inadimplência no mês.</p>
            <div className="frag"><div className="wl-progress" style={{ margin: 0 }}><span>Ocupação</span><div className="wl-progress__track"><div className="wl-progress__fill" style={{ width: "71%" }} /></div><span className="wl-mono">71%</span></div></div>
          </article>
        </div>
      </div>
    </section>
  );
}
