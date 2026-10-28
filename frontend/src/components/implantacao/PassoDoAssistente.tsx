"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { marca as marcaApi, ramo as ramoApi, type AndamentoDoAssistente } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { mensagemDoErro } from "@/lib/erros";
import { destinoAntesDe, destinoDepoisDe } from "@/lib/implantacao";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { CascaDoAssistente } from "./CascaDoAssistente";
import { PassoContrato } from "./PassoContrato";
import { PassoEquipe } from "./PassoEquipe";
import { PassoFilial } from "./PassoFilial";
import { PassoMarca } from "./PassoMarca";
import { PassoPrecos } from "./PassoPrecos";
import { PassoRamo } from "./PassoRamo";
import { PassoRecebimentos } from "./PassoRecebimentos";

function Carregando({ texto }: { texto: string }) {
  return (
    <p className="text-body text-ink-muted" aria-busy="true">
      {texto}
    </p>
  );
}

function Marca({ andamento }: { andamento: AndamentoDoAssistente }) {
  const router = useRouter();
  const consulta = useQuery({ queryKey: ["marca"], queryFn: () => marcaApi.obter(), staleTime: 5 * 60_000 });
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  if (!consulta.data) return <Carregando texto="Carregando a marca…" />;
  const depois = () => router.push(destinoDepoisDe(andamento, "marca"));
  return <PassoMarca guardada={consulta.data} aoContinuar={depois} aoPular={depois} />;
}

function Ramo({ andamento }: { andamento: AndamentoDoAssistente }) {
  const router = useRouter();
  const marca = useMarcaDaEmpresa();
  const consulta = useQuery({ queryKey: ["ramo"], queryFn: () => ramoApi.obter() });
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  if (!consulta.data) return <Carregando texto="Carregando o ramo…" />;
  return <PassoRamo guardado={consulta.data} nomeDaEmpresa={marca.nome} voltarPara={destinoAntesDe(andamento, "ramo")} aoContinuar={() => router.push(destinoDepoisDe(andamento, "ramo"))} />;
}

/** Os passos que gravam por telas próprias (filial, preços, contrato, equipe): "Continuar" relê o andamento e segue; "Pular" só navega (IMP-05). */
function ComRodape({ andamento, passo }: { andamento: AndamentoDoAssistente; passo: "filial" | "precos" | "contrato" | "recebimentos" | "equipe" }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const { eu } = useSessao();
  const feito = andamento.passos.find((p) => p.passo === passo)?.feito ?? false;
  const antes = destinoAntesDe(andamento, passo);
  const depois = destinoDepoisDe(andamento, passo);
  const seguir = async () => {
    await cliente.invalidateQueries({ queryKey: ["implantacao"] });
    router.push(depois);
  };
  if (passo === "filial") return <PassoFilial voltarPara={antes} pularPara={depois} aoContinuar={() => void seguir()} />;
  if (passo === "precos") return <PassoPrecos feito={feito} voltarPara={antes} pularPara={depois} aoContinuar={() => void seguir()} />;
  if (passo === "contrato") return <PassoContrato feito={feito} voltarPara={antes} pularPara={depois} aoPublicar={() => void cliente.invalidateQueries({ queryKey: ["implantacao"] })} aoContinuar={() => void seguir()} />;
  if (passo === "recebimentos") return <PassoRecebimentos feito={feito} voltarPara={antes} pularPara={depois} aoContinuar={() => void seguir()} />;
  return <PassoEquipe eu={eu} feito={feito} voltarPara={antes} pularPara={depois} aoContinuar={() => void seguir()} />;
}

/** Passo do assistente que ainda não tem tela (passo sem rota própria): a moldura segue, e os botões só navegam. */
export function SemTela({ andamento, passo }: { andamento: AndamentoDoAssistente; passo: string }) {
  const atual = andamento.passos.find((p) => p.passo === passo);
  return (
    <section className="wl-panel flex flex-col gap-4" aria-labelledby="passo-sem-tela">
      <h1 id="passo-sem-tela" className="text-title md:text-display">
        {atual?.rotulo}
      </h1>
      <p className="m-0 text-body text-ink-muted">Esta etapa ainda não está disponível aqui. Você pode seguir e voltar quando ela estiver pronta.</p>
      <div className="flex flex-wrap items-center gap-2">
        <Link href={destinoAntesDe(andamento, passo)} className="wl-btn wl-btn--quiet">
          Voltar
        </Link>
        <Link href={destinoDepoisDe(andamento, passo)} className="wl-btn wl-btn--solid ml-auto">
          Pular por agora
        </Link>
      </div>
    </section>
  );
}

/** Corpo do passo da vez, escolhido pela chave que a API mandou. */
export function CorpoDoPasso({ andamento, passo }: { andamento: AndamentoDoAssistente; passo: string }) {
  if (passo === "marca") return <Marca andamento={andamento} />;
  if (passo === "ramo") return <Ramo andamento={andamento} />;
  if (passo === "filial" || passo === "precos" || passo === "contrato" || passo === "recebimentos" || passo === "equipe") return <ComRodape andamento={andamento} passo={passo} />;
  return <SemTela andamento={andamento} passo={passo} />;
}

/** Rota /implantacao/[passo]: a moldura e o passo da vez. Quais passos existem e o que está feito vêm da API. */
export function PassoDoAssistente({ passo }: { passo: string }) {
  return <CascaDoAssistente passo={passo}>{(andamento) => <CorpoDoPasso andamento={andamento} passo={passo} />}</CascaDoAssistente>;
}
