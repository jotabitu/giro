"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Ellipsis } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Aviso, CampoDeDinheiro, Dialogo, Gaveta, Icone } from "@/design-system";
import { ErroApi, veiculos, type MotivoDaBaixa, type Veiculo, type VeiculoDetalhe } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dinheiro, placa } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

// VEI-23 (T-518): Colocar à venda (VEN-01), Voltar para a frota (VEI-15, VEI-18) e Dar baixa (MOV-03) na ficha do veículo.
// Referência: docs/telas/html/Veiculo-Desktop.dc.html e Veiculo-Mobile.dc.html ("Estados desta tela").
// A API decide quem vê cada ação (`acoes`) e recusa o que não pode; a tela só mostra o que vem e repete a validação da VEI-23.

export type AcaoDeStatus = "colocar_a_venda" | "voltar_para_frota" | "baixar";

const PERIGO = "wl-btn bg-critical text-on-critical";
const LIMITE_DA_DESCRICAO = 200;

const MOTIVOS: { valor: MotivoDaBaixa; rotulo: string }[] = [
  { valor: "perda_total", rotulo: "Perda total" },
  { valor: "roubo", rotulo: "Roubo" },
  { valor: "sucata", rotulo: "Sucata" },
  { valor: "outro", rotulo: "Outro" },
];

/** "A moto" ou "O carro" e as concordâncias da VEI-23 ("Para carro, 'o carro' no lugar de 'a moto'"). */
export function palavrasDoVeiculo(v: Pick<Veiculo, "tipo_veiculo">) {
  const moto = v.tipo_veiculo !== "carro";
  return {
    oVeiculo: moto ? "a moto" : "o carro",
    OVeiculo: moto ? "A moto" : "O carro",
    ele: moto ? "ela" : "ele",
    colocado: moto ? "colocada" : "colocado",
    alugado: moto ? "Esta moto está alugada." : "Este carro está alugado.",
  };
}

/** Os textos dos diálogos, como a VEI-23. `semPlano` vem do `aviso_preco` da API (VEI-15). */
export function textosDaAcao(v: Pick<Veiculo, "placa" | "tipo_veiculo" | "aviso_preco">) {
  const p = placa(v.placa);
  const w = palavrasDoVeiculo(v);
  return {
    colocar_a_venda: {
      titulo: `Colocar a ${p} à venda?`,
      texto: `${w.OVeiculo} sai da frota de locação e não aparece mais na Nova locação. O estoque à venda começa a contar hoje.`,
    },
    voltar_para_frota: {
      titulo: `Voltar a ${p} para a frota?`,
      texto: v.aviso_preco
        ? `${w.OVeiculo} sai do estoque à venda, mas fica indisponível, com o motivo Sem preço · ligue um plano, porque não tem nenhum plano ligado. Ligue um plano em Planos e preços para alugar.`
        : `${w.OVeiculo} sai do estoque à venda e volta a aparecer na Nova locação. Se ${w.ele} for ${w.colocado} à venda de novo, os dias em estoque recomeçam do zero.`,
      depoisDaVenda: `Encerre ou marque a venda como perdida antes de voltar ${w.oVeiculo} para a frota.`,
    },
    baixar: {
      titulo: `Dar baixa na ${p}?`,
      texto: `A baixa não se desfaz. ${w.OVeiculo} sai da frota e das listas e fica só no histórico. Uma movimentação aberta é cancelada.`,
      depoisDaVenda: "Encerre ou marque a venda como perdida antes de dar baixa.",
      alugado: `${w.alugado} Dê baixa depois da devolução.`,
    },
  };
}

/** O aviso no alto da ficha depois da ação, com o que a API devolveu (VEI-23, "Aviso de sucesso na ficha"). */
export function avisoDeSucesso(acao: AcaoDeStatus, depois: Pick<Veiculo, "placa" | "status" | "valor_venda_centavos">, motivo?: MotivoDaBaixa): string {
  const p = placa(depois.placa);
  if (acao === "colocar_a_venda") return depois.valor_venda_centavos != null ? `A ${p} está à venda por ${dinheiro(depois.valor_venda_centavos)}.` : `A ${p} está à venda.`;
  if (acao === "voltar_para_frota") return depois.status === "indisponivel" ? `A ${p} voltou para a frota, indisponível: sem preço.` : `A ${p} voltou para a frota.`;
  const rotulo = MOTIVOS.find((m) => m.valor === motivo)?.rotulo;
  return motivo && motivo !== "outro" && rotulo ? `Baixa da ${p} registrada: ${rotulo.toLowerCase()}.` : `Baixa da ${p} registrada.`;
}

