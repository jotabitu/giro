"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ErroApi, veiculos, type GaleriaDoEditar as Galeria } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { GaleriaDeFotos, type RecusaDeFoto } from "./GaleriaDeFotos";

// VEI-10. Contrato: docs/api/veiculos.md, "Fotos do veículo". Uma foto por requisição, na ordem da escolha;
// a recusa de cada uma aparece com o nome do arquivo e as outras seguem (CA-414-02, 03).

const FOTO_INVALIDA = "Envie uma foto JPG ou PNG de até 10 MB.";

export function mensagemDaRecusa(e: unknown): string {
  // Acima de 12 MB o proxy responde 413 antes do Django: a mensagem é a mesma do formato.
  if (e instanceof ErroApi && e.status === 413) return FOTO_INVALIDA;
  return campoDoErro(e, "arquivo") ?? mensagemDoErro(e);
}

export function GaleriaDoEditar({ id }: { id: number }) {
  const cliente = useQueryClient();
  const chave = ["veiculo", id, "fotos"] as const;
  const consulta = useQuery({ queryKey: chave, queryFn: () => veiculos.fotos(id) });
  const [recusas, setRecusas] = useState<RecusaDeFoto[]>([]);
  const [progresso, setProgresso] = useState<string | null>(null);

  const guardar = (g: Galeria) => {
    cliente.setQueryData(chave, g);
    void cliente.invalidateQueries({ queryKey: ["veiculo", id], exact: true });
  };
  const recusar = (nome: string, e: unknown) => setRecusas((r) => [...r, { chave: `${nome}-${r.length}`, nome, mensagem: mensagemDaRecusa(e) }]);

  const enviar = useMutation({
    mutationFn: async (arquivos: File[]) => {
      setRecusas([]);
      for (const [i, a] of arquivos.entries()) {
        setProgresso(arquivos.length > 1 ? `Enviando ${i + 1} de ${arquivos.length}…` : "Enviando…");
        try {
          guardar(await veiculos.enviarFoto(id, a));
        } catch (e) {
          recusar(a.name, e);
        }
      }
      setProgresso(null);
    },
  });
  const trocar = useMutation({
    mutationFn: async ({ fotoId, arquivo }: { fotoId: number; arquivo: File }) => {
      setRecusas([]);
      try {
        guardar(await veiculos.trocarFoto(id, fotoId, arquivo));
      } catch (e) {
        recusar(arquivo.name, e);
      }
    },
  });
  const capa = useMutation({ mutationFn: (fotoId: number) => veiculos.usarComoCapa(id, fotoId), onSuccess: guardar });
  const apagar = useMutation({ mutationFn: (fotoId: number) => veiculos.apagarFoto(id, fotoId), onSuccess: guardar });

  const g = consulta.data;
  const ocupado = [enviar, trocar, capa, apagar].some((m) => m.isPending);
  const erroDaAcao = [capa, apagar].find((m) => m.isError)?.error;

  if (consulta.isPending) return <p className="text-body text-ink-muted" aria-busy="true">Carregando as fotos…</p>;
  if (consulta.isError || !g) return <p role="alert" className="text-body">{mensagemDoErro(consulta.error)}</p>;
  return (
    <>
      <GaleriaDeFotos
        fotos={g.fotos}
        total={g.total}
        limite={g.limite}
        podeEditar={g.editar}
        motivo={g.motivo}
        ocupado={ocupado}
        progresso={progresso}
        recusas={recusas}
        aoDispensarRecusas={() => setRecusas([])}
        aoEnviar={(arquivos) => enviar.mutate(arquivos)}
        aoTrocar={(f, arquivo) => trocar.mutate({ fotoId: f.id, arquivo })}
        aoUsarComoCapa={(f) => capa.mutate(f.id)}
        aoApagar={(f) => apagar.mutate(f.id)}
      />
      {erroDaAcao && (
        <p role="alert" className="text-body text-critical-ink">
          {mensagemDoErro(erroDaAcao)}
        </p>
      )}
    </>
  );
}
