// Blocos da ficha que vêm da API (T-275, "Blocos da ficha" de veiculos.md): aparecem quando a chave vem e somem quando não vem.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { contas, veiculos, type VeiculoDetalhe, type VistoriaRecente } from "@/lib/api";
import { AgoraDesktop, FotosEAvarias, FotosEAvariasCelular, MovimentacoesCelular, MovimentacoesDoVeiculo } from "./FichaBlocos";

let base: VeiculoDetalhe;
beforeAll(async () => {
  const r = await contas.entrar({ email: "rodrigo@motorapida.com.br", senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") throw new Error("esperava pronto");
  base = await veiculos.obter(501);
});

const html = (el: ReactElement) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);
const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

const comBlocos = (): VeiculoDetalhe => ({
  ...base,
  locacao_atual: {
    ...(base.locacao_atual as NonNullable<VeiculoDetalhe["locacao_atual"]>),
    plano: { periodicidade: "semanal", plano_especial: null, valor_periodo_centavos: 29940 },
    pagamento: { situacao: "atrasado", rotulo: "Parcela 2 atrasada", conta_id: 28412, valor_centavos: 30609, atrasadas: 1, cobrar: true },
  },
  manutencao: {
    proxima: {
      servico: "Troca de óleo",
      km: 19900,
      faltam_km: 950,
      intervalo_km: 1000,
      progresso_pct: "5.00",
      dias_estimados: null,
      depois: { servico: "Revisão 20 mil", km: 20000, faltam_km: 1050 },
      nota: "Faltando 500 km, abre uma OS agendada para a devolução.",
    },
    os_aberta: null,
  },
});

describe("Agora (desktop)", () => {
  it("pagamento da locação com o valor do dia, o plano e o Cobrar quando a API manda", () => {
    const t = texto(html(<AgoraDesktop v={comBlocos()} />));
    expect(t).toContain("LOC-2841 · Semanal R$ 299,40");
    expect(t).toContain("Pagamentos");
    expect(t).toContain("Parcela 2 atrasada · R$ 306,09");
    expect(t).toContain("Cobrar");
    expect(t).toContain("Ver locação");
  });

  it("próxima manutenção com o intervalo, o faltam, a barra, o depois e a nota; sem o trecho de dias quando vem null", () => {
    const h = html(<AgoraDesktop v={comBlocos()} />);
    const t = texto(h);
    expect(t).toContain("a cada 1.000 km");
    expect(t).toContain("Troca de óleo");
    expect(t).toContain("aos 19.900 km");
    expect(t).toContain("faltam");
    expect(t).toContain("950 km");
    expect(t).not.toContain("cerca de");
    expect(t).toContain("Depois: revisão 20 mil, a 1.050 km. Faltando 500 km, abre uma OS agendada para a devolução.");
    expect(h).toContain('role="progressbar"');
    expect(h).toContain('aria-valuenow="5"');
  });

  it("com os dias estimados que a API mandar, mostra o trecho", () => {
    const v = comBlocos();
    v.manutencao!.proxima!.dias_estimados = 6;
    expect(texto(html(<AgoraDesktop v={v} />))).toContain("(cerca de 6 dias de uso)");
  });

  it("sem plano, pagamento e campos novos da manutenção, mostra só o que a API manda e não inventa número", () => {
    const h = html(<AgoraDesktop v={base} />);
    const t = texto(h);
    expect(t).toContain("Carlos Menezes");
    expect(t).not.toContain("Pagamentos");
    expect(t).not.toContain("Cobrar");
    expect(t).not.toContain("faltam");
    expect(t).not.toContain("a cada");
    expect(h).not.toContain('role="progressbar"');
  });

  it("pagamento em dia mostra só o rótulo, sem valor e sem Cobrar", () => {
    const v = comBlocos();
    v.locacao_atual!.pagamento = { situacao: "em_dia", rotulo: "Em dia", conta_id: null, valor_centavos: 0, atrasadas: 0, cobrar: false };
    const t = texto(html(<AgoraDesktop v={v} />));
    expect(t).toContain("Em dia");
    expect(t).not.toContain("R$ 0,00");
    expect(t).not.toContain("Cobrar");
  });

  it("pagamento atrasado para quem não cobra (cobrar false) não mostra o botão", () => {
    const v = comBlocos();
    v.locacao_atual!.pagamento!.cobrar = false;
    const t = texto(html(<AgoraDesktop v={v} />));
    expect(t).toContain("Parcela 2 atrasada · R$ 306,09");
    expect(t).not.toContain("Cobrar");
  });
});

const vistoria: VistoriaRecente = {
  id: 3120,
  tipo: "saida",
  concluida_em: "2026-09-23T12:10:00Z",
  vistoriador: { id: 4, nome: "João Silva" },
  locacao_codigo: "LOC-2841",
  total_fotos: 12,
  fotos: (["frente", "traseira", "lado_esquerdo", "lado_direito", "painel"] as const).map((posicao, i) => ({ id: 901 + i, posicao, url: "", url_expira_em: "" })),
  avarias: [
    { id: 51, descricao: "Risco no tanque, lado esquerdo", registrada_em: "2026-07-12T14:00:00Z", preexistente: true, locacao_codigo: null, foto_id: 903 },
    { id: 77, descricao: "Retrovisor direito trincado", registrada_em: "2026-09-23T12:05:00Z", preexistente: false, locacao_codigo: "LOC-2841", foto_id: 905 },
  ],
};

describe("Fotos e avarias (desktop)", () => {
  it("fotos nas cinco posições, avarias numeradas com a origem e o aviso de que a da saída não é cobrada", () => {
    const t = texto(html(<FotosEAvarias vistoria={vistoria} />));
    expect(t).toContain("vistoria de saída · 23 set · João Silva");
    for (const p of ["Frente", "Traseira", "Esquerda", "Direita", "Painel"]) expect(t).toContain(p);
    expect(t).toContain("Ver as 12 fotos da vistoria");
    expect(t).toContain("2 avarias registradas");
    expect(t).toContain("Risco no tanque, lado esquerdo");
    expect(t).toContain("12 jul · já existia, não cobrar");
    expect(t).toContain("23 set · registrado na saída da LOC-2841");
    expect(t).toContain("Avaria registrada na saída não é cobrada do cliente na devolução.");
  });

  it("o selo de avaria fica na foto a que a avaria aponta", () => {
    const h = html(<FotosEAvarias vistoria={vistoria} />);
    expect(h.match(/absolute right-2 top-2/g)).toHaveLength(2);
  });

  it("sem a vistoria (financeiro, veículo sem vistoria) o painel não aparece", () => {
    expect(html(<FotosEAvarias vistoria={undefined} />)).toBe("");
    expect(html(<FotosEAvarias vistoria={null} />)).toBe("");
  });

  it("vistoria sem avarias diz que não há nenhuma e não mostra o aviso da devolução", () => {
    const t = texto(html(<FotosEAvarias vistoria={{ ...vistoria, avarias: [] }} />));
    expect(t).toContain("Nenhuma avaria registrada");
    expect(t).not.toContain("não é cobrada");
  });
});

describe("Movimentações (desktop)", () => {
  it("sem o bloco da API o painel não aparece", () => {
    expect(html(<MovimentacoesDoVeiculo v={{ ...base, movimentacoes: undefined }} />)).toBe("");
    expect(html(<MovimentacoesDoVeiculo v={{ ...base, movimentacoes: null }} />)).toBe("");
  });

  it("sem movimentações mostra o texto vazio com o motivo da API", () => {
    const v: VeiculoDetalhe = { ...base, movimentacoes: { total: 0, ultimas: [], em_andamento: null }, acoes: { ...base.acoes, movimentar: false, motivo_movimentar: "Veículo alugado não se movimenta." } };
    const t = texto(html(<MovimentacoesDoVeiculo v={v} />));
    expect(t).toContain("Nenhuma movimentação. Veículo alugado não se movimenta.");
    expect(t).toContain("ver todas");
  });

  it("lista as últimas com o código, o caminho e a data", () => {
    const v: VeiculoDetalhe = {
      ...base,
      movimentacoes: { total: 1, ultimas: [{ id: 43, codigo: "MOV-0043", status: "concluida", destino_nome: "Filial Centro", paradas: ["Lava Rápido Aldeota"], iniciada_em: "2026-09-29T12:00:00Z", concluida_em: "2026-09-29T15:00:00Z" }], em_andamento: null },
    };
    const t = texto(html(<MovimentacoesDoVeiculo v={v} />));
    expect(t).toContain("MOV-0043");
    expect(t).toContain("Lava Rápido Aldeota → Filial Centro");
    expect(t).toContain("29 set");
  });
});

describe("Blocos da ficha no celular", () => {
  it("fotos e avarias: tipo, data e avarias numeradas; some sem vistoria", () => {
    expect(html(<FotosEAvariasCelular vistoria={null} />)).toBe("");
    const t = texto(html(<FotosEAvariasCelular vistoria={vistoria} />));
    expect(t).toContain("saída · 23 set");
    expect(t).toContain("Retrovisor direito trincado");
    expect(t).toContain("23 set · registrado na saída da LOC-2841");
  });

  it("fotos e avarias sem avaria diz que não há", () => {
    const t = texto(html(<FotosEAvariasCelular vistoria={{ ...vistoria, tipo: "devolucao", fotos: [], total_fotos: 0, avarias: [] }} />));
    expect(t).toContain("devolução · 23 set");
    expect(t).toContain("Nenhuma avaria registrada.");
  });

  it("movimentações: texto vazio com o motivo da API e some sem o bloco", () => {
    expect(html(<MovimentacoesCelular v={{ ...base, movimentacoes: undefined }} />)).toBe("");
    const v: VeiculoDetalhe = { ...base, movimentacoes: { total: 0, ultimas: [], em_andamento: null }, acoes: { ...base.acoes, movimentar: false, motivo_movimentar: "Veículo alugado não se movimenta." } };
    expect(texto(html(<MovimentacoesCelular v={v} />))).toContain("Nenhuma movimentação. Veículo alugado não se movimenta.");
  });
});