/** O 409 `VEN-10` da trava do estoque, com a venda que o "Ver a venda" abre. */
function vendaAberta(e: unknown): { mensagem: string; vendaId: number | null } | null {
  if (!(e instanceof ErroApi) || e.status !== 409 || e.codigo !== "VEN-10") return null;
  const id = Number(e.detalhes?.venda_id);
  return { mensagem: e.message, vendaId: Number.isFinite(id) && id > 0 ? id : null };
}

const recusaDeAlugado = (e: unknown) => e instanceof ErroApi && e.status === 409 && e.codigo === "transicao_veiculo" && e.detalhes?.de === "alugado";

/** Só dos testes (como o `abertoDeInicio` do Excluir): o diálogo já preenchido, conferido ou com a recusa da API, para ver o que ele diz sem clicar. */
export type EstadoInicial = { valor?: string; fipe?: string; motivo?: MotivoDaBaixa; descricao?: string; conferir?: boolean; erro?: unknown };

type Comum = { v: VeiculoDetalhe; celular?: boolean; aoFechar: () => void; aoConcluir: (mensagem: string) => void; inicial?: EstadoInicial };

/** Desktop: janela no centro, a principal à direita; celular: gaveta de baixo, a principal em cima e na largura toda (as referências). */
function Janela({ celular, titulo, aoFechar, travada, principal, saida, children }: { celular?: boolean; titulo: string; aoFechar: () => void; travada: boolean; principal: ReactNode; saida: ReactNode; children: ReactNode }) {
  const acoes = celular ? (
    <div className="flex w-full flex-col gap-2 [&_.wl-btn]:w-full [&_.wl-btn]:justify-center">
      {principal}
      {saida}
    </div>
  ) : (
    <>
      {saida}
      {principal}
    </>
  );
  const props = { aberto: true, aoFechar: () => !travada && aoFechar(), titulo, acoes, fecharAoClicarFora: !travada };
  const corpo = <div className="flex flex-col gap-[14px]">{children}</div>;
  return celular ? (
    <Gaveta {...props} lado="baixo">
      {corpo}
    </Gaveta>
  ) : (
    <Dialogo {...props} tamanho="pequeno">
      {corpo}
    </Dialogo>
  );
}

const Texto = ({ children }: { children: ReactNode }) => <p className="m-0 text-body text-ink-muted">{children}</p>;

function Botao({ perigo, solido, enviando, rotulo, rotuloEnviando, aoClicar }: { perigo?: boolean; solido?: boolean; enviando?: boolean; rotulo: string; rotuloEnviando?: string; aoClicar: () => void }) {
  return (
    <button type="button" className={perigo ? PERIGO : solido ? "wl-btn wl-btn--solid" : "wl-btn"} disabled={enviando} onClick={aoClicar}>
      {enviando && rotuloEnviando ? rotuloEnviando : rotulo}
    </button>
  );
}

/** O diálogo troca de botões com a venda aberta (409 `VEN-10`): a frase da API, o que fazer e "Ver a venda". */
function JanelaDaVendaAberta({ celular, titulo, venda, depois, aoFechar }: { celular?: boolean; titulo: string; venda: { mensagem: string; vendaId: number | null }; depois: string; aoFechar: () => void }) {
  return (
    <Janela
      celular={celular}
      titulo={titulo}
      aoFechar={aoFechar}
      travada={false}
      principal={
        venda.vendaId ? (
          <Link href={`/vendas/${venda.vendaId}`} className="wl-btn wl-btn--solid">
            Ver a venda
          </Link>
        ) : null
      }
      saida={<Botao rotulo="Fechar" aoClicar={aoFechar} />}
    >
      <Aviso tom="critico">{venda.mensagem}</Aviso>
      <Texto>{depois}</Texto>
    </Janela>
  );
}

/** Relê a ficha (e as listas e contagens que mudam com o status) depois da ação ou de uma recusa que diz que a ficha mudou. */
function useReler(id: number) {
  const cache = useQueryClient();
  return () => Promise.all([cache.invalidateQueries({ queryKey: ["veiculo", id] }), cache.invalidateQueries({ queryKey: ["veiculos"] }), cache.invalidateQueries({ queryKey: ["contadores"] })]);
}

