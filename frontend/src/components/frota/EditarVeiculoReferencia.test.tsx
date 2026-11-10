// T-448 · Editar veículo perto da referência (Veiculo-Editar-Desktop|Mobile): galeria no topo, ações no cabeçalho, travados e rótulos.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { contas, veiculos, type Eu } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos/501/editar", useSearchParams: () => new URLSearchParams() }));

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { EditarVeiculo } from "./EditarVeiculo";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function pagina(id: number): Promise<string> {
  const ficha = await veiculos.obter(id);
  const cliente = new QueryClient();
  cliente.setQueryData(["veiculo", id], ficha);
  cliente.setQueryData(["categorias", { filial: String(ficha.filial.id), tipo: ficha.tipo_veiculo }], await veiculos.categorias({ filial: ficha.filial.id, tipo_veiculo: ficha.tipo_veiculo }));
  return renderToStaticMarkup(
    <QueryClientProvider client={cliente}>
      <EditarVeiculo id={id} />
    </QueryClientProvider>,
  );
}

describe("editar veículo na referência (T-448)", () => {
  beforeAll(() => entrarComo("rodrigo@motorapida.com.br"));

  it("test_vei_01_editar_galeria_no_topo_cartao_ao_lado_acoes_no_cabecalho_e_documentos_no_fim", async () => {
    const html = await pagina(501);
    const t = texto(html);
    ordem(t, ["Editar veículo", "Cancelar", "Salvar alterações", "Carregando as fotos…", "Honda CG 160 Fan", "Identificação", "Documentos"]);
    // O botão de salvar fica no cabeçalho e liga ao formulário pelo atributo form.
    expect(html).toMatch(/<button[^>]*form="editar-veiculo"[^>]*>Salvar alterações/);
    expect(html).toContain('id="editar-veiculo"');
    // Sem Finalidade, Plano de manutenção nem Renovar: não há regra nem campo (T-448).
    for (const fora of ["Finalidade", "Plano de manutenção", "Renovar"]) expect(t, fora).not.toContain(fora);
  });

  it("test_vei_01_editar_placa_e_chassi_fixos_no_cadastro", async () => {
    const t = texto(await pagina(501));
    expect(t).toContain("Fixo no cadastro");
    expect(t).toContain("17 caracteres · Fixo no cadastro");
  });

  it("test_vei_09_editar_tipo_do_documento_chama_tipo_no_crlv_e", async () => {
    const t = texto(await pagina(501));
    expect(t).toContain("Tipo no CRLV-e");
    expect(t).toContain("Não é o tipo do veículo, que fica em Uso na frota.");
  });
});
