// DADOS FALSOS da página pública do recibo nos testes (docs/api/vistorias.md). Só api-falsa.ts importa este arquivo.
// Tokens: "link-juliana" (LOC-2836, concluída), "link-vencido" (410 link_expirado); outro, 404.
import { ErroApi } from "@/lib/api/tipos";
import type { ConsultaDoRecibo } from "@/lib/api/tipos-recibo";
import { pausa } from "./falso";

let consultas = 0;

export const reciboFalso = {
  async consultar(corpo: { token: string }): Promise<ConsultaDoRecibo> {
    await pausa();
    if (corpo.token === "link-vencido") throw new ErroApi(410, "link_expirado", "Este link venceu. Peça um novo à locadora.");
    if (corpo.token !== "link-juliana") throw new ErroApi(404, "nao_encontrado", "Link não encontrado");
    consultas += 1;
    return {
      empresa: { nome_exibicao: "Moto Rápida", logo_url: null, cor_marca: "#0E7C66" },
      // A URL do PDF muda a cada consulta, como a assinada de 15 minutos da API.
      recibo: { codigo: "LOC-2836", cliente_primeiro_nome: "Juliana", concluida_em: "2026-10-14T20:35:00Z", pdf_url: `/recibos/LOC-2836.pdf?v=${consultas}`, pdf_url_expira_em: "2026-10-14T20:50:00Z" },
    };
  },
};