/** Colocar à venda (VEN-01): valor de venda obrigatório e referência FIPE opcional, sempre digitável até a rotina da fase 2. */
export function ColocarAVenda({ v, celular, aoFechar, aoConcluir, inicial }: Comum) {
  const t = textosDaAcao(v).colocar_a_venda;
  const reler = useReler(v.id);
  const [valor, setValor] = useState(inicial?.valor ?? "");
  const [fipe, setFipe] = useState(inicial?.fipe ?? "");
  const [faltaValor, setFaltaValor] = useState(Boolean(inicial?.conferir) && !centavosDoTexto(inicial?.valor ?? ""));
  const enviar = useMutation({
    mutationFn: (corpo: { valor_venda_centavos: number; referencia_fipe_centavos?: number | null }) => veiculos.colocarAVenda(v.id, corpo),
    onSuccess: async (depois) => {
      await reler();
      aoConcluir(avisoDeSucesso("colocar_a_venda", depois));
    },
    onError: (e) => {
      if (e instanceof ErroApi && e.status === 409) void reler();
    },
  });
  const confirmar = () => {
    const centavos = centavosDoTexto(valor);
    if (!centavos) return setFaltaValor(true);
    setFaltaValor(false);
    const referencia = fipe.trim() ? centavosDoTexto(fipe) : null;
    enviar.mutate(referencia ? { valor_venda_centavos: centavos, referencia_fipe_centavos: referencia } : { valor_venda_centavos: centavos });
  };
  const erro = enviar.error ?? inicial?.erro ?? null;
  const doCampo = (c: string) => campoDoErro(erro, c);
  // VEI-15 e as outras recusas (403, 409) aparecem como a API mandou, no alto do diálogo; os 400 ficam no campo.
  const recusa = erro && !(erro instanceof ErroApi && erro.status === 400 && erro.campos) ? mensagemDoErro(erro) : null;
  return (
    <Janela
      celular={celular}
      titulo={t.titulo}
      aoFechar={aoFechar}
      travada={enviar.isPending}
      principal={<Botao solido rotulo="Colocar à venda" rotuloEnviando="Colocando à venda…" enviando={enviar.isPending} aoClicar={confirmar} />}
      saida={<Botao rotulo="Cancelar" enviando={enviar.isPending} aoClicar={aoFechar} />}
    >
      {recusa && <Aviso tom="critico">{recusa}</Aviso>}
      <Texto>{t.texto}</Texto>
      <CampoDeDinheiro rotulo="Valor de venda" prefixo mono cheio placeholder="R$ 0,00" value={valor} onChange={(e) => (setValor(e.target.value), setFaltaValor(false))} erro={faltaValor ? "Informe o valor de venda." : doCampo("valor_venda_centavos")} />
      <CampoDeDinheiro rotulo="Referência FIPE" prefixo mono cheio placeholder="R$ 0,00" value={fipe} onChange={(e) => setFipe(e.target.value)} erro={doCampo("referencia_fipe_centavos")} dica="Opcional. Aparece ao lado do valor de venda." />
    </Janela>
  );
}

/** Voltar para a frota: sem campo; sem plano ligado, o texto da VEI-15. A venda aberta troca o diálogo (409 `VEN-10`). */
export function VoltarParaFrota({ v, celular, aoFechar, aoConcluir, inicial }: Comum) {
  const t = textosDaAcao(v).voltar_para_frota;
  const reler = useReler(v.id);
  const enviar = useMutation({
    mutationFn: () => veiculos.voltarParaFrota(v.id),
    onSuccess: async (depois) => {
      await reler();
      aoConcluir(avisoDeSucesso("voltar_para_frota", depois));
    },
    onError: (e) => {
      if (e instanceof ErroApi && e.status === 409) void reler();
    },
  });
  const erro = enviar.error ?? inicial?.erro ?? null;
  const venda = vendaAberta(erro);
  if (venda) return <JanelaDaVendaAberta celular={celular} titulo={t.titulo} venda={venda} depois={t.depoisDaVenda} aoFechar={aoFechar} />;
  return (
    <Janela
      celular={celular}
      titulo={t.titulo}
      aoFechar={aoFechar}
      travada={enviar.isPending}
      principal={<Botao solido rotulo="Voltar para a frota" rotuloEnviando="Voltando…" enviando={enviar.isPending} aoClicar={() => enviar.mutate()} />}
      saida={<Botao rotulo="Cancelar" enviando={enviar.isPending} aoClicar={aoFechar} />}
    >
      {erro != null && <Aviso tom="critico">{mensagemDoErro(erro)}</Aviso>}
      <Texto>{t.texto}</Texto>
    </Janela>
  );
}

