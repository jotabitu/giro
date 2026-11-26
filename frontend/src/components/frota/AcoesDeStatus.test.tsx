// T-518 · Colocar à venda, voltar para a frota e baixa na ficha do veículo (VEI-23, VEN-01, VEI-15, MOV-03; docs/api/veiculos.md,
// "Ações de status"; Veiculo-Desktop e Veiculo-Mobile, "Estados desta tela"). A API decide em `acoes` e recusa o resto; a tela só mostra.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { contas, ErroApi, veiculos, type Eu, type VeiculoDetalhe } from "@/lib/api";
import { ajustarVeiculoFalso } from "@/testes/falsos/falso-frota";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/veiculos", useSearchParams: () => new URLSearchParams() }));
const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));

import { avisoDeSucesso, ColocarAVenda, DarBaixa, errosDaBaixa, MaisAcoesDoCelular, textosDaAcao, VoltarParaFrota, type EstadoInicial } from "./AcoesDeStatus";
import { FichaVeiculo } from "./FichaVeiculo";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");
const ordem = (h: string, trechos: string[]) => {
  let pos = -1;
  for (const t of trechos) {
    const i = h.indexOf(t, pos + 1);
    expect(i, t).toBeGreaterThan(pos);
    pos = i;
  }
};

const ADMIN = "mariana@motorapida.com.br";
const GERENTE = "rodrigo@motorapida.com.br";
const VENDEDOR = "bruna@motorapida.com.br";
const FINANCEIRO = "financeiro@motorapida.com.br";
// Do falso: SAK-1D39 disponível (moto), QYB-5H60 à venda, QXA-4B21 alugada, UEF-8L63 disponível (carro).
const DISPONIVEL = 504;
const A_VENDA = 507;
const ALUGADO = 501;
const CARRO = 510;

// A API falsa limita a 10 entradas por minuto por e-mail: só entra de novo quando a pessoa muda.
let quem = "";
async function entrar(email: string) {
  if (quem === email) return;
  quem = email;
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

const html = (no: ReactNode) => renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{no}</QueryClientProvider>);

async function ficha(id: number): Promise<{ desktop: string; celular: string }> {
  const cache = new QueryClient();
  cache.setQueryData(["veiculo", id], await veiculos.obter(id));
  cache.setQueryData(["veiculo", id, "documentos"], await veiculos.documentos(id));
  cache.setQueryData(["veiculo", id, "locacoes"], await veiculos.locacoes(id));
  cache.setQueryData(["veiculo", id, "manutencoes"], await veiculos.manutencoes(id));
  const h = renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <FichaVeiculo id={id} />
    </QueryClientProvider>,
  );
  const [, desktop = "", celular = ""] = h.replace(/^(<link[^>]*>)+/, "").match(/^<div class="hidden md:block">(.*)<\/div><div class="md:hidden">(.*)<\/div>$/s) ?? [];
  return { desktop, celular };
}

/** O cabeçalho do desktop: do título até os indicadores. */
const cabecalho = (desktop: string) => texto(desktop.slice(0, desktop.indexOf("Ocupação")));

const falha = async (p: Promise<unknown>): Promise<ErroApi> => {
  try {
    await p;
  } catch (e) {
    if (e instanceof ErroApi) return e;
  }
  throw new Error("esperava ErroApi");
};

const nada = () => {};
type Dialogo = typeof ColocarAVenda;
const janela = (D: Dialogo, v: VeiculoDetalhe, opcoes: { celular?: boolean; inicial?: EstadoInicial } = {}) => html(<D v={v} aoFechar={nada} aoConcluir={nada} {...opcoes} />);

const desfazer: (() => void)[] = [];
const ajustar = (...args: Parameters<typeof ajustarVeiculoFalso>) => desfazer.push(ajustarVeiculoFalso(...args));
afterEach(() => {
  while (desfazer.length) desfazer.pop()?.();
});

