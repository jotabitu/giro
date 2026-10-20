"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { ramo as ramoApi, type Ramo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { corpoDoRamo, marcasDoRamo, podeAlternar, recusaDoRamo, type ChaveDaMarca, type MarcasDoRamo } from "@/lib/ramo";
import { OpcaoDoRamo } from "../ramo/OpcaoDoRamo";

// Referência: docs/telas/html/Onboarding-Ramo-Desktop.dc.html e Onboarding-Ramo-Mobile.dc.html (passo "O que a empresa faz").
// As opções, os avisos e os módulos vêm da API (PLT-12, docs/api/empresas.md). "Continuar" sempre chama o PUT, também sem mudança, e isso marca o passo.

const chaveDaAtividade = (v: string): ChaveDaMarca => (v === "aluga" ? "locacao" : "venda");

/** Passo "O que a empresa faz" do assistente: atividades e tipos de veículo, que ligam os módulos do menu. */
export function PassoRamo({ guardado, nomeDaEmpresa, voltarPara, aoContinuar }: { guardado: Ramo; nomeDaEmpresa: string; voltarPara: string; aoContinuar: () => void }) {
  const cliente = useQueryClient();
  const [marcas, setMarcas] = useState<MarcasDoRamo>(marcasDoRamo(guardado));
  const corpo = corpoDoRamo(marcas);

  const salvar = useMutation({
    mutationFn: () => {
      if (!corpo) throw new Error("ramo incompleto");
      return ramoApi.trocar(corpo);
    },
    onSuccess: async (novo) => {
      cliente.setQueryData(["ramo"], novo);
      await Promise.all([cliente.invalidateQueries({ queryKey: ["implantacao"] }), cliente.invalidateQueries({ queryKey: ["configuracoes"] }), cliente.invalidateQueries({ queryKey: ["eu"] })]);
      aoContinuar();
    },
  });
  const recusa = recusaDoRamo(salvar.error);
  const erroGeral = salvar.isError && !recusa;

  const alternar = (chave: ChaveDaMarca) => {
    setMarcas((m) => ({ ...m, [chave]: !m[chave] }));
    salvar.reset();
  };
  const modulos = guardado.modulos[corpo?.atividade ?? guardado.atividade] ?? [];
  const dica = guardado.atividades_aceitas.includes("aluga") && guardado.atividades_aceitas.includes("vende") ? "Marque as duas se a empresa aluga e vende. Pelo menos uma precisa ficar marcada." : null;

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (corpo && !salvar.isPending) salvar.mutate();
      }}
    >
      <div>
        <h1 className="text-title md:text-display">O que a {nomeDaEmpresa} faz?</h1>
        <p className="mt-2 mb-0 text-body text-ink-muted">Ligamos só o que você usa, para o menu ficar simples. Dá para mudar depois em Configurações.</p>
      </div>

      {recusa && (
        <div role="alert" className="flex flex-col gap-2 rounded-lg bg-critical-soft p-4 text-critical-ink">
          <strong className="text-body">Não foi possível salvar o ramo</strong>
          <span className="text-body">{recusa.mensagem}</span>
          {recusa.link && (
            <span>
              <Link href={recusa.link.href} className="wl-btn">
                {recusa.link.rotulo}
              </Link>
            </span>
          )}
        </div>
      )}
      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {mensagemDoErro(salvar.error)}
        </p>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_520px]">
          <section className="wl-panel flex flex-col gap-3" aria-labelledby="passo-ramo-atividades">
            <h2 id="passo-ramo-atividades" className="text-heading">
              Atividades
            </h2>
            {guardado.atividades.map((a) => {
              const chave = chaveDaAtividade(a.valor);
              return <OpcaoDoRamo key={a.valor} titulo={a.titulo} descricao={a.descricao} aviso={a.aviso} marcado={marcas[chave]} travado={!podeAlternar(guardado, marcas, chave)} aoAlternar={() => alternar(chave)} />;
            })}
            {dica && <p className="m-0 text-caption text-ink-muted">{dica}</p>}
          </section>

          <section className="wl-panel flex flex-col gap-3" aria-labelledby="passo-ramo-tipos">
            <h2 id="passo-ramo-tipos" className="text-heading">
              Tipos de veículo
            </h2>
            {guardado.tipos.map((t) => (
              <OpcaoDoRamo key={t.valor} titulo={t.titulo} marcado={marcas[t.valor]} travado={!podeAlternar(guardado, marcas, t.valor)} aoAlternar={() => alternar(t.valor)} />
            ))}
          </section>

          <div className="flex items-center justify-between gap-2">
            <Link href={voltarPara} className="wl-btn wl-btn--quiet">
              Voltar
            </Link>
            <Button type="submit" variante="solido" disabled={!corpo || salvar.isPending}>
              {salvar.isPending ? "Salvando…" : "Continuar"}
            </Button>
          </div>
        </div>

        <aside className="flex min-w-0 flex-col gap-6 md:flex-[1_1_300px]">
          <section className="wl-panel flex flex-col gap-3" aria-labelledby="passo-ramo-modulos">
            <div>
              <h2 id="passo-ramo-modulos" className="text-heading">
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
          <section className="wl-panel hidden flex-col gap-1.5 md:flex">
            <h2 className="text-heading">Dá para mudar depois</h2>
            <p className="m-0 text-body text-ink-muted">Em Configurações, no cartão O que a empresa faz. Nada é apagado: o que ficar desligado fica guardado.</p>
          </section>
        </aside>
      </div>
    </form>
  );
}