function MotivoDaBaixaEscolha({ valor, aoMudar, erro }: { valor: MotivoDaBaixa | null; aoMudar: (m: MotivoDaBaixa) => void; erro?: string }) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-[6px] ${erro ? "wl-field--error" : ""}`}>
      <span id={id} className="wl-field__label">
        Motivo da baixa
      </span>
      <div role="radiogroup" aria-labelledby={id} className="grid grid-cols-2 gap-2">
        {MOTIVOS.map((m) => {
          const marcado = valor === m.valor;
          return (
            <button
              key={m.valor}
              type="button"
              role="radio"
              aria-checked={marcado}
              onClick={() => aoMudar(m.valor)}
              className={`flex min-h-[44px] items-center gap-[10px] rounded-[16px] bg-surface px-[14px] py-3 text-left text-body ${marcado ? "shadow-[inset_0_0_0_2px_var(--ink)]" : "shadow-[inset_0_0_0_1px_var(--line)]"}`}
            >
              <span aria-hidden="true" className={`size-4 shrink-0 rounded-full ${marcado ? "shadow-[inset_0_0_0_5px_var(--ink)]" : "shadow-[inset_0_0_0_1.5px_var(--ink-muted)]"}`} />
              {m.rotulo}
            </button>
          );
        })}
      </div>
      {erro && <span className="wl-field__hint">{erro}</span>}
    </div>
  );
}

function Descricao({ valor, aoMudar, erro, outro }: { valor: string; aoMudar: (t: string) => void; erro?: string; outro: boolean }) {
  const id = useId();
  const apoio = erro ?? (outro ? undefined : "Opcional. Ex.: boletim de ocorrência 4512/2026.");
  return (
    <div className={`wl-field wl-field--cheio ${erro ? "wl-field--error" : ""}`}>
      <label className="wl-field__label flex justify-between" htmlFor={id}>
        <span>Descrição</span>
        <span aria-label={`${valor.length} de ${LIMITE_DA_DESCRICAO} caracteres`}>
          {valor.length}/{LIMITE_DA_DESCRICAO}
        </span>
      </label>
      <textarea id={id} className="wl-input h-auto min-h-[84px] resize-none pt-[10px]" rows={3} value={valor} onChange={(e) => aoMudar(e.target.value)} aria-invalid={erro ? true : undefined} aria-describedby={apoio ? `${id}-dica` : undefined} />
      {apoio && (
        <span id={`${id}-dica`} className="wl-field__hint">
          {apoio}
        </span>
      )}
    </div>
  );
}

/** Erros da VEI-23 que a tela repete antes de mandar (a API confere os mesmos, 400 no campo). */
export function errosDaBaixa(motivo: MotivoDaBaixa | null, descricao: string): { motivo?: string; descricao?: string } {
  const erros: { motivo?: string; descricao?: string } = {};
  if (!motivo) erros.motivo = "Escolha o motivo da baixa.";
  if (descricao.length > LIMITE_DA_DESCRICAO) erros.descricao = "Use até 200 caracteres.";
  else if (motivo === "outro" && !descricao.trim()) erros.descricao = "Descreva o motivo da baixa.";
  return erros;
}

/** Dar baixa (só o administrador): o aviso de perigo, o motivo em botões de opção e a descrição com contador. */
export function DarBaixa({ v, celular, aoFechar, aoConcluir, inicial }: Comum) {
  const t = textosDaAcao(v).baixar;
  const reler = useReler(v.id);
  const [motivo, setMotivo] = useState<MotivoDaBaixa | null>(inicial?.motivo ?? null);
  const [descricao, setDescricao] = useState(inicial?.descricao ?? "");
  const [conferir, setConferir] = useState(Boolean(inicial?.conferir));
  const enviar = useMutation({
    mutationFn: (corpo: { motivo: MotivoDaBaixa; descricao: string }) => veiculos.baixar(v.id, corpo),
    onSuccess: async (depois, corpo) => {
      await reler();
      aoConcluir(avisoDeSucesso("baixar", depois, corpo.motivo));
    },
    onError: (e) => {
      if (e instanceof ErroApi && e.status === 409) void reler();
    },
  });
  const locais = conferir ? errosDaBaixa(motivo, descricao) : {};
  const confirmar = () => {
    setConferir(true);
    const erros = errosDaBaixa(motivo, descricao);
    if (!motivo || erros.motivo || erros.descricao) return;
    enviar.mutate({ motivo, descricao: descricao.trim() });
  };
  const erro = enviar.error ?? inicial?.erro ?? null;
  const venda = vendaAberta(erro);
  if (venda) return <JanelaDaVendaAberta celular={celular} titulo={t.titulo} venda={venda} depois={t.depoisDaVenda} aoFechar={aoFechar} />;
  if (recusaDeAlugado(erro)) {
    return (
      <Janela celular={celular} titulo={t.titulo} aoFechar={aoFechar} travada={false} principal={null} saida={<Botao rotulo="Fechar" aoClicar={aoFechar} />}>
        <Aviso tom="critico">{t.alugado}</Aviso>
      </Janela>
    );
  }
  const recusa = erro && !(erro instanceof ErroApi && erro.status === 400 && erro.campos) ? mensagemDoErro(erro) : null;
  return (
    <Janela
      celular={celular}
      titulo={t.titulo}
      aoFechar={aoFechar}
      travada={enviar.isPending}
      principal={<Botao perigo rotulo="Dar baixa" rotuloEnviando="Dando baixa…" enviando={enviar.isPending} aoClicar={confirmar} />}
      saida={<Botao rotulo="Cancelar" enviando={enviar.isPending} aoClicar={aoFechar} />}
    >
      {recusa && <Aviso tom="critico">{recusa}</Aviso>}
      <Aviso tom="critico">{t.texto}</Aviso>
      {/* MOV-03: com a movimentação aberta, a API manda a frase pronta ("A MOV-0002 será cancelada."). */}
      {v.acoes.aviso_baixar && <Aviso tom="atencao">{v.acoes.aviso_baixar}</Aviso>}
      <MotivoDaBaixaEscolha valor={motivo} aoMudar={setMotivo} erro={locais.motivo ?? campoDoErro(erro, "motivo")} />
      <Descricao valor={descricao} aoMudar={setDescricao} outro={motivo === "outro"} erro={locais.descricao ?? campoDoErro(erro, "descricao")} />
    </Janela>
  );
}

/** A janela da ação escolhida. Uma por vez, para as duas árvores da ficha (desktop e celular). */
export function JanelaDeStatus({ acao, ...comum }: Comum & { acao: AcaoDeStatus }) {
  if (acao === "colocar_a_venda") return <ColocarAVenda {...comum} />;
  if (acao === "voltar_para_frota") return <VoltarParaFrota {...comum} />;
  return <DarBaixa {...comum} />;
}

/** O aviso verde no alto da ficha depois da ação (VEI-23). */
export function AvisoDaAcao({ mensagem }: { mensagem: string }) {
  return (
    <p role="status" className="m-0 flex items-center gap-[10px] rounded-[16px] bg-success-soft px-4 py-3 text-body text-success-ink">
      {mensagem}
    </p>
  );
}

/**
 * Menu "Mais ações" do celular (VEI-23): "Editar"; "Voltar para a frota" (o "Colocar à venda" já é o botão do fim da ficha e não se repete);
 * depois de um separador, "Dar baixa" no tom de perigo. Só o que a API libera em `acoes`. Sem nada para mostrar, o botão não aparece.
 */
export function MaisAcoesDoCelular({ v, aoEscolher, abertoDeInicio = false }: { v: VeiculoDetalhe; aoEscolher: (a: AcaoDeStatus) => void; abertoDeInicio?: boolean }) {
  const [aberto, setAberto] = useState(abertoDeInicio);
  const caixa = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!aberto) return;
    const fora = (e: PointerEvent) => {
      if (caixa.current && !caixa.current.contains(e.target as Node)) setAberto(false);
    };
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberto(false);
    };
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", tecla);
    caixa.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    return () => {
      document.removeEventListener("pointerdown", fora);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);
  const a = v.acoes;
  if (!a.editar && !a.voltar_para_frota && !a.baixar) return null;
  const escolher = (acao: AcaoDeStatus) => {
    setAberto(false);
    aoEscolher(acao);
  };
  const item = "wl-menu__item w-full border-0 bg-transparent text-left text-body";
  return (
    <div ref={caixa} className="relative shrink-0">
      <button type="button" className="wl-icon-btn wl-icon-btn--sm" aria-label="Mais ações" aria-haspopup="menu" aria-expanded={aberto} onClick={() => setAberto((x) => !x)} style={{ width: 44, height: 44 }}>
        <Icone de={Ellipsis} />
      </button>
      {aberto && (
        <div role="menu" aria-label="Mais ações" className="wl-menu left-auto w-[260px]">
          {a.editar && (
            <Link role="menuitem" href={`/veiculos/${v.id}/editar`} className={`${item} text-ink no-underline`}>
              Editar
            </Link>
          )}
          {a.voltar_para_frota && (
            <button role="menuitem" type="button" className={item} onClick={() => escolher("voltar_para_frota")}>
              Voltar para a frota
            </button>
          )}
          {a.baixar && (
            <>
              {(a.editar || a.voltar_para_frota) && <div role="separator" className="mx-0 my-1 h-px bg-line" />}
              <button role="menuitem" type="button" className={`${item} text-critical-ink`} onClick={() => escolher("baixar")}>
                Dar baixa
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
