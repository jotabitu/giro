import { ErroApi, type AtividadeDoRamo, type CorpoDoRamo, type Ramo, type TrabalhaCom } from "@/lib/api";

/** As quatro marcas da tela; quais combinações valem quem decide é a API (`atividades_aceitas`). */
export type MarcasDoRamo = { locacao: boolean; venda: boolean; motos: boolean; carros: boolean };
export type ChaveDaMarca = keyof MarcasDoRamo;

export function marcasDoRamo(r: Pick<Ramo, "atividade" | "trabalha_com">): MarcasDoRamo {
  return { locacao: r.atividade !== "vende", venda: r.atividade !== "aluga", motos: r.trabalha_com !== "carros", carros: r.trabalha_com !== "motos" };
}

export function atividadeDasMarcas(m: MarcasDoRamo): AtividadeDoRamo | null {
  if (m.locacao && m.venda) return "ambos";
  return m.locacao ? "aluga" : m.venda ? "vende" : null;
}

export function trabalhaComDasMarcas(m: MarcasDoRamo): TrabalhaCom | null {
  if (m.motos && m.carros) return "ambos";
  return m.motos ? "motos" : m.carros ? "carros" : null;
}

/** O corpo do PUT, ou `null` enquanto não há ao menos uma atividade e um tipo marcados. */
export function corpoDoRamo(m: MarcasDoRamo): CorpoDoRamo | null {
  const atividade = atividadeDasMarcas(m);
  const trabalha_com = trabalhaComDasMarcas(m);
  return atividade && trabalha_com ? { atividade, trabalha_com } : null;
}

export function ramoMudou(guardado: Pick<Ramo, "atividade" | "trabalha_com">, m: MarcasDoRamo): boolean {
  const c = corpoDoRamo(m);
  return c !== null && (c.atividade !== guardado.atividade || c.trabalha_com !== guardado.trabalha_com);
}

/** A marca pode ser invertida? Fica sempre uma de cada grupo, e a atividade resultante tem que estar em `atividades_aceitas` (no Essencial, "Locação" não desliga). */
export function podeAlternar(r: Pick<Ramo, "atividades_aceitas">, m: MarcasDoRamo, chave: ChaveDaMarca): boolean {
  const novo = { ...m, [chave]: !m[chave] };
  if (chave === "motos" || chave === "carros") return trabalhaComDasMarcas(novo) !== null;
  const atividade = atividadeDasMarcas(novo);
  return atividade !== null && r.atividades_aceitas.includes(atividade);
}

export type RecusaDoRamo = { mensagem: string; motivo: string; link: { href: string; rotulo: string } | null };

const LINKS_DOS_ABERTOS: Record<string, { href: string; rotulo: string }> = {
  locacoes_vistoria: { href: "/locacoes", rotulo: "Ver locações abertas" },
  vendas_comissoes: { href: "/vendas", rotulo: "Ver vendas abertas" },
};

/** 422 `PLT-12`: o texto é o da API; o link só leva à lista do módulo que a API apontou em `recurso`. */
export function recusaDoRamo(erro: unknown): RecusaDoRamo | null {
  if (!(erro instanceof ErroApi) || erro.status !== 422 || erro.codigo !== "PLT-12") return null;
  const motivo = String(erro.detalhes?.motivo ?? "");
  const link = motivo === "abertos" ? (LINKS_DOS_ABERTOS[String(erro.detalhes?.recurso ?? "")] ?? null) : null;
  return { mensagem: erro.message, motivo, link };
}
