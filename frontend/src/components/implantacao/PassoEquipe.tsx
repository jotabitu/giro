"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button, Icone, StatusBadge } from "@/design-system";
import { ConvidarPessoa } from "@/components/admin/ConvidarPessoa";
import { usuarios, type Eu } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { ROTULO_DO_PERFIL } from "@/lib/usuarios";
import { RodapeDoPasso } from "./RodapeDoPasso";

// Referência: docs/telas/html/Onboarding-Equipe-Desktop.dc.html e Onboarding-Equipe-Mobile.dc.html.
// Lê GET /api/usuarios/?situacao=convites e grava POST /api/usuarios/convites/, um por pessoa (USR-01, PLT-03).
// O passo `equipe` é marcado pela API no primeiro convite enviado, mesmo sem aceite (IMP-07).

/** Passo "Convidar equipe" do assistente: o último. "Convidar depois" só navega. */
export function PassoEquipe({ eu, feito, voltarPara, pularPara, aoContinuar }: { eu: Eu; feito: boolean; voltarPara: string; pularPara: string; aoContinuar: () => void }) {
  const cliente = useQueryClient();
  const [convidando, setConvidando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const consulta = useQuery({ queryKey: ["usuarios", "convites", "assistente"], queryFn: () => usuarios.listar({ situacao: "convites" }) });
  const convites = consulta.data?.resultados ?? [];

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-labelledby="passo-equipe-titulo">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <h1 id="passo-equipe-titulo" className="text-title md:text-display">
            Quem trabalha com você?
          </h1>
          <p className="mt-1.5 mb-0 text-body text-ink-muted">Cada pessoa recebe um convite por e-mail ou WhatsApp e só vê o que o perfil dela permite.</p>
        </div>
        <Button variante="solido" icone={<Icone de={Plus} />} onClick={() => setConvidando(true)}>
          Convidar pessoa
        </Button>
      </div>

      {aviso && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {aviso}
        </p>
      )}

      <section aria-label="Convites enviados" className="flex flex-col">
        {consulta.isPending && (
          <p className="m-0 text-body text-ink-muted" aria-busy="true">
            Carregando os convites…
          </p>
        )}
        {consulta.isError && (
          <p role="alert" className="m-0 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
            {mensagemDoErro(consulta.error)}
          </p>
        )}
        {consulta.isSuccess && convites.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhum convite enviado ainda. Use o botão Convidar pessoa, ou convide depois em Administração › Usuários.</p>}
        {convites.map((c) => (
          <div key={c.id} className="flex flex-wrap items-center gap-3 border-b border-line py-3 last:border-b-0">
            <div className="min-w-0 flex-1">
              <div className="font-medium">{c.nome || c.email}</div>
              <div className="text-caption text-ink-muted">
                {c.nome ? `${c.email} · ` : ""}
                {c.todas_filiais ? "Todas as filiais" : c.filiais.map((f) => f.nome).join(", ")}
              </div>
            </div>
            <StatusBadge tom="neutro" compacto>
              {ROTULO_DO_PERFIL[c.perfil]}
            </StatusBadge>
            <StatusBadge tom="alerta" compacto>
              Convite pendente
            </StatusBadge>
          </div>
        ))}
      </section>

      <section aria-label="O que cada perfil vê" className="flex flex-col gap-2 rounded-[20px] bg-surface-sunken p-4 text-caption">
        <div className="text-body font-semibold">O que cada perfil vê</div>
        <div>
          <b>Gerente:</b> <span className="text-ink-muted">tudo da filial, aprova descontos e cancelamentos.</span>
        </div>
        <div>
          <b>Vendedor:</b> <span className="text-ink-muted">clientes, propostas e as próprias vendas e comissões. Não vê custo nem margem.</span>
        </div>
        <div>
          <b>Vistoriador:</b> <span className="text-ink-muted">retirada e devolução pelo celular. Não vê valores.</span>
        </div>
        <div>
          <b>Financeiro:</b> <span className="text-ink-muted">contas a pagar e receber, caixa e relatórios.</span>
        </div>
      </section>

      <RodapeDoPasso voltarPara={voltarPara} pularPara={pularPara} rotuloDePular="Convidar depois" rotuloDeContinuar="Concluir" podeContinuar={feito} aoContinuar={aoContinuar} />

      {convidando && (
        <ConvidarPessoa
          eu={eu}
          aoFechar={() => setConvidando(false)}
          aoConcluir={(mensagem) => {
            setAviso(mensagem);
            void cliente.invalidateQueries({ queryKey: ["implantacao"] });
          }}
        />
      )}
    </section>
  );
}
