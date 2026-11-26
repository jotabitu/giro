"use client";

import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type ReactNode } from "react";
import { Dialogo, Gaveta } from "@/design-system";
import { ErroApi } from "@/lib/api";
import { deixarAvisoParaALista } from "@/lib/aviso-da-lista";
import { mensagemDoErro } from "@/lib/erros";

// "Excluir" da ficha do veículo (VEI-22) e da ficha do cliente (CLI-13). Referência: Veiculo-Desktop/Mobile e Cliente-Detalhe-Desktop/Mobile.
// A API decide: `acoes.excluir` traz o título e o texto da confirmação (`permitido`) ou o motivo e o caminho do aviso.
// A tela só escolhe o botão e mostra o que vem. Os botões ("Excluir veículo", "Manter veículo", "Fechar") são da tela.

/** O que a ficha recebe em `acoes.excluir` (os dois contratos têm estes campos). */
export type AcaoDeExcluir = { permitido: boolean; titulo: string; texto: string | null; motivo: string | null; caminho: string | null };

/** Recusas que mudam o que a ficha diz (histórico novo, cliente bloqueado): com elas a tela relê a ficha e a janela vira o aviso da API. */
export function recusaMudaAFicha(e: unknown): boolean {
  return e instanceof ErroApi && e.status === 409 && (e.codigo === "VEI-22" || e.codigo === "CLI-13" || e.codigo === "transicao_cliente");
}

/** Chama a rota e, deu certo, deixa a `mensagem` da API para a lista e volta para ela. Uma recusa sobe como veio. */
export async function excluirEVoltar(executar: () => Promise<{ mensagem: string }>, lista: string, navegar: (rota: string) => void, antes?: () => Promise<unknown>): Promise<string> {
  const { mensagem } = await executar();
  await antes?.();
  deixarAvisoParaALista(lista, mensagem);
  navegar(lista);
  return mensagem;
}

const PERIGO = "wl-btn bg-critical text-on-critical";
const DE_TEXTO = "wl-btn bg-transparent text-critical-ink";

type Janela = {
  acao: AcaoDeExcluir;
  celular?: boolean;
  /** "veículo" ou "cliente": os botões "Excluir veículo" e "Manter veículo". */
  coisa: string;
  enviando?: boolean;
  /** A recusa que não muda a ficha (403, rede), como a API mandou. */
  erro?: string | null;
  aoConfirmar: () => void;
  aoFechar: () => void;
  /** O botão do caminho no aviso ("Colocar à venda", "Inativar cliente"), quando a ficha o oferece. */
  caminho?: ReactNode;
};

/** A confirmação (sem histórico) ou o aviso (com histórico). Desktop: janela no centro; celular: gaveta de baixo, botões na largura toda. */
export function JanelaDeExcluir({ acao, celular, coisa, enviando, erro, aoConfirmar, aoFechar, caminho }: Janela) {
  const largura = celular ? "w-full justify-center" : "";
  const descricao = (acao.permitido ? acao.texto : [acao.motivo, acao.caminho].filter(Boolean).join(" ")) || undefined;
  const excluir = (
    <button key="excluir" type="button" className={`${PERIGO} ${largura}`} disabled={enviando} onClick={aoConfirmar}>
      {enviando ? "Excluindo…" : `Excluir ${coisa}`}
    </button>
  );
  const manter = (
    <button key="manter" type="button" className={`wl-btn ${largura}`} disabled={enviando} onClick={aoFechar}>
      Manter {coisa}
    </button>
  );
  const fechar = (
    <button key="fechar" type="button" className={`wl-btn ${largura}`} onClick={aoFechar}>
      Fechar
    </button>
  );
  const doCaminho = !acao.permitido && caminho ? <span key="caminho" className={celular ? "flex w-full [&_.wl-btn]:w-full [&_.wl-btn]:justify-center" : "contents"}>{caminho}</span> : null;
  // Desktop: a principal por último, à direita; celular: a principal em cima (as referências).
  const botoes = acao.permitido ? (celular ? [excluir, manter] : [manter, excluir]) : celular ? [doCaminho, fechar] : [fechar, doCaminho];
  const acoes = celular ? <div className="flex w-full flex-col gap-2">{botoes}</div> : <>{botoes}</>;
  const conteudo = erro ? (
    <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
      {erro}
    </p>
  ) : undefined;
  const props = { aberto: true, aoFechar, titulo: acao.titulo, descricao, acoes, fecharAoClicarFora: !enviando };
  return celular ? (
    <Gaveta {...props} lado="baixo">
      {conteudo}
    </Gaveta>
  ) : (
    <Dialogo {...props}>{conteudo}</Dialogo>
  );
}

type Props = {
  acao: AcaoDeExcluir;
  /** Duas árvores na ficha: no desktop, "Excluir" no cabeçalho; no celular, o botão na largura toda no fim da ficha e a gaveta de baixo. */
  celular?: boolean;
  /** "Excluir" no desktop; "Excluir veículo" ou "Excluir cliente" no celular. */
  rotulo: string;
  coisa: string;
  executar: () => Promise<{ mensagem: string }>;
  /** A ficha que a recusa (409) manda reler. */
  chaveDaFicha: QueryKey;
  /** Listas e contagens que mudam quando o cadastro sai. */
  chavesDasListas: QueryKey[];
  /** A lista para onde a tela volta, com a `mensagem` da API ("/veiculos", "/clientes"). */
  lista: string;
  /** O botão do caminho no aviso. Recebe o `fechar` da janela. */
  caminho?: (fechar: () => void) => ReactNode;
  estiloDoBotao?: CSSProperties;
  /** A janela já aberta, para conferir o que ela diz sem clicar (testes). */
  abertoDeInicio?: boolean;
};

/** A janela aberta: o roteador e a gravação só existem enquanto ela está na tela. */
function JanelaAberta({ acao, celular, coisa, executar, chaveDaFicha, chavesDasListas, lista, caminho, aoSair }: Omit<Props, "rotulo" | "estiloDoBotao" | "abertoDeInicio"> & { aoSair: () => void }) {
  const cache = useQueryClient();
  const router = useRouter();
  const excluir = useMutation({
    mutationFn: () => excluirEVoltar(executar, lista, (rota) => router.push(rota), () => Promise.all(chavesDasListas.map((queryKey) => cache.invalidateQueries({ queryKey })))),
    onError: (e) => {
      if (recusaMudaAFicha(e)) void cache.invalidateQueries({ queryKey: chaveDaFicha, exact: true });
    },
  });
  const fechar = () => {
    if (!excluir.isPending) aoSair();
  };
  // Depois do 409 a ficha relida já traz o aviso: o erro só aparece enquanto a confirmação ainda está na tela.
  const erro = excluir.isError && acao.permitido ? mensagemDoErro(excluir.error) : null;
  return <JanelaDeExcluir acao={acao} celular={celular} coisa={coisa} enviando={excluir.isPending} erro={erro} aoConfirmar={() => excluir.mutate()} aoFechar={fechar} caminho={caminho?.(fechar)} />;
}

export function ExcluirCadastro({ rotulo, estiloDoBotao, abertoDeInicio = false, ...janela }: Props) {
  const [aberto, setAberto] = useState(abertoDeInicio);
  return (
    <>
      <button type="button" className={`${DE_TEXTO} ${janela.celular ? "w-full justify-center" : ""}`} style={estiloDoBotao} onClick={() => setAberto(true)}>
        {rotulo}
      </button>
      {aberto && <JanelaAberta {...janela} aoSair={() => setAberto(false)} />}
    </>
  );
}
