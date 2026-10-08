"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Info } from "lucide-react";
import { Icone, Panel, StatusBadge } from "@/design-system";
import { clientes, type ClienteCompleto, type TipoDocumentoCliente } from "@/lib/api";
import { textoDePendencias } from "@/lib/clientes";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { celular, dataCompleta } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";
import { useSessao } from "@/lib/sessao";
import { AnaliseDoCadastro } from "./AnaliseDoCadastro";
import { BotaoDocumento } from "./BotaoDocumento";

const completo = (c: unknown): c is ClienteCompleto => typeof c === "object" && c !== null && "documentos" in c;

/** Cadastro do cliente salvo: documentos para enviar, pendências e análise. A edição dos dados entra com o contrato de PATCH. */
export function CadastroDoCliente({ id }: { id: number }) {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["cliente", id], queryFn: () => clientes.obter(id) });
  const [erros, setErros] = useState<Partial<Record<TipoDocumentoCliente, string>>>({});
  const [enviando, setEnviando] = useState<TipoDocumentoCliente | null>(null);

  const enviar = useMutation({
    mutationFn: ({ tipo, arquivo }: { tipo: TipoDocumentoCliente; arquivo: File }) => clientes.enviarDocumento(id, tipo, arquivo),
    onMutate: ({ tipo }) => {
      setEnviando(tipo);
      setErros((e) => ({ ...e, [tipo]: undefined }));
    },
    onSuccess: (atualizado) => {
      cliente.setQueryData(["cliente", id], atualizado);
      void cliente.invalidateQueries({ queryKey: ["clientes"] });
    },
    onError: (e, { tipo }) => setErros((x) => ({ ...x, [tipo]: campoDoErro(e, "arquivo") ?? mensagemDoErro(e) })),
    onSettled: () => setEnviando(null),
  });

  if (consulta.isError) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/clientes" className="text-body text-ink">
          Clientes
        </Link>
        <p role="alert" className="wl-panel text-body">
          {mensagemDoErro(consulta.error)}
        </p>
      </div>
    );
  }
  const c = consulta.data;
  if (!c) {
    return (
      <p className="wl-panel text-body text-ink-muted" aria-busy="true">
        Carregando o cliente…
      </p>
    );
  }

  const dados = completo(c) ? c : null;
  const pendencias = dados ? textoDePendencias(dados.pendencias) : null;
  return (
    <div className="flex flex-col gap-6">
      <nav aria-label="Caminho" className="text-body text-ink-muted">
        <Link href="/clientes" className="text-ink">
          Clientes
        </Link>{" "}
        / {c.nome}
      </nav>

      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div>
          <h1 className="text-title md:text-display">{c.nome}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-caption text-ink-muted">
            <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
              {c.situacao.rotulo}
            </StatusBadge>
            <span className="wl-mono">{c.documento_mascarado}</span>
            <span>· {celular(c.celular)}</span>
            <span>· cliente desde {dataCompleta(c.cliente_desde)}</span>
          </div>
        </div>
        {eu.pode.locacoes_criar && c.status === "ativo" && (
          <Link href={`/locacoes/nova?cliente=${c.id}`} className="wl-btn wl-btn--solid md:ml-auto">
            Iniciar locação
          </Link>
        )}
      </header>

      {pendencias && (
        <p className="flex items-start gap-3 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          <Icone de={Info} />
          <span>{pendencias}</span>
        </p>
      )}

      {dados ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <Panel titulo="Documentos" subtitulo="JPG, PNG ou PDF, até 10 MB">
            <div className="grid gap-3 md:grid-cols-2">
              {dados.documentos.map((d) => (
                <BotaoDocumento
                  key={d.tipo}
                  tipo={d.tipo}
                  enviado={d.enviado_em !== null}
                  enviando={enviando === d.tipo}
                  erro={erros[d.tipo]}
                  aoEscolher={(arquivo) => enviar.mutate({ tipo: d.tipo, arquivo })}
                />
              ))}
            </div>
          </Panel>
          <AnaliseDoCadastro analise={dados.analise} />
        </div>
      ) : (
        <p className="wl-panel text-body text-ink-muted">Seu perfil vê só o resumo do cliente. Os dados completos e os documentos ficam com quem cadastra.</p>
      )}
    </div>
  );
}
