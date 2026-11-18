import { Bike, Clipboard, Clock, Wallet, type LucideIcon } from "lucide-react";
import { Icone } from "@/design-system/Icone";

const PROBLEMAS: { icone: LucideIcon; titulo: string; texto: string; selo: string; tom: string }[] = [
  { icone: Bike, titulo: "A moto parada que ninguém viu", texto: "Ela volta da oficina e fica no pátio dias sem gerar locação, porque a planilha não diz que está livre.", selo: "Em manutenção há 9 dias", tom: " wl-badge--warning" },
  { icone: Wallet, titulo: "A caução esquecida na gaveta", texto: "O cliente devolve, ninguém lembra quanto ficou retido e o acerto vira discussão no balcão.", selo: "Caução sem registro", tom: " wl-badge--critical" },
  { icone: Clock, titulo: "A cobrança atrasada no WhatsApp", texto: "Cada semanal é uma conversa. Se você não manda a mensagem, o pagamento simplesmente não chega.", selo: "Atrasado 6 dias", tom: " wl-badge--critical" },
  { icone: Clipboard, titulo: "A vistoria no papel", texto: "O risco no tanque não tem foto nem data. Na devolução, é a sua palavra contra a do cliente.", selo: "Sem foto de saída", tom: "" },
];

export function Problema() {
  return (
    <section id="problema">
      <div className="wrap">
        <div className="head">
          <p className="over">O que dá errado hoje</p>
          <h2 className="h2">Planilha, caderno e WhatsApp não avisam quando algo sai do lugar.</h2>
        </div>
        <div className="probs">
          {PROBLEMAS.map((p) => (
            <article key={p.titulo} className="wl-panel prob">
              <span className="ic"><Icone de={p.icone} /></span>
              <h3>{p.titulo}</h3>
              <p>{p.texto}</p>
              <span className={`wl-badge wl-badge--sm${p.tom}`}><span className="wl-badge__dot" />{p.selo}</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
