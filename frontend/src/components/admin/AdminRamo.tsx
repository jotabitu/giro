"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Lock } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { ramo as ramoApi, type Ramo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { corpoDoRamo, marcasDoRamo, podeAlternar, ramoMudou, recusaDoRamo, type ChaveDaMarca, type MarcasDoRamo } from "@/lib/ramo";
import { useSessao } from "@/lib/sessao";

// Referência: docs/telas/html/Admin-Ramo-Desktop.dc.html e Admin-Ramo-Mobile.dc.html. As opções, os avisos, os módulos e as recusas vêm da API (PLT-12, docs/api/empresas.md).

function Opcao({ titulo, descricao, aviso, marcado, travado, aoAlternar }: { titulo: string; descricao?: string; aviso?: string | null; marcado: boolean; travado: boolean; aoAlternar: () => void }) {
  return (
    <div>
      <button
        type="button"
        aria-pressed={marcado}
        aria-disabled={travado}
        onClick={() => !travado && aoAlternar()}
        className={`flex min-h-11 w-full items-start gap-3 rounded-lg border p-4 text-left text-ink ${marcado ? "border-ink bg-brand-soft" : "border-line bg-surface"} ${travado ? "opacity-70" : ""}`}
      >
        <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-sm border ${marcado ? "border-ink bg-ink text-surface" : "border-line"}`} aria-hidden="true">
          {marcado && <Icone de={Check} />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[16px] font-semibold">{titulo}</span>
          {descricao && <span className="mt-0.5 block text-[14px] text-ink-muted">{descricao}</span>}
        </span>
        {travado && marcado && <Icone de={Lock} />}
      </button>
      {aviso && <p className="mt-1.5 mb-0 text-caption text-ink-muted">{aviso}</p>}
    </div>
  );
}

function Formulario({ guardado }: { guardado: Ramo }) {
  const cliente = useQueryClient();
  const [marcas, setMarcas] = useState<MarcasDoRamo>(marcasDoRamo(guardado));
  const [salvo, setSalvo] = useState(false);
  const mudou = ramoMudou(guardado, marcas);
  const corpo = corpoDoRamo(marcas);

  const salvar = useMutation({
    mutationFn: () => {
      if (!corpo) throw new Error("ramo incompleto");
      return ramoApi.trocar(corpo);
    },
    onSuccess: async (novo) => {
      cliente.setQueryData(["ramo"], novo);
      // O cartão de Configurações e o menu mudam no pedido seguinte.
      await Promise.all([cliente.invalidateQueries({ queryKey: ["configuracoes"] }), cliente.invalidateQueries({ queryKey: ["eu"] })]);
      setSalvo(true);
    },
  });
  const recusa = recusaDoRamo(salvar.error);
  const erroGeral = salvar.isError && !recusa;

  const alternar = (chave: ChaveDaMarca) => {
    setMarcas((m) => ({ ...m, [chave]: !m[chave] }));
    setSalvo(false);
    salvar.reset();
  };
  const desfazer = () => {
    setMarcas(marcasDoRamo(guardado));
    salvar.reset();
  };

  const marcada = corpo?.atividade ?? guardado.atividade;
  const modulos = guardado.modulos[marcada] ?? [];
  const chaveDaAtividade = (v: string): ChaveDaMarca => (v === "aluga" ? "locacao" : "venda");
  const dica = guardado.atividades_aceitas.includes("aluga") && guardado.atividades_aceitas.includes("vende") ? "Marque as duas se a empresa aluga e vende. Pelo menos uma precisa ficar marcada." : null;

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (mudou && corpo && !salvar.isPending) salvar.mutate();
      }}
    >
      {recusa && (
        <div role="alert" className="flex flex-col gap-2 rounded-lg bg-critical-soft p-4 text-critical-ink">
          <strong className="text-body">Não foi possível trocar o ramo</strong>
          <span className="text-body">{recusa.mensagem}</span>
          <span className="flex flex-wrap items-center gap-3">
            {recusa.link && (
              <Link href={recusa.link.href} className="wl-btn">
                {recusa.link.rotulo}
              </Link>
            )}
            <Button type="button" variante="quieto" onClick={desfazer}>
              Manter o ramo atual
            </Button>
          </span>
          <span className="text-caption">Nada mudou. Resolva o que está aberto e tente de novo.</span>
        </div>
      )}
      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(salvar.error)}
        </p>
      )}
      {salvo && (
        <p role="status" className="flex items-center gap-2 rounded-lg bg-success-soft p-4 text-body text-success-ink">
          <Icone de={Check} />
          Ramo salvo. O menu muda agora, e nada foi apagado.
        </p>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_520px]">
          <section className="wl-panel flex flex-col gap-3" aria-labelledby="ramo-atividades">
            <h2 id="ramo-atividades" className="text-heading">
              Atividades
            </h2>
            {guardado.atividades.map((a) => {
              const chave = chaveDaAtividade(a.valor);
              return <Opcao key={a.valor} titulo={a.titulo} descricao={a.descricao} aviso={a.aviso} marcado={marcas[chave]} travado={!podeAlternar(guardado, marcas, chave)} aoAlternar={() => alternar(chave)} />;
            })}
            {dica && <p className="m-0 text-caption text-ink-muted">{dica}</p>}
          </section>

          <section className="wl-panel flex flex-col gap-3" aria-labelledby="ramo-tipos">
            <h2 id="ramo-tipos" className="text-heading">
              Tipos de veículo
            </h2>
            {guardado.tipos.map((t) => {
              const chave: ChaveDaMarca = t.valor;
              return <Opcao key={t.valor} titulo={t.titulo} marcado={marcas[chave]} travado={!podeAlternar(guardado, marcas, chave)} aoAlternar={() => alternar(chave)} />;
            })}
          </section>

          <div className="flex items-center justify-end gap-2">
            <Button type="button" variante="quieto" onClick={desfazer} disabled={!mudou || salvar.isPending}>
              Cancelar
            </Button>
            <Button type="submit" variante="solido" disabled={!mudou || !corpo || salvar.isPending}>
              {salvar.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:flex-[1_1_300px]">
          <section className="wl-panel flex flex-col gap-3" aria-labelledby="ramo-modulos">
            <div>
              <h2 id="ramo-modulos" className="text-heading">
                Módulos que vamos ligar
              </h2>
              <p className="mt-1 mb-0 text-caption text-ink-muted">{modulos.length === 1 ? "1 módulo no seu plano" : `${modulos.length} módulos no seu plano`}</p>
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {modulos.map((m) => (
                <li key={m} className="flex items-center gap-2 text-body">
                  <Icone de={Check} />
                  {m}
                </li>
              ))}
            </ul>
          </section>
          <section className="wl-panel flex flex-col gap-1.5">
            <h2 className="text-heading">O que acontece com os dados</h2>
            <p className="m-0 text-body text-ink-muted">Nada é apagado. O que ficar desligado fica guardado e volta se você ligar de novo. Só o administrador troca o ramo.</p>
          </section>
        </aside>
      </div>
    </form>
  );
}

/** Administração › Configurações › O que a empresa faz: liga e desliga módulos pelo ramo (PLT-12). A API decide o que vale. */
export function AdminRamo() {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["ramo"], queryFn: () => ramoApi.obter(), enabled: podeVer });

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center gap-3 md:items-end md:gap-4">
        <Link href="/admin/configuracoes" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 shrink-0 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">
            <span className="md:hidden">Configurações</span>
            <span className="hidden md:inline">
              Administração / <Link href="/admin/configuracoes" className="underline">Configurações</Link>
            </span>
          </div>
          <h1 className="text-title md:mt-1.5 md:text-display">O que a empresa faz</h1>
          <p className="mt-1.5 hidden text-body text-ink-muted md:block">Ligamos só o que você usa, para o menu ficar simples</p>
        </div>
      </header>

      {!podeVer && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Só o administrador troca o ramo.
        </p>
      )}
      {podeVer && consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {podeVer && consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando o ramo…
        </p>
      )}
      {podeVer && consulta.data && <Formulario guardado={consulta.data} />}
    </div>
  );
}
