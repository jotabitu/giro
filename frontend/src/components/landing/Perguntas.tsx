import { Plus } from "lucide-react";
import { Icone } from "@/design-system/Icone";

// TODO(landing): validar com a equipe as respostas de importação de planilha, validade jurídica e LGPD.
const PERGUNTAS = [
  { p: "Consigo trazer minha planilha?", r: "Sim. Você envia a planilha de veículos e clientes e a gente importa para você durante o teste." },
  { p: "O contrato tem validade jurídica?", r: "O contrato é assinado eletronicamente pelo link, com registro de data, hora e dispositivo. A assinatura eletrônica é reconhecida pela lei brasileira para contratos entre particulares." },
  { p: "Dá para cobrar por Pix e boleto?", r: "Sim. Cada parcela gera Pix e boleto, e o pagamento cai como recebido no contrato." },
  { p: "Meus dados ficam seguros? E a LGPD?", r: "Os dados ficam em servidores com acesso por usuário e permissão. Você controla quem vê cada tela e pode exportar ou apagar os dados de um cliente quando ele pedir." },
  { p: "Funciona no celular?", r: "Funciona no navegador do celular, sem instalar nada. A vistoria foi pensada primeiro para o celular." },
  { p: "Quanto tempo leva para começar?", r: "Você cria a conta em minutos e cadastra a primeira locação no mesmo dia. A importação da planilha entra junto." },
];

export function Perguntas() {
  return (
    <section id="perguntas">
      <div className="wrap faq-grid">
        <div className="head" style={{ alignContent: "start" }}>
          <p className="over">Perguntas frequentes</p>
          <h2 className="h2">O que as locadoras perguntam antes de começar.</h2>
        </div>
        <div className="faq">
          {PERGUNTAS.map((q) => (
            <details key={q.p}>
              <summary>{q.p} <Icone de={Plus} /></summary>
              <p>{q.r}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
