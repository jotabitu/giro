// DADOS FALSOS da página pública de assinatura nos testes (docs/api/contratos.md). Só api-falsa.ts importa este arquivo.
// Tokens: "link-lucas" (LOC-2856, enviado), "link-vencido" (410 link_expirado), "link-assinado" (410 contrato_ja_assinado); outro, 404.
import { ErroApi } from "@/lib/api/tipos";
import type { AssinaturaFeita, ConsultaDaAssinatura } from "@/lib/api/tipos-assinar";
import { pausa } from "./falso";

const CLIENTE = "Lucas Ferreira";
let assinado = false;

const semAcento = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().replace(/\s+/g, " ").toLowerCase();

export const assinarFalso = {
  async consultar(corpo: { token: string }): Promise<ConsultaDaAssinatura> {
    await pausa();
    if (corpo.token === "link-vencido") throw new ErroApi(410, "link_expirado", "Este link venceu. Peça um novo à locadora.");
    if (corpo.token === "link-assinado" || (corpo.token === "link-lucas" && assinado)) throw new ErroApi(410, "contrato_ja_assinado", "Este contrato já foi assinado.");
    if (corpo.token !== "link-lucas") throw new ErroApi(404, "nao_encontrado", "Link não encontrado");
    return {
      empresa: { nome_exibicao: "Moto Rápida", logo_url: null, cor_marca: "#0E7C66" },
      contrato: { codigo: "LOC-2856", titulo: "Contrato de locação semanal", cliente_nome: CLIENTE, pdf_url: "/contratos/LOC-2856.pdf", pdf_url_expira_em: "2026-10-15T15:15:00Z", status: "enviado" },
    };
  },

  async assinar(corpo: { token: string; aceite: boolean; nome_completo: string }): Promise<AssinaturaFeita> {
    await this.consultar({ token: corpo.token });
    if (!corpo.aceite) throw new ErroApi(400, "validacao", "Confira os campos destacados", undefined, { aceite: "Marque que leu e concorda" });
    if (semAcento(corpo.nome_completo) !== semAcento(CLIENTE)) throw new ErroApi(400, "nome_nao_confere", "Digite seu nome completo como está no cadastro", undefined, { nome_completo: "Digite seu nome completo como está no cadastro" });
    assinado = true;
    return { status: "assinado", assinado_em: "2026-10-15T15:02:00Z" };
  },
};
