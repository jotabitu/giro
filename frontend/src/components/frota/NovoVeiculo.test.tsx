import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Eu } from "@/lib/api";

const sessao = vi.hoisted(() => ({ veiculos: "editar" as string }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {}, replace: () => {} }), usePathname: () => "/veiculos", useSearchParams: () => new URLSearchParams() }));
vi.mock("@/lib/sessao", () => ({
  useSessao: () => ({ eu: { filiais: [{ id: 1, nome: "Filial Centro" }], pode: { veiculos: sessao.veiculos } } as unknown as Eu, sair: async () => {} }),
}));

import { ListaVeiculos } from "./ListaVeiculos";
import { NovoVeiculoForm } from "./NovoVeiculoForm";

const html = (el: React.ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);

describe("botão Cadastrar veículo na Frota", () => {
  it("aparece uma vez só, como botão preto com texto, para quem pode editar veículos", () => {
    sessao.veiculos = "editar";
    const h = html(<ListaVeiculos />);
    expect(h).toContain('href="/veiculos/novo"');
    expect(h).toContain("Cadastrar veículo");
    expect(h.match(/href="\/veiculos\/novo"/g)).toHaveLength(1);
    expect(h).toContain("wl-btn wl-btn--solid");
    expect(h).not.toContain("wl-icon-btn");
    expect(h).not.toContain('aria-label="Cadastrar veículo"');
  });

  it("não aparece para quem só vê ou só registra km", () => {
    for (const p of ["nao", "km_e_avarias"]) {
      sessao.veiculos = p;
      expect(html(<ListaVeiculos />)).not.toContain("/veiculos/novo");
    }
  });
});

describe("tela Cadastrar veículo", () => {
  it("mostra os campos do contrato e as filiais da pessoa", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    for (const t of ["Placa", "Marca", "Modelo", "Chassi", "Renavam", "Km atual", "Tipo de plano", "Salvar veículo", "Salvar e cadastrar outro"]) expect(h).toContain(t);
    expect(h).toContain("Nunca diminui depois de salvo");
    expect(h).toContain(">Filial Centro</option>");
  });

  it("test_vei_09_cadastro_mostra_combustivel_dados_do_documento_rastreador_e_anotacoes_todos_opcionais (CA-421-06, CA-421-08)", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    for (const t of ["Combustível", "Espécie", "Tipo", "Carroceria", "Potência (cv)", "Cilindrada (cc)", "Lotação (pessoas)", "Peso bruto total (kg)", "Número do motor", "Observações do CRLV-e", "Rastreador · número ou IMEI", "Rastreador · empresa", "Anotações"]) expect(h).toContain(t);
    // Opcionais: nenhum campo da VEI-09 é obrigatório na tela.
    expect(h).not.toMatch(/(Combustível|Potência|Lotação|Anotações)[^<]*<[^>]*required/);
    for (const flex of ['<option value="flex">Flex</option>', '<option value="gasolina">Gasolina</option>']) expect(h).toContain(flex);
  });

  it("test_vei_11_tipo_antes_da_categoria_com_moto_marcado (CA-438-01)", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    const tipo = h.indexOf(">Moto ou carro</label>");
    expect(tipo).toBeGreaterThan(h.indexOf(">Filial</label>"));
    expect(tipo).toBeLessThan(h.indexOf(">Tipo de plano</label>"));
    expect(h).toMatch(/<option value="moto" selected="">Moto<\/option>/);
    expect(h).toContain('<option value="carro">Carro</option>');
    // O controle de tipo saiu do cabeçalho: um só campo de tipo na tela.
    expect(h.match(/Tipo de plano/g)).toHaveLength(1);
  });

  it("a leitura do CRLV-e está ligada e a FIPE segue desativada (VEI-08)", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    expect(h).toMatch(/<button(?![^>]*disabled)[^>]*>Enviar CRLV-e/);
    expect(h).toContain('accept=".pdf,application/pdf"');
    expect(h).toContain("Envie o PDF do CRLV-e e preenchemos placa");
    expect(h).toContain('list="modelos-do-catalogo"');
    expect(h).not.toContain("Validade do CRLV");
    expect(h).toContain("A consulta FIPE ainda não está disponível");
  });

  it("T-519: o bloco do painel lateral e a barra flutuante submetem o mesmo form; a barra nasce escondida até o bloco sair da tela", () => {
    sessao.veiculos = "editar";
    const h = html(<NovoVeiculoForm />);
    const formulario = h.slice(h.indexOf("<form"), h.indexOf("</form>"));
    // Os dois botões principais estão dentro do mesmo <form>: Enter e clique salvam do mesmo jeito.
    expect(formulario.match(/<button type="submit"[^>]*>Salvar veículo<\/button>/g)).toHaveLength(2);
    expect(formulario.match(/>Salvar e cadastrar outro</g)).toHaveLength(1);
    expect(formulario.match(/>Cancelar</g)).toHaveLength(2);
    expect(formulario.indexOf("Salvar e cadastrar outro")).toBeLessThan(formulario.indexOf("sticky bottom-[88px]"));
    // Antes da primeira medida o bloco conta como visível: a barra fica inerte e invisível.
    expect(formulario).toMatch(/aria-hidden="true"[^>]*inert=""[^>]*class="sticky bottom-\[88px\][^"]*opacity-0/);
  });

  it("perfil sem permissão não vê o formulário", () => {
    sessao.veiculos = "nao";
    const h = html(<NovoVeiculoForm />);
    expect(h).toContain("Seu perfil não cadastra veículos");
    expect(h).not.toContain("Chassi");
  });
});
