"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check } from "lucide-react";
import Link from "next/link";
import { Button, Icone, TextField } from "@/design-system";
import { marca as marcaApi, type MarcaEmpresa } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { CORES_DE_ATALHO } from "@/lib/marca-edicao";
import { useSessao } from "@/lib/sessao";
import { EscolhaDaCor } from "../marca/EscolhaDaCor";
import { EscolhaDoLogo } from "../marca/EscolhaDoLogo";
import { PreviaDaMarca } from "../marca/PreviaDaMarca";
import { useEdicaoDaMarca } from "../marca/useEdicaoDaMarca";
import { useLimiteDoEstoque } from "./useLimiteDoEstoque";

// Referência: docs/telas/html/Admin-Marca-Desktop.dc.html e Admin-Marca-Mobile.dc.html. "Dados da empresa" e "Endereço do sistema" ficam fora (sem contrato, docs/api/empresas.md).

const DICA_DA_COR = "Usada nos botões e destaques. O texto em cima dela muda sozinho para continuar legível.";
const DICA_DO_LIMITE = "Acima disso, o veículo à venda aparece como parado e o gerente da filial é avisado. De 1 a 365 dias, igual para todas as filiais.";

export function FormularioDaMarca({ guardada }: { guardada: MarcaEmpresa }) {
  const m = useEdicaoDaMarca(guardada);
  const limite = useLimiteDoEstoque();
  const salvando = m.salvar.isPending || limite.salvar.isPending;
  const mudou = m.mudou || limite.mudou;
  // A cor salva vem na frente, como a bolinha marcada da tela de referência.
  const atalhos = [{ hex: guardada.cor, rotulo: "Cor atual" }, ...CORES_DE_ATALHO.filter((c) => c.hex !== guardada.cor.toUpperCase())];

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (salvando) return;
        if (m.mudou) m.salvar.mutate();
        if (limite.mudou) limite.salvar.mutate();
      }}
    >
      {(m.erroGeral ?? limite.erroGeral) !== null && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(m.erroGeral ?? limite.erroGeral)}
        </p>
      )}
      {m.salvar.isSuccess && (
        <p role="status" className="flex items-center gap-2 rounded-lg bg-success-soft p-4 text-body text-success-ink">
          <Icone de={Check} />
          Marca salva. As cores já mudaram no sistema.
        </p>
      )}
      {limite.salvar.isSuccess && !m.salvar.isSuccess && (
        <p role="status" className="flex items-center gap-2 rounded-lg bg-success-soft p-4 text-body text-success-ink">
          <Icone de={Check} />
          Limite de dias em estoque salvo.
        </p>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_520px]">
          <section className="wl-panel flex min-w-0 flex-col gap-[18px]" aria-labelledby="marca-titulo">
            <h2 id="marca-titulo" className="text-heading">
              Marca
            </h2>
            <EscolhaDoLogo logoUrl={m.logoUrl} iniciais={m.previa.iniciais} variante="admin" desligado={salvando} erro={m.erro("logo")} aoEscolher={m.escolherLogo} aoRemover={m.removerLogo} />
            <EscolhaDaCor rotulo="Cor principal" cores={atalhos} atual={m.edicao.cor} digitavel erro={m.erro("cor")} dica={DICA_DA_COR} aoEscolher={m.escolherCor} aoDigitar={m.digitarCor} />
            <TextField rotulo="Nome que aparece para clientes" cheio value={m.edicao.nome} maxLength={80} onChange={(e) => m.mudarNome(e.target.value)} erro={m.erro("nome_exibicao")} />
          </section>

          {/* VEI-19 (T-486): o limite de dias em estoque, gravado pelo mesmo Salvar. */}
          {limite.carregado && (
            <section className="wl-panel flex min-w-0 flex-col gap-[18px]" aria-labelledby="estoque-titulo">
              <h2 id="estoque-titulo" className="text-heading">
                Estoque à venda
              </h2>
              <TextField
                rotulo="Limite de dias em estoque"
                mono
                inputMode="numeric"
                value={limite.texto}
                disabled={!limite.podeEditar || salvando}
                onChange={(e) => limite.digitar(e.target.value)}
                erro={limite.erro}
                dica={limite.podeEditar ? DICA_DO_LIMITE : "Só o administrador altera."}
              />
            </section>
          )}

          <div className="flex items-center justify-end gap-2">
            <Button
              variante="quieto"
              disabled={!mudou || salvando}
              onClick={() => {
                m.descartar();
                limite.descartar();
              }}
            >
              Cancelar
            </Button>
            <Button type="submit" variante="solido" disabled={!mudou || salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </div>

        <aside className="wl-panel flex min-w-0 flex-col gap-4 md:flex-[1_1_320px]" aria-labelledby="previa-titulo">
          <h2 id="previa-titulo" className="text-heading">
            Prévia
          </h2>
          <PreviaDaMarca marca={m.previa} logoUrl={m.logoUrl} />
        </aside>
      </div>
    </form>
  );
}

/** Administração › Empresa e marca: logo, cor principal e nome que aparecem para a equipe e para os clientes. Só o administrador. */
export function AdminMarca() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["marca"], queryFn: () => marcaApi.obter(), enabled: podeVer, staleTime: 5 * 60_000 });

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-3 md:items-end md:gap-4">
        <Link href="/admin/configuracoes" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 shrink-0 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Empresa e marca</h1>
          <p className="mt-1.5 hidden text-body text-ink-muted md:block">Como o sistema, os contratos e as mensagens aparecem para a sua equipe e seus clientes</p>
        </div>
      </header>

      {!podeVer && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Só o administrador muda a marca.
        </p>
      )}
      {podeVer && consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {podeVer && consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando a marca…
        </p>
      )}
      {podeVer && consulta.isSuccess && consulta.data === null && (
        <p role="alert" className="text-body">
          Esta empresa não tem marca para editar.
        </p>
      )}
      {podeVer && consulta.data && <FormularioDaMarca guardada={consulta.data} />}
    </div>
  );
}
