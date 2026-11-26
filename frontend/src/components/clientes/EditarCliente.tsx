"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { clientes, type ClienteCompleto, type ClienteResumo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { useSessao } from "@/lib/sessao";
import { NovoClienteForm } from "./NovoClienteForm";

const completo = (c: ClienteResumo | ClienteCompleto): c is ClienteCompleto => "documentos" in c;

/** Editar cliente (T-516, PATCH /api/clientes/{id}/): carrega a ficha completa e abre o formulário do cadastro com os dados dela. */
export function EditarCliente({ id }: { id: number }) {
  const { eu } = useSessao();
  const consulta = useQuery({ queryKey: ["cliente", id], queryFn: () => clientes.obter(id) });
  const voltar = (
    <Link href={`/clientes/${id}`} className="text-body text-ink-muted">
      Voltar para o cliente
    </Link>
  );

  if (consulta.isError) {
    return (
      <div className="flex flex-col gap-4">
        {voltar}
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
  if (!eu.pode.clientes_cadastrar || !completo(c)) {
    return (
      <div className="flex flex-col gap-4">
        {voltar}
        <p role="alert" className="wl-panel text-body">
          Seu perfil não tem acesso a esta ação.
        </p>
      </div>
    );
  }
  return <NovoClienteForm cliente={c} />;
}
