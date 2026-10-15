"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Button, Icone, TextField } from "@/design-system";
import { assinar, ErroApi } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataHoraCurta } from "@/lib/formatos";
import { useTokenDoFragmento } from "@/lib/fragmento";
import { Aviso } from "../acesso/Aviso";
import { PaginaAcesso, Passo } from "../acesso/PaginaAcesso";

// Página pública de assinatura (S-15, docs/api/contratos.md), aberta pelo link `/assinar#<token>` no celular do cliente.
// Sem login. O token sai do fragmento, fica só em memória e vai no corpo das duas chamadas.

function titulo(erro: unknown): string {
  if (erro instanceof ErroApi && erro.codigo === "link_expirado") return "Link vencido";
  if (erro instanceof ErroApi && erro.codigo === "contrato_ja_assinado") return "Contrato já assinado";
  return "Link não encontrado";
}

// O 404 de token desconhecido vem sem o corpo padrão da API (docs/api/contratos.md só diz 404): o texto é daqui.
function texto(erro: unknown): string {
  return erro instanceof ErroApi && erro.status === 404 ? "Este link não existe mais. Peça um novo à locadora." : mensagemDoErro(erro);
}

/** Assinatura do contrato pelo cliente: lê o contrato, pede o nome completo e o aceite. */
export function AssinarContrato() {
  const { pronto, token } = useTokenDoFragmento();
  const [nome, setNome] = useState("");
  const [aceite, setAceite] = useState(false);

  const consulta = useQuery({ queryKey: ["assinar"], queryFn: () => assinar.consultar({ token: token! }), enabled: token !== null, retry: false, retryOnMount: false, staleTime: Infinity });
  const enviar = useMutation({ mutationFn: () => assinar.assinar({ token: token!, aceite, nome_completo: nome.trim() }) });

  if (pronto && token === null) {
    return (
      <PaginaAcesso titulo="Link não encontrado">
        <Aviso tipo="erro">Este link não tem o contrato. Abra o link completo que a locadora enviou ou peça um novo.</Aviso>
      </PaginaAcesso>
    );
  }

  if (!pronto || consulta.isPending) {
    return (
      <PaginaAcesso titulo="Assinar contrato">
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando o contrato…
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

  const c = consulta.data.contrato;

  if (enviar.isSuccess) {
    return (
      <PaginaAcesso titulo="Contrato assinado" descricao={`Obrigado, ${c.cliente_nome.split(" ")[0]}. A locadora já recebeu a sua assinatura.`}>
        <Passo numero={<Icone de={FileText} />} titulo={c.titulo}>
          <p className="text-body">
            <span className="wl-mono">{c.codigo}</span> · assinado em {dataHoraCurta(enviar.data.assinado_em)}
          </p>
          <p className="text-caption text-ink-muted">Você pode fechar esta página. A locadora guarda uma cópia com o registro da assinatura.</p>
        </Passo>
      </PaginaAcesso>
    );
  }

  const erroGeral = enviar.isError && !campoDoErro(enviar.error, "nome_completo") && !campoDoErro(enviar.error, "aceite");
  // Link vencido ou já usado durante a assinatura: a tela explica em vez de deixar o formulário tentando de novo.
  if (enviar.error instanceof ErroApi && enviar.error.status === 410) {
    return (
      <PaginaAcesso titulo={titulo(enviar.error)}>
        <Aviso tipo="erro">{mensagemDoErro(enviar.error)}</Aviso>
      </PaginaAcesso>
    );
  }

  function assinarAgora(e: FormEvent) {
    e.preventDefault();
    enviar.mutate();
  }

  return (
    <PaginaAcesso titulo={c.titulo} descricao="Leia o contrato e confirme com o seu nome completo.">
      <Passo numero={1} titulo="Contrato">
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className="grid size-[52px] shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted">
            <Icone de={FileText} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="wl-mono text-body font-medium">{c.codigo}</div>
            <div className="text-caption text-ink-muted">Para {c.cliente_nome}</div>
          </div>
        </div>
        {c.pdf_url ? (
          <a href={c.pdf_url} target="_blank" rel="noopener noreferrer" className="wl-btn w-full justify-center md:w-auto">
            Ler o contrato (PDF)
          </a>
        ) : (
          <Aviso>O PDF não está disponível agora. Peça à locadora para reenviar o link.</Aviso>
        )}
      </Passo>
      <Passo numero={2} titulo="Sua assinatura">
        <form className="flex flex-col gap-4" onSubmit={assinarAgora} noValidate>
          <TextField cheio rotulo="Nome completo" autoComplete="name" value={nome} onChange={(e) => setNome(e.target.value)} dica="Como está no seu cadastro na locadora." erro={campoDoErro(enviar.error, "nome_completo")} />
          <div>
            <label className="flex min-h-11 items-start gap-3 text-body">
              <input type="checkbox" checked={aceite} onChange={(e) => setAceite(e.target.checked)} className="wl-marcar mt-1" />
              <span>Li o contrato e concordo com os termos.</span>
            </label>
            {campoDoErro(enviar.error, "aceite") && (
              <p role="alert" className="text-caption text-critical">
                {campoDoErro(enviar.error, "aceite")}
              </p>
            )}
          </div>
          {erroGeral && <Aviso tipo="erro">{mensagemDoErro(enviar.error)}</Aviso>}
          <div className="grid md:flex">
            <Button type="submit" variante="solido" disabled={!nome.trim() || !aceite || enviar.isPending}>
              {enviar.isPending ? "Assinando…" : "Assinar contrato"}
            </Button>
          </div>
          <p className="text-caption text-ink-muted">Ao assinar, ficam registrados a data, a hora e o aparelho que você está usando.</p>
        </form>
      </Passo>
    </PaginaAcesso>
  );
}
