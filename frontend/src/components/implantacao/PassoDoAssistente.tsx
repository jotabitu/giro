"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { marca as marcaApi, ramo as ramoApi, type AndamentoDoAssistente } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { destinoAntesDe, destinoDepoisDe } from "@/lib/implantacao";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { CascaDoAssistente } from "./CascaDoAssistente";
import { PassoMarca } from "./PassoMarca";
import { PassoRamo } from "./PassoRamo";

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

/** Passo do assistente que ainda não tem tela (sem contrato ou sem página): a moldura segue, e os botões só navegam. */
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
  return <SemTela andamento={andamento} passo={passo} />;
}

/** Rota /implantacao/[passo]: a moldura e o passo da vez. Quais passos existem e o que está feito vêm da API. */
export function PassoDoAssistente({ passo }: { passo: string }) {
  return <CascaDoAssistente passo={passo}>{(andamento) => <CorpoDoPasso andamento={andamento} passo={passo} />}</CascaDoAssistente>;
}