describe("VEI-23: as ações que a API libera, por perfil e estado", () => {
  it("test_ven_01_gerente_ve_colocar_a_venda_no_disponivel_e_voltar_para_a_frota_no_a_venda_sem_dar_baixa", async () => {
    await entrar(GERENTE);
    const disponivel = await ficha(DISPONIVEL);
    ordem(cabecalho(disponivel.desktop), ["Editar", "Movimentar", "Mandar para oficina", "Colocar à venda", "Excluir"]);
    expect(cabecalho(disponivel.desktop)).not.toMatch(/Voltar para a frota|Dar baixa/);
    // O botão funciona: nada de "Ainda não está disponível".
    expect(disponivel.desktop).toMatch(/<button type="button" class="wl-btn wl-btn--solid">(<svg.*?<\/svg>)?Colocar à venda<\/button>/);
    expect(disponivel.desktop + disponivel.celular).not.toContain("Ainda não está disponível\">Colocar");
    const aVenda = await ficha(A_VENDA);
    ordem(cabecalho(aVenda.desktop), ["Editar", "Voltar para a frota", "Excluir"]);
    expect(cabecalho(aVenda.desktop)).not.toMatch(/Colocar à venda|Dar baixa/);
  });

  it("test_mov_03_administrador_ve_dar_baixa_menos_no_alugado", async () => {
    await entrar(ADMIN);
    ordem(cabecalho((await ficha(DISPONIVEL)).desktop), ["Colocar à venda", "Dar baixa", "Excluir"]);
    ordem(cabecalho((await ficha(A_VENDA)).desktop), ["Voltar para a frota", "Dar baixa", "Excluir"]);
    const alugado = cabecalho((await ficha(ALUGADO)).desktop);
    expect(alugado).not.toMatch(/Dar baixa|Colocar à venda|Voltar para a frota/);
    // Dar baixa é um botão de texto no tom de perigo, como o Excluir.
    expect((await ficha(DISPONIVEL)).desktop).toContain('<button type="button" class="wl-btn bg-transparent text-critical-ink">Dar baixa</button>');
  });

  it("test_ven_01_vendedor_e_financeiro_nao_veem_nenhuma_acao_de_status", async () => {
    for (const email of [VENDEDOR, FINANCEIRO]) {
      await entrar(email);
      for (const id of [DISPONIVEL, A_VENDA]) {
        const { desktop, celular } = await ficha(id);
        expect(texto(desktop + celular)).not.toMatch(/Colocar à venda|Voltar para a frota|Dar baixa/);
        expect(celular).not.toContain('aria-label="Mais ações"');
      }
    }
  });

  it("test_ven_01_celular_colocar_a_venda_no_fim_da_ficha_e_mais_acoes_ligado", async () => {
    await entrar(GERENTE);
    const { celular } = await ficha(DISPONIVEL);
    ordem(texto(celular), ["Oficina", "Colocar à venda", "Excluir veículo"]);
    expect(celular).toMatch(/<button type="button" class="wl-btn wl-btn--solid">Colocar à venda<\/button>/);
    // O botão de três pontos abre o menu (não está mais desativado).
    expect(celular).toMatch(/<button type="button" class="wl-icon-btn wl-icon-btn--sm" aria-label="Mais ações" aria-haspopup="menu" aria-expanded="false"/);
    expect(celular.match(/width:44px;height:44px/g)).toHaveLength(2);
  });
});

