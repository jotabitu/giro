"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSessao } from "@/lib/sessao";
import { importacao } from "@/lib/api";
import { atualDoTipo, emAndamento, TIPOS_DE_IMPORTACAO } from "@/lib/importacao";
import { mensagemDoErro } from "@/lib/erros";
import { useMarcaDaEmpresa } from "@/lib/marca-empresa";
import { CaixaDeImportacao } from "./CaixaDeImportacao";

// Referência: docs/telas/html/Onboarding-Importar-Desktop.dc.html e Onboarding-Importar-Mobile.dc.html (passo 11 da implantação).
// As telas dos outros passos do assistente ainda não existem: a lista de passos é só a posição, e os botões levam ao que existe (ver `[decisão]`).

const PASSOS = ["Empresa e marca", "Primeira filial", "O que a empresa faz", "Tabela de preços", "Modelo de contrato", "Recebimentos", "Importar dados", "Convidar equipe"];
const PASSO_ATUAL = 7;

/** Passo "Importar dados" do assistente de implantação: planilhas de veículos e de clientes, conferidas linha por linha. Só o administrador. */
export function ImportarDados() {
  const { eu } = useSessao();
  const marca = useMarcaDaEmpresa();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({
    queryKey: ["importacao", "lista"],
    queryFn: () => importacao.listar(),
    enabled: podeVer,
    refetchInterval: (q) => (q.state.data?.some(emAndamento) ? 3_000 : false),
  });

  if (!podeVer)
    return (
      <p role="alert" className="m-4 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador importa dados.
      </p>
    );

  const lista = consulta.data ?? [];

  return (
    <div className="mx-auto flex min-h-screen max-w-[1200px] flex-col gap-6 bg-canvas p-4 md:p-6">
      <header className="flex items-center gap-3">
        <div className="wl-logo-slot" aria-hidden="true">
          {marca.logo ? (
            // eslint-disable-next-line @next/next/no-img-element -- logo servido pela API (S-12): sempre <img>, nunca inline
            <img src={marca.logo.url} alt="" width={40} height={40} style={{ borderRadius: "inherit", objectFit: "contain" }} />
          ) : (
            marca.iniciais
          )}
        </div>
        <span className="text-heading">{marca.nome}</span>
        <span className="hidden text-body text-ink-muted md:inline">Configuração inicial</span>
        <Link href="/inicio" className="wl-btn wl-btn--sm ml-auto md:h-12 md:px-5 md:text-[length:inherit]">
          <span className="hidden md:inline">Salvar e sair</span>
          <span className="md:hidden">Sair</span>
        </Link>
      </header>

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <aside className="wl-panel hidden shrink-0 flex-col gap-4 md:flex md:w-[280px]" aria-label="Passos da configuração">
          <div>
            <div className="mb-2 text-caption text-ink-muted">
              Passo {PASSO_ATUAL} de {PASSOS.length}
            </div>
            <div className="wl-progressbar" role="progressbar" aria-label="Passos da configuração" aria-valuemin={0} aria-valuemax={PASSOS.length} aria-valuenow={PASSO_ATUAL}>
              <div className="wl-progressbar__fill" style={{ width: `${(PASSO_ATUAL / PASSOS.length) * 100}%` }} />
            </div>
          </div>
          <ol className="m-0 flex list-none flex-col gap-0.5 p-0">
            {PASSOS.map((nome, i) => {
              const n = i + 1;
              const agora = n === PASSO_ATUAL;
              return (
                <li key={nome} aria-current={agora ? "step" : undefined} className={`flex min-h-[44px] items-center gap-3 rounded-pill px-3 text-body ${agora ? "bg-solid text-on-solid" : n < PASSO_ATUAL ? "text-ink" : "text-ink-muted"}`}>
                  <span className={`grid size-[26px] shrink-0 place-items-center rounded-full text-caption font-medium ${agora ? "bg-brand text-on-brand" : "bg-surface-sunken text-ink"}`}>{n}</span>
                  {nome}
                </li>
              );
            })}
          </ol>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-label="Importar dados">
          <div className="md:hidden">
            <div className="mb-2 flex justify-between text-caption text-ink-muted">
              <span>
                Passo {PASSO_ATUAL} de {PASSOS.length}
              </span>
              <span>{PASSOS[PASSO_ATUAL]} a seguir</span>
            </div>
            <div className="flex gap-1" aria-hidden="true">
              {PASSOS.map((p, i) => (
                <span key={p} className={`h-1.5 flex-1 rounded-pill ${i < PASSO_ATUAL ? "bg-solid" : "bg-surface-sunken"}`} />
              ))}
            </div>
          </div>

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
            <Link href="/inicio" className="wl-btn wl-btn--quiet mr-auto hidden md:inline-flex">
              Voltar
            </Link>
            <Link href="/admin/usuarios" className="wl-btn">
              <span className="hidden md:inline">Cadastrar um por um depois</span>
              <span className="md:hidden">Depois</span>
            </Link>
            <Link href="/admin/usuarios" className="wl-btn wl-btn--solid">
              Continuar
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
