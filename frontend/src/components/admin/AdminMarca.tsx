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

// Referência: docs/telas/html/Admin-Marca-Desktop.dc.html e Admin-Marca-Mobile.dc.html. "Dados da empresa" e "Endereço do sistema" ficam fora (sem contrato, docs/api/empresas.md).

const DICA_DA_COR = "Usada nos botões e destaques. O texto em cima dela muda sozinho para continuar legível.";

export function FormularioDaMarca({ guardada }: { guardada: MarcaEmpresa }) {
  const m = useEdicaoDaMarca(guardada);
  const salvando = m.salvar.isPending;
  // A cor salva vem na frente, como a bolinha marcada da tela de referência.
  const atalhos = [{ hex: guardada.cor, rotulo: "Cor atual" }, ...CORES_DE_ATALHO.filter((c) => c.hex !== guardada.cor.toUpperCase())];

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (m.mudou && !salvando) m.salvar.mutate();
      }}
    >
      {m.erroGeral !== null && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(m.erroGeral)}
        </p>
      )}
      {m.salvar.isSuccess && (
        <p role="status" className="flex items-center gap-2 rounded-lg bg-success-soft p-4 text-body text-success-ink">
          <Icone de={Check} />
          Marca salva. As cores já mudaram no sistema.
        </p>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <section className="wl-panel flex min-w-0 flex-col gap-[18px] md:flex-[999_1_520px]" aria-labelledby="marca-titulo">
          <h2 id="marca-titulo" className="text-heading">
            Marca
          </h2>
          <EscolhaDoLogo logoUrl={m.logoUrl} iniciais={m.previa.iniciais} variante="admin" desligado={salvando} erro={m.erro("logo")} aoEscolher={m.escolherLogo} aoRemover={m.removerLogo} />
          <EscolhaDaCor rotulo="Cor principal" cores={atalhos} atual={m.edicao.cor} digitavel erro={m.erro("cor")} dica={DICA_DA_COR} aoEscolher={m.escolherCor} aoDigitar={m.digitarCor} />
          <TextField rotulo="Nome que aparece para clientes" cheio value={m.edicao.nome} maxLength={80} onChange={(e) => m.mudarNome(e.target.value)} erro={m.erro("nome_exibicao")} />
          <div className="flex items-center justify-end gap-2">
            <Button variante="quieto" disabled={!m.mudou || salvando} onClick={m.descartar}>
              Cancelar
            </Button>
            <Button type="submit" variante="solido" disabled={!m.mudou || salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </section>

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