describe("VEI-23: menu Mais ações do celular", () => {
  const menu = async (id: number) => { const h = html(<MaisAcoesDoCelular v={await veiculos.obter(id)} aoEscolher={nada} abertoDeInicio />); return texto(h.slice(h.indexOf('role="menu"')).replace(/^[^>]*>/, "<i>")); };

  it("test_mov_03_menu_do_administrador_com_dar_baixa_por_ultimo_depois_do_separador", async () => {
    await entrar(ADMIN);
    // Disponível: o "Colocar à venda" já é o botão do fim da ficha e não se repete.
    expect(await menu(DISPONIVEL)).toBe("|Editar|Dar baixa|");
    expect(await menu(A_VENDA)).toBe("|Editar|Voltar para a frota|Dar baixa|");
    const h = html(<MaisAcoesDoCelular v={await veiculos.obter(A_VENDA)} aoEscolher={nada} abertoDeInicio />);
    ordem(h, ['role="menuitem"', "Editar", "Voltar para a frota", 'role="separator"', "text-critical-ink", "Dar baixa"]);
    expect(h).toContain('href="/veiculos/507/editar"');
  });

  it("test_vei_15_menu_do_gerente_sem_dar_baixa", async () => {
    await entrar(GERENTE);
    expect(await menu(A_VENDA)).toBe("|Editar|Voltar para a frota|");
    expect(html(<MaisAcoesDoCelular v={await veiculos.obter(A_VENDA)} aoEscolher={nada} abertoDeInicio />)).not.toContain("separator");
    expect(await menu(DISPONIVEL)).toBe("|Editar|");
  });

  it("test_ven_01_sem_acao_nenhuma_o_botao_mais_acoes_nao_aparece", async () => {
    await entrar(VENDEDOR);
    expect(html(<MaisAcoesDoCelular v={await veiculos.obter(DISPONIVEL)} aoEscolher={nada} />)).toBe("");
  });
});

describe("VEN-01: Colocar à venda", () => {
  it("test_ven_01_dialogo_com_valor_de_venda_e_referencia_fipe", async () => {
    await entrar(GERENTE);
    const v = await veiculos.obter(DISPONIVEL);
    const t = texto(janela(ColocarAVenda, v));
    ordem(t, [
      "Colocar a SAK-1D39 à venda?",
      "A moto sai da frota de locação e não aparece mais na Nova locação. O estoque à venda começa a contar hoje.",
      "Valor de venda",
      "Referência FIPE",
      "Opcional. Aparece ao lado do valor de venda.",
      "Cancelar",
      "Colocar à venda",
    ]);
    // Os dois campos são de dinheiro, sempre digitáveis (a rotina da FIPE é da fase 2).
    expect(janela(ColocarAVenda, v).match(/inputMode="numeric"/g)).toHaveLength(2);
    expect(janela(ColocarAVenda, v)).not.toMatch(/readOnly|readonly/);
    // Celular: gaveta de baixo, a principal em cima.
    const celular = janela(ColocarAVenda, v, { celular: true });
    expect(celular).toContain("wl-gaveta--baixo");
    ordem(texto(celular), ["Referência FIPE", "Colocar à venda", "Cancelar"]);
    // Carro: "o carro" no lugar de "a moto".
    expect(texto(janela(ColocarAVenda, await veiculos.obter(CARRO)))).toContain("O carro sai da frota de locação");
  });

  it("test_ven_01_valor_vazio_ou_zero_pede_o_valor", async () => {
    await entrar(GERENTE);
    const v = await veiculos.obter(DISPONIVEL);
    for (const valor of ["", "R$ 0,00"]) {
      const h = janela(ColocarAVenda, v, { inicial: { valor, conferir: true } });
      expect(texto(h)).toContain("Informe o valor de venda.");
      expect(h).toContain("wl-field wl-field--error");
    }
    expect(texto(janela(ColocarAVenda, v, { inicial: { valor: "R$ 9.000,00", conferir: true } }))).not.toContain("Informe o valor de venda.");
    // A API recusa do mesmo jeito, no campo.
    const e = await falha(veiculos.colocarAVenda(DISPONIVEL, { valor_venda_centavos: 0 }));
    expect(e.campos?.valor_venda_centavos).toBe("Informe o valor de venda.");
  });

  it("test_ven_01_colocar_a_venda_muda_a_ficha_e_mostra_o_aviso_com_o_valor_da_api", async () => {
    await entrar(GERENTE);
    ajustar(DISPONIVEL, {});
    const depois = await veiculos.colocarAVenda(DISPONIVEL, { valor_venda_centavos: 900000, referencia_fipe_centavos: 1240000 });
    expect(depois.status).toBe("a_venda");
    expect(avisoDeSucesso("colocar_a_venda", depois)).toBe("A SAK-1D39 está à venda por R$ 9.000,00.");
    // Relida, a ficha troca o botão: agora é Voltar para a frota.
    ordem(cabecalho((await ficha(DISPONIVEL)).desktop), ["Editar", "Voltar para a frota", "Excluir"]);
  });

  it("test_vei_15_colocar_a_venda_sem_plano_mostra_a_recusa_da_api_no_dialogo", async () => {
    await entrar(GERENTE);
    ajustar(DISPONIVEL, { semPlano: true });
    const e = await falha(veiculos.colocarAVenda(DISPONIVEL, { valor_venda_centavos: 900000 }));
    expect([e.status, e.codigo]).toEqual([409, "VEI-15"]);
    const h = janela(ColocarAVenda, await veiculos.obter(DISPONIVEL), { inicial: { valor: "R$ 9.000,00", erro: e } });
    ordem(texto(h), ["Colocar a SAK-1D39 à venda?", "A tabela de preços desta moto não está preenchida. Preencha para alugar ou colocar à venda.", "A moto sai da frota de locação", "Valor de venda"]);
    expect(h).toContain('class="wl-note wl-note--critical" role="alert"');
  });

  it("test_ven_01_403_aparece_como_a_api_manda", async () => {
    await entrar(VENDEDOR);
    const e = await falha(veiculos.colocarAVenda(DISPONIVEL, { valor_venda_centavos: 900000 }));
    expect(e.status).toBe(403);
    await entrar(GERENTE);
    expect(texto(janela(ColocarAVenda, await veiculos.obter(DISPONIVEL), { inicial: { erro: e } }))).toContain("Seu perfil não tem acesso a esta ação.");
  });
});

