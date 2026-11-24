// T-509 · Todo campo de reais usa o campo único com a máscara ao vivo; os campos numéricos que não são dinheiro ficam como estavam.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const arquivo = (caminho: string): string => readFileSync(new URL(caminho, import.meta.url), "utf8");

/** Módulo → telas com campo de dinheiro e quantos campos de dinheiro cada uma tem. */
const TELAS: Record<string, Record<string, number>> = {
  precos: { "precos/DialogoDaCategoria.tsx": 1, "precos/ExtrasDeLocacao.tsx": 1, "precos/PlanosDeCompra.tsx": 1, "precos/PlanosEspeciais.tsx": 1 },
  "precos do veiculo": { "precos-veiculo/PrecosDoVeiculo.tsx": 2, "precos-veiculo/PlanosDeAluguel.tsx": 3, "precos-veiculo/LocacaoComCompra.tsx": 4, "precos-veiculo/CustosMensais.tsx": 1 },
  financeiro: { "financeiro/CaixaDoDia.tsx": 3, "financeiro/NovaDespesa.tsx": 1, "financeiro/NovoLancamento.tsx": 1, "financeiro/DialogoRenegociarConta.tsx": 1 },
  movimentacoes: { "movimentacoes/NovaMovimentacao.tsx": 1, "movimentacoes/ParadaDaMovimentacao.tsx": 1 },
  vistorias: { "vistorias/AcertoDaDevolucao.tsx": 2 },
  vendas: { "vendas/TelaDaVenda.tsx": 1 },
  frota: { "frota/NovoVeiculoForm.tsx": 1, "frota/EditarVeiculo.tsx": 1 },
  implantacao: { "implantacao/PassoRecebimentos.tsx": 1 },
  admin: { "admin/FormularioDaFilial.tsx": 1 },
};

describe("campo único de dinheiro", () => {
  for (const [modulo, telas] of Object.entries(TELAS)) {
    it(`${modulo}: os campos de reais são CampoDeDinheiro ou InputDeDinheiro`, () => {
      for (const [tela, quantos] of Object.entries(telas)) {
        const codigo = arquivo(`./${tela}`);
        const usos = codigo.match(/<(CampoDeDinheiro|InputDeDinheiro)[\s>]/g) ?? [];
        expect(usos.length, tela).toBeGreaterThanOrEqual(quantos);
      }
    });
  }

  it("não sobrou a CampoDeDinheiro antiga de components/precos", () => {
    expect(() => arquivo("./precos/CampoDeDinheiro.tsx")).toThrow();
  });
});
