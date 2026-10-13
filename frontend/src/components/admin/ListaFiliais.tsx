"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, Ellipsis, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Icone, StatusBadge } from "@/design-system";
import { Confirmacao } from "@/components/financeiro/Comuns";
import { filiais, type FilialDaLista, type PlanoDeFiliais } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { useFilial } from "@/lib/filial-escolhida";
import { mascaraCnpj, percentual } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { AcoesDaFilial } from "./AcoesDaFilial";

// Referência: docs/telas/html/Filiais-Desktop.dc.html e Filiais-Mobile.dc.html.
// Plano, indicadores e resumos vêm da API (FIL-01 a FIL-06, PLT-03); indicador de app que ainda não existe vem `null` e sai "—".

const AVISOS: Record<string, string> = { criada: "Filial criada. Confirme os feriados dela na tela de edição.", salva: "Alterações da filial salvas." };

const numero = (n: number | null) => (n === null ? "—" : new Intl.NumberFormat("pt-BR").format(n));

function Indicador({ valor, rotulo }: { valor: string; rotulo: string }) {
  return (
    <div className="rounded-md bg-surface-sunken px-[14px] py-3">
      <b className="block text-[22px] leading-[26px] font-semibold">{valor}</b>
      <span className="text-caption text-ink-muted">{rotulo}</span>
    </div>
  );
}

