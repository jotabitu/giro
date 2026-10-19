"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSessao } from "@/lib/sessao";
import { importacao } from "@/lib/api";
import { atualDoTipo, emAndamento, TIPOS_DE_IMPORTACAO } from "@/lib/importacao";
import { destinoAntesDe, destinoDepoisDe } from "@/lib/implantacao";
import { mensagemDoErro } from "@/lib/erros";
import { CaixaDeImportacao } from "./CaixaDeImportacao";
import { CascaDoAssistente } from "./CascaDoAssistente";

// Referência: docs/telas/html/Onboarding-Importar-Desktop.dc.html e Onboarding-Importar-Mobile.dc.html. A moldura e os passos vêm da CascaDoAssistente.

/** Passo "Importar dados" do assistente de implantação: planilhas de veículos e de clientes, conferidas linha por linha. Só o administrador. */
export function ImportarDados() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({
    queryKey: ["importacao", "lista"],
    queryFn: () => importacao.listar(),
    enabled: podeVer,
    refetchInterval: (q) => (q.state.data?.some(emAndamento) ? 3_000 : false),
  });
  const lista = consulta.data ?? [];

  return (
    <CascaDoAssistente passo="importar" semPermissao="Só o administrador importa dados.">
      {(andamento) => (
        <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-label="Importar dados">
          <div>
            <h1 className="text-title md:text-display">Traga sua frota e seus clientes</h1>
            <p className="mt-1.5 mb-0 text-body text-ink-muted">
              <span className="hidden md:inline">Baixe a planilha modelo, preencha e envie. Conferimos linha por linha antes de importar.</span>
              <span className="md:hidden">Envie a planilha modelo preenchida. Conferimos linha por linha.</span>
            </p>
          </div>

          {consulta.isError && (
            <p role="alert" className="text-body">
              {mensagemDoErro(consulta.error)}
            </p>
          )}
          {consulta.isPending && (
            <p className="text-body text-ink-muted" aria-busy="true">
              Carregando as importações…
            </p>
          )}

          {consulta.data && (
            <div className="grid gap-4 md:grid-cols-[repeat(auto-fit,minmax(300px,1fr))]">
              {TIPOS_DE_IMPORTACAO.map((t) => (
                <CaixaDeImportacao key={t.tipo} tipo={t.tipo} atual={atualDoTipo(lista, t.tipo)} eu={eu} />
              ))}
            </div>
          )}

          <p className="m-0 rounded-md bg-surface-sunken p-4 text-caption text-ink-muted">
            <span className="hidden md:inline">Contratos em andamento você cadastra pela tela de nova locação, para gerar as parcelas certas. Se preferir, nossa equipe faz a importação por você.</span>
            <span className="md:hidden">Planilhas grandes ficam mais fáceis no computador. Você pode continuar por lá com o mesmo login.</span>
          </p>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link href={destinoAntesDe(andamento, "importar")} className="wl-btn wl-btn--quiet mr-auto hidden md:inline-flex">
              Voltar
            </Link>
            <Link href={destinoDepoisDe(andamento, "importar")} className="wl-btn">
              <span className="hidden md:inline">Cadastrar um por um depois</span>
              <span className="md:hidden">Depois</span>
            </Link>
            <Link href={destinoDepoisDe(andamento, "importar")} className="wl-btn wl-btn--solid">
              Continuar
            </Link>
          </div>
        </section>
      )}
    </CascaDoAssistente>
  );
}
