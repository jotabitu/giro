"use client";

import { ArrowLeft, Clock, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Icone } from "@/design-system";
import { useFilial } from "@/lib/filial-escolhida";
import { useSessao } from "@/lib/sessao";
import { CategoriasDePreco } from "./CategoriasDePreco";
import { ExtrasDeLocacao } from "./ExtrasDeLocacao";
import { HistoricoDePrecos } from "./HistoricoDePrecos";
import { PlanosEspeciais } from "./PlanosEspeciais";

// Referência: docs/telas/html/Precos-Desktop.dc.html e Precos-Mobile.dc.html.
// Tudo vem das rotas de categorias, extras e planos especiais; a tela não calcula preço (LOC-01, LOC-15, FIL-04).
// O painel "Regras de cobrança" da referência fica de fora: ainda não há rota (vem de ConfiguracaoEmpresa).

/** Administração › Tabelas de preço (T-359). */
export function TabelaDePrecos() {
  const { eu } = useSessao();
  const filialEscolhida = useFilial();
  const [criando, setCriando] = useState(false);
  const [historico, setHistorico] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  if (!eu.pode.administracao)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador mexe nas tabelas de preço.
      </p>
    );

  const id = filialEscolhida?.escolha && filialEscolhida.escolha !== "todas" ? Number(filialEscolhida.escolha) : null;
  const filial = id !== null && Number.isFinite(id) ? { id, nome: filialEscolhida?.nome ?? "Esta filial" } : null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-4">
        <Link href="/admin/configuracoes" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Tabelas de preço</h1>
          <p className="m-0 mt-1.5 text-body text-ink-muted">Valores usados ao criar uma locação. Mudanças valem só para contratos novos.</p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button icone={<Icone de={Clock} />} onClick={() => setHistorico(true)}>
            Histórico de preços
          </Button>
          <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setCriando(true)}>
            Nova categoria
          </Button>
        </div>
      </header>

      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}

      <CategoriasDePreco filial={filial} criando={criando} aoFecharCriacao={() => setCriando(false)} aoAvisar={setAviso} />

      <div className="flex flex-wrap items-start gap-6">
        <div className="min-w-0 flex-[1_1_420px]">
          <PlanosEspeciais aoAvisar={setAviso} />
        </div>
        <div className="min-w-0 flex-[1_1_420px]">
          <ExtrasDeLocacao aoAvisar={setAviso} />
        </div>
      </div>

      {historico && <HistoricoDePrecos aoFechar={() => setHistorico(false)} />}
    </div>
  );
}