function Linha({ rotulo, children, soDesktop }: { rotulo: string; children: React.ReactNode; soDesktop?: boolean }) {
  return (
    <div className={`justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0 ${soDesktop ? "hidden md:flex" : "flex"}`}>
      <span className="text-ink-muted">{rotulo}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

function CartaoDaFilial({ f, aoAcoes, aoVerPainel }: { f: FilialDaLista; aoAcoes: (f: FilialDaLista) => void; aoVerPainel: (f: FilialDaLista) => void }) {
  const i = f.indicadores;
  return (
    <article className={`flex flex-col gap-4 rounded-[28px] bg-surface p-6 ${f.ativo ? "" : "opacity-80"}`}>
      <div className="flex items-start gap-3">
        <div className="grid size-[52px] shrink-0 place-items-center rounded-[14px] bg-surface-sunken text-ink-muted" aria-hidden="true">
          <Icone de={Building2} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-heading font-semibold">{f.nome}</h2>
            {f.matriz && (
              <StatusBadge tom="solido" compacto>
                Matriz
              </StatusBadge>
            )}
            <StatusBadge tom={f.ativo ? "sucesso" : "neutro"} compacto>
              {f.ativo ? "Ativa" : "Inativa"}
            </StatusBadge>
          </div>
          <div className="mt-1 text-caption text-ink-muted">{f.endereco_resumo}</div>
        </div>
        <button type="button" aria-label={`Mais ações de ${f.nome}`} onClick={() => aoAcoes(f)} className="wl-icon-btn wl-icon-btn--sm size-11 shrink-0">
          <Icone de={Ellipsis} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Indicador valor={numero(i.veiculos)} rotulo="veículos" />
        <Indicador valor={numero(i.locacoes_ativas)} rotulo="locações ativas" />
        <Indicador valor={numero(i.usuarios)} rotulo="usuários" />
        <Indicador valor={i.ocupacao_pct === null ? "—" : percentual(i.ocupacao_pct)} rotulo="ocupação" />
      </div>

      <div>
        <Linha rotulo="Gerente">{f.gerentes.length ? f.gerentes.map((g) => g.nome).join(", ") : "Nenhum gerente"}</Linha>
        <Linha rotulo="Funcionamento">{f.horario_resumo || "—"}</Linha>
        {f.cnpj && (
          <Linha rotulo="CNPJ" soDesktop>
            <span className="wl-mono">{mascaraCnpj(f.cnpj)}</span>
          </Linha>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href={`/admin/filiais/${f.id}`} className="wl-btn wl-btn--sm">
          Editar dados
        </Link>
        {f.ativo && (
          <Button compacto variante="quieto" onClick={() => aoVerPainel(f)}>
            Ver painel da filial
          </Button>
        )}
      </div>
    </article>
  );
}

function CartaoNova({ plano }: { plano: PlanoDeFiliais }) {
  const restam = plano.limite === null ? null : Math.max(plano.limite - plano.usado, 0);
  return (
    <Link href={plano.bloqueado ? "/admin/assinatura" : "/admin/filiais/nova"} className="flex min-h-[180px] flex-col items-center justify-center gap-2.5 rounded-[28px] border-[1.5px] border-dashed border-line p-6 text-center text-ink md:min-h-[280px]">
      <span className="grid size-12 place-items-center rounded-full bg-surface-sunken" aria-hidden="true">
        <Icone de={Plus} />
      </span>
      <span className="text-heading font-semibold">{plano.bloqueado ? "Mudar de plano" : "Nova filial"}</span>
      <span className="text-caption text-ink-muted">
        {plano.bloqueado
          ? "Seu plano chegou ao limite de filiais. Mude de plano para abrir outra."
          : restam === null
            ? "Cada filial tem frota, caixa e equipe próprios."
            : `Seu plano permite mais ${restam} ${restam === 1 ? "filial" : "filiais"}. Cada uma tem frota, caixa e equipe próprios.`}
      </span>
    </Link>
  );
}

const COMO_FUNCIONA = [
  ["Veículos e caixa", "separados por filial"],
  ["Clientes e tabelas de preço", "compartilhados (ou por filial, se preferir)"],
  ["Transferir veículo entre filiais", "pela ficha do veículo"],
  ["Quem vê o quê", "definido em Usuários"],
] as const;

/** Administração › Filiais: plano, uma carta por filial com indicadores e as ações; a edição é outra tela. */
export function ListaFiliais() {
  const { eu } = useSessao();
  const router = useRouter();
  const { valor } = useFiltrosNaUrl();
  const escolhida = useFilial();
  const [acoes, setAcoes] = useState<FilialDaLista | null>(null);
  const [aviso, setAviso] = useState<string | null>(valor("ok") ? (AVISOS[valor("ok") ?? ""] ?? null) : null);

  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["filiais-admin", "lista"], queryFn: () => filiais.listar(), enabled: podeVer });
  const d = podeVer ? consulta.data : undefined;
  const plano = d?.plano;

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa Filiais.
      </p>
    );

  const verPainel = (f: FilialDaLista) => {
    escolhida?.trocar(String(f.id));
    router.push("/inicio");
  };
  const textoDoPlano = plano ? (plano.limite === null ? `${plano.usado} filiais no plano ${plano.nome_plano}` : `${plano.usado} de ${plano.limite} filiais do plano ${plano.nome_plano}`) : null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3 md:items-end">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1 md:flex-none">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Filiais</h1>
          {textoDoPlano && <p className="mt-1 hidden text-body text-ink-muted md:block">{textoDoPlano}</p>}
        </div>
        {plano && (
          <Link
            href={plano.bloqueado ? "/admin/assinatura" : "/admin/filiais/nova"}
            aria-label="Nova filial"
            className="wl-icon-btn wl-icon-btn--sm size-11 md:hidden"
          >
            <Icone de={Plus} />
          </Link>
        )}
        {plano && (
          <Link href={plano.bloqueado ? "/admin/assinatura" : "/admin/filiais/nova"} className="wl-btn wl-btn--solid hidden md:ml-auto md:inline-flex">
            {plano.bloqueado ? "Mudar de plano" : "Nova filial"}
          </Link>
        )}
      </header>

      {plano && (
        <div className="flex items-center gap-2.5 rounded-lg bg-surface-sunken px-4 py-3 text-caption text-ink-muted md:hidden">
          <span className="flex-1">Filiais do plano</span>
          <StatusBadge tom="superficie" compacto>
            {plano.limite === null ? String(plano.usado) : `${plano.usado} de ${plano.limite}`}
          </StatusBadge>
        </div>
      )}

      {aviso && <Confirmacao>{aviso}</Confirmacao>}
      {consulta.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando as filiais…
        </p>
      )}

      {d && (
        <div className="grid gap-6 lg:grid-cols-2">
          {d.resultados.map((f) => (
            <CartaoDaFilial key={f.id} f={f} aoAcoes={setAcoes} aoVerPainel={verPainel} />
          ))}
          <CartaoNova plano={d.plano} />
        </div>
      )}

      <section className="wl-panel" aria-label="Como funciona com mais de uma filial">
        <h2 className="text-heading">
          <span className="hidden md:inline">Como funciona com mais de uma filial</span>
          <span className="md:hidden">Com mais de uma filial</span>
        </h2>
        {COMO_FUNCIONA.map(([titulo, texto]) => (
          <div key={titulo} className="flex items-center gap-3 border-b border-line py-[14px] last:border-b-0">
            <span className="text-body">{titulo}</span>
            <span className="ml-auto text-right text-caption text-ink-muted">{texto}</span>
          </div>
        ))}
      </section>

      {acoes && <AcoesDaFilial filial={acoes} aoFechar={() => setAcoes(null)} aoConcluir={setAviso} />}
    </div>
  );
}
