import { Check, Clock, CreditCard, X } from "lucide-react";
import { Icone } from "@/design-system/Icone";
import { LINK_TESTE_GRATIS } from "./links";

const PLANOS = [
  { nome: "Essencial", preco: "R$ 199", frase: "Para quem está saindo da planilha.", itens: ["Frota com status", "Locações e contratos", "Vistoria pelo celular", "Contas a receber"], pro: false },
  { nome: "Profissional", preco: "R$ 449", frase: "Para a locadora que cobra toda semana.", itens: ["Tudo do Essencial", "Caixa do dia", "Manutenção", "Relatórios", "Sua cor, logo e endereço"], pro: true },
  { nome: "Completo", preco: "R$ 899", frase: "Para quem também vende motos e carros.", itens: ["Tudo do Profissional", "Vendas com aprovação do gerente", "Mais de uma filial"], pro: false },
];

export function Planos() {
  return (
    <section id="planos" style={{ background: "var(--surface-sunken)" }}>
      <div className="wrap">
        <div className="head">
          <p className="over">Planos</p>
          <h2 className="h2">Comece grátis e escolha o plano depois.</h2>
        </div>
        <div className="plans">
          {PLANOS.map((p) => (
            <article key={p.nome} className={p.pro ? "wl-panel plan pro" : "wl-panel plan"}>
              <h3>{p.nome}{p.pro && <> <span className="wl-badge wl-badge--sm wl-badge--brand">Mais vendido</span></>}</h3>
              <div className="price"><b>{p.preco}</b><span className="wl-muted">/mês</span></div>
              <p className="wl-muted">{p.frase}</p>
              <ul>
                {p.itens.map((item) => <li key={item}><Icone de={Check} />{item}</li>)}
              </ul>
              <a className={p.pro ? "wl-btn wl-btn--brand" : "wl-btn wl-btn--quiet"} href={LINK_TESTE_GRATIS}>Começar teste grátis</a>
            </article>
          ))}
        </div>
        <div className="terms">
          <span className="wl-badge wl-badge--surface"><Icone de={Clock} />14 dias grátis</span>
          <span className="wl-badge wl-badge--surface"><Icone de={CreditCard} />Sem cartão</span>
          <span className="wl-badge wl-badge--surface"><Icone de={X} />Cancele quando quiser</span>
        </div>
      </div>
    </section>
  );
}