describe("VEI-15, VEI-18: Voltar para a frota", () => {
  it("test_vei_15_dialogo_comum_e_sem_plano", async () => {
    await entrar(GERENTE);
    const comum = texto(janela(VoltarParaFrota, await veiculos.obter(A_VENDA)));
    ordem(comum, [
      "Voltar a QYB-5H60 para a frota?",
      "A moto sai do estoque à venda e volta a aparecer na Nova locação. Se ela for colocada à venda de novo, os dias em estoque recomeçam do zero.",
      "Cancelar",
      "Voltar para a frota",
    ]);
    ajustar(A_VENDA, { semPlano: true });
    const semPlano = texto(janela(VoltarParaFrota, await veiculos.obter(A_VENDA)));
    expect(semPlano).toContain(
      "A moto sai do estoque à venda, mas fica indisponível, com o motivo Sem preço · ligue um plano, porque não tem nenhum plano ligado. Ligue um plano em Planos e preços para alugar.",
    );
    expect(textosDaAcao({ placa: "UEF8L63", tipo_veiculo: "carro", aviso_preco: null }).voltar_para_frota.texto).toBe(
      "O carro sai do estoque à venda e volta a aparecer na Nova locação. Se ele for colocado à venda de novo, os dias em estoque recomeçam do zero.",
    );
  });

  it("test_vei_15_voltar_para_a_frota_disponivel_ou_indisponivel_como_a_api_devolve", async () => {
    await entrar(GERENTE);
    ajustar(A_VENDA, {});
    const depois = await veiculos.voltarParaFrota(A_VENDA);
    expect(depois.status).toBe("disponivel");
    expect(avisoDeSucesso("voltar_para_frota", depois)).toBe("A QYB-5H60 voltou para a frota.");
    ordem(cabecalho((await ficha(A_VENDA)).desktop), ["Editar", "Colocar à venda", "Excluir"]);
    desfazer.pop()?.();
    ajustar(A_VENDA, { semPlano: true });
    const semPreco = await veiculos.voltarParaFrota(A_VENDA);
    expect([semPreco.status, semPreco.motivo_status]).toEqual(["indisponivel", "Sem preço · ligue um plano"]);
    expect(avisoDeSucesso("voltar_para_frota", semPreco)).toBe("A QYB-5H60 voltou para a frota, indisponível: sem preço.");
  });

  it("test_vei_15_venda_aberta_troca_o_dialogo_com_ver_a_venda", async () => {
    await entrar(GERENTE);
    ajustar(A_VENDA, { vendaAberta: { id: 177, codigo: "VEN-0177" } });
    const e = await falha(veiculos.voltarParaFrota(A_VENDA));
    expect([e.status, e.codigo, e.detalhes]).toEqual([409, "VEN-10", { venda_id: 177 }]);
    const h = janela(VoltarParaFrota, await veiculos.obter(A_VENDA), { inicial: { erro: e } });
    ordem(texto(h), ["Voltar a QYB-5H60 para a frota?", "Este veículo tem uma venda em andamento (VEN-0177).", "Encerre ou marque a venda como perdida antes de voltar a moto para a frota.", "Fechar", "Ver a venda"]);
    expect(h).toContain('<a class="wl-btn wl-btn--solid" href="/vendas/177">Ver a venda</a>');
    expect(texto(h)).not.toContain("Cancelar");
    // Celular: "Ver a venda" em cima.
    ordem(texto(janela(VoltarParaFrota, await veiculos.obter(A_VENDA), { celular: true, inicial: { erro: e } })), ["Ver a venda", "Fechar"]);
  });
});

