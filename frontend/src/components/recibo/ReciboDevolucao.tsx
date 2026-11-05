"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { Button, Icone } from "@/design-system";
import { ErroApi, recibo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataHoraCompleta } from "@/lib/formatos";
import { useTokenDoFragmento } from "@/lib/fragmento";
import { Aviso } from "../acesso/Aviso";
import { PaginaAcesso, Passo } from "../acesso/PaginaAcesso";

// Página pública do recibo da devolução (DEV-02, S-15, AUD-05, docs/api/vistorias.md), aberta pelo link `/recibo#<token>`.
// Sem login. O token sai do fragmento, fica só em memória e vai no corpo de cada chamada.

const LINK_VENCIDO = "Este link venceu ou não existe. Peça um novo à locadora.";

function titulo(erro: unknown): string {
  return erro instanceof ErroApi && (erro.status === 404 || erro.status === 410) ? "Link não encontrado" : "Recibo da devolução";
}

// 404 e 410 têm o mesmo texto: a API não diz qual dos dois aconteceu (token desconhecido, anulado ou vencido).
function texto(erro: unknown): string {
  return erro instanceof ErroApi && (erro.status === 404 || erro.status === 410) ? LINK_VENCIDO : mensagemDoErro(erro);
}

/** Abre o PDF numa aba. A aba nasce no clique (sem bloqueio de pop-up) e recebe a URL quando a API responde. */
function abrirPdf(url: string, aba: Window | null) {
  if (aba) aba.location.href = url;
  else window.location.assign(url);
}

/** Recibo da devolução para o cliente final: marca da locadora, código, primeiro nome e "Baixar recibo". */
export function ReciboDevolucao() {
  const { pronto, token } = useTokenDoFragmento();

  const consulta = useQuery({ queryKey: ["recibo"], queryFn: () => recibo.consultar({ token: token! }), enabled: token !== null, retry: false, retryOnMount: false, staleTime: Infinity, gcTime: 0 });
  // A URL do PDF vale 15 minutos (AUD-05): cada clique pede uma nova, em vez de reusar a da primeira consulta.
  const baixar = useMutation({
    mutationFn: async (aba: Window | null) => {
      try {
        const r = await recibo.consultar({ token: token! });
        abrirPdf(r.recibo.pdf_url, aba);
      } catch (e) {
        aba?.close();
        throw e;
      }
    },
  });

  if (pronto && token === null) {
    return (
      <PaginaAcesso titulo="Link não encontrado">
        <Aviso tipo="erro">{LINK_VENCIDO}</Aviso>
      </PaginaAcesso>
    );
  }

  if (!pronto || consulta.isPending) {
    return (
      <PaginaAcesso titulo="Recibo da devolução">
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando o recibo…
        </p>
      </PaginaAcesso>
    );
  }

  if (consulta.isError) {
    return (
      <PaginaAcesso titulo={titulo(consulta.error)}>
        <Aviso tipo="erro">{texto(consulta.error)}</Aviso>
      </PaginaAcesso>
    );
  }

  const r = consulta.data.recibo;

  function baixarAgora() {
    // O pop-up tem que abrir dentro do clique; `opener = null` impede a aba de voltar à página do recibo.
    const aba = window.open("about:blank", "_blank");
    if (aba) aba.opener = null;
    baixar.mutate(aba);
  }

  return (
    <PaginaAcesso titulo={`Recibo da devolução da ${r.codigo}`} descricao={`Olá, ${r.cliente_primeiro_nome}. Aqui está o recibo da devolução${r.concluida_em ? `, concluída em ${dataHoraCompleta(r.concluida_em)}` : ""}.`}>
      <Passo numero={<Icone de={FileText} />} titulo="Recibo">
        <p className="text-body">
          <span className="wl-mono">{r.codigo}</span> · devolução concluída
        </p>
        {baixar.isError && <Aviso tipo="erro">{texto(baixar.error)}</Aviso>}
        <div className="grid md:flex">
          <Button type="button" variante="solido" onClick={baixarAgora} disabled={baixar.isPending}>
            {baixar.isPending ? "Abrindo…" : "Baixar recibo"}
          </Button>
        </div>
        <p className="text-caption text-ink-muted">O PDF abre numa nova aba. Se o link da locadora venceu, peça um novo.</p>
      </Passo>
    </PaginaAcesso>
  );
}