describe("MOV-03: Dar baixa", () => {
  it("test_mov_03_dialogo_da_baixa_com_aviso_motivos_e_descricao", async () => {
    await entrar(ADMIN);
    const v = await veiculos.obter(DISPONIVEL);
    const h = janela(DarBaixa, v);
    ordem(texto(h), [
      "Dar baixa na SAK-1D39?",
      "A baixa não se desfaz. A moto sai da frota e das listas e fica só no histórico. Uma movimentação aberta é cancelada.",
      "Motivo da baixa",
      "Perda total",
      "Roubo",
      "Sucata",
      "Outro",
      "Descrição",
      "0/200",
      "Opcional. Ex.: boletim de ocorrência 4512/2026.",
      "Cancelar",
      "Dar baixa",
    ]);
    expect(h).toContain('class="wl-note wl-note--critical" role="alert"');
    expect(h.match(/role="radio" aria-checked="false"/g)).toHaveLength(4);
    expect(h).toContain('<button type="button" class="wl-btn bg-critical text-on-critical">Dar baixa</button>');
    // No Outro, a descrição é obrigatória: a dica de "Opcional" sai.
    expect(texto(janela(DarBaixa, v, { inicial: { motivo: "outro" } }))).not.toContain("Opcional.");
    expect(janela(DarBaixa, v, { inicial: { motivo: "roubo", descricao: "Boletim de ocorrência 4512/2026." } })).toContain('role="radio" aria-checked="true"');
    expect(texto(janela(DarBaixa, v, { inicial: { motivo: "roubo", descricao: "Boletim de ocorrência 4512/2026." } }))).toContain("32/200");
  });

  it("test_mov_03_aviso_baixar_da_api_com_a_movimentacao_aberta", async () => {
    await entrar(ADMIN);
    expect((await veiculos.obter(DISPONIVEL)).acoes.aviso_baixar).toBeNull();
    ajustar(DISPONIVEL, { movimentacaoAberta: "MOV-0002" });
    const v = await veiculos.obter(DISPONIVEL);
    expect(v.acoes.aviso_baixar).toBe("A MOV-0002 será cancelada.");
    ordem(texto(janela(DarBaixa, v)), ["Uma movimentação aberta é cancelada.", "A MOV-0002 será cancelada.", "Motivo da baixa"]);
  });

  it("test_vei_23_validacao_da_baixa_motivo_outro_e_200_caracteres", async () => {
    expect(errosDaBaixa(null, "")).toEqual({ motivo: "Escolha o motivo da baixa." });
    expect(errosDaBaixa("roubo", "")).toEqual({});
    expect(errosDaBaixa("outro", "   ")).toEqual({ descricao: "Descreva o motivo da baixa." });
    expect(errosDaBaixa("outro", "Moto parada no pátio")).toEqual({});
    expect(errosDaBaixa("sucata", "a".repeat(200))).toEqual({});
    expect(errosDaBaixa("sucata", "a".repeat(201))).toEqual({ descricao: "Use até 200 caracteres." });
    await entrar(ADMIN);
    const v = await veiculos.obter(DISPONIVEL);
    const semMotivo = janela(DarBaixa, v, { inicial: { conferir: true } });
    expect(texto(semMotivo)).toContain("Escolha o motivo da baixa.");
    const outro = janela(DarBaixa, v, { inicial: { motivo: "outro", conferir: true } });
    ordem(texto(outro), ["Descrição", "0/200", "Descreva o motivo da baixa."]);
    const longa = texto(janela(DarBaixa, v, { inicial: { motivo: "outro", descricao: "b".repeat(214), conferir: true } }));
    ordem(longa, ["214/200", "Use até 200 caracteres."]);
    // A API confere o mesmo (400 em `descricao`) e a tela mostra no campo.
    const e = await falha(veiculos.baixar(DISPONIVEL, { motivo: "outro", descricao: "" }));
    expect([e.status, e.campos?.descricao]).toEqual([400, "Descreva o motivo da baixa."]);
    expect(texto(janela(DarBaixa, v, { inicial: { motivo: "outro", erro: e } }))).toContain("Descreva o motivo da baixa.");
  });

  it("test_mov_03_baixa_registrada_com_o_motivo_no_aviso", async () => {
    await entrar(ADMIN);
    ajustar(DISPONIVEL, {});
    const depois = await veiculos.baixar(DISPONIVEL, { motivo: "roubo", descricao: "Boletim 4512/2026" });
    expect(depois.status).toBe("baixado");
    expect(avisoDeSucesso("baixar", depois, "roubo")).toBe("Baixa da SAK-1D39 registrada: roubo.");
    expect(avisoDeSucesso("baixar", depois, "perda_total")).toBe("Baixa da SAK-1D39 registrada: perda total.");
    expect(avisoDeSucesso("baixar", depois, "outro")).toBe("Baixa da SAK-1D39 registrada.");
  });

  it("test_mov_03_recusas_da_api_alugado_venda_aberta_e_perfil", async () => {
    await entrar(ADMIN);
    const alugada = await falha(veiculos.baixar(ALUGADO, { motivo: "roubo", descricao: "" }));
    expect([alugada.status, alugada.codigo]).toEqual([409, "transicao_veiculo"]);
    const h = janela(DarBaixa, await veiculos.obter(ALUGADO), { inicial: { erro: alugada } });
    ordem(texto(h), ["Dar baixa na QXA-4B21?", "Esta moto está alugada. Dê baixa depois da devolução.", "Fechar"]);
    expect(texto(h)).not.toMatch(/Motivo da baixa|Cancelar/);

    ajustar(A_VENDA, { vendaAberta: { id: 177, codigo: "VEN-0177" } });
    const venda = await falha(veiculos.baixar(A_VENDA, { motivo: "roubo", descricao: "" }));
    const comVenda = janela(DarBaixa, await veiculos.obter(A_VENDA), { inicial: { erro: venda } });
    ordem(texto(comVenda), ["Este veículo tem uma venda em andamento (VEN-0177).", "Encerre ou marque a venda como perdida antes de dar baixa.", "Fechar", "Ver a venda"]);

    await entrar(GERENTE);
    const proibido = await falha(veiculos.baixar(DISPONIVEL, { motivo: "roubo", descricao: "" }));
    expect(proibido.status).toBe(403);
    await entrar(ADMIN);
    expect(texto(janela(DarBaixa, await veiculos.obter(DISPONIVEL), { inicial: { motivo: "roubo", erro: proibido } }))).toContain("Seu perfil não tem acesso a esta ação.");
  });
});
