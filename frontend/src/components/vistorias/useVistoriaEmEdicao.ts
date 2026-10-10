"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { vistorias, type AvariaDaVistoria, type EdicaoDaVistoria, type PosicaoFoto, type Vistoria } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";

/**
 * A vistoria em edição (saída ou chegada). Cada mudança vai para a API na hora (o `PATCH` é o "Salvar e continuar depois", DEV-05)
 * e a resposta, que traz as pendências e se pode concluir, substitui o que está na tela.
 */
export function useVistoriaEmEdicao(id: number | undefined, aoMudar?: () => void) {
  const cache = useQueryClient();
  const chave = ["vistoria", id] as const;
  const consulta = useQuery({ queryKey: chave, queryFn: () => vistorias.obter(id ?? 0), enabled: id !== undefined, retry: false });
  const [fotoEnviando, setFotoEnviando] = useState<PosicaoFoto | null>(null);

  const guardar = (v: Vistoria) => {
    cache.setQueryData(chave, v);
    aoMudar?.();
  };

  const editar = useMutation({ mutationFn: (patch: EdicaoDaVistoria) => vistorias.editar(id ?? 0, patch), onSuccess: guardar });
  const foto = useMutation({
    mutationFn: async ({ posicao, arquivo }: { posicao: PosicaoFoto; arquivo: File }) => {
      setFotoEnviando(posicao);
      await vistorias.enviarFoto(id ?? 0, posicao, arquivo);
      return vistorias.obter(id ?? 0);
    },
    onSuccess: guardar,
    onSettled: () => setFotoEnviando(null),
  });
  const avaria = useMutation({
    mutationFn: async ({ descricao, arquivo, oficina }: { descricao: string; arquivo: File; oficina: boolean }) => {
      await vistorias.enviarFoto(id ?? 0, "avaria", arquivo);
      const atual = await vistorias.obter(id ?? 0);
      const ultima = [...atual.fotos].reverse().find((f) => f.posicao === "avaria");
      return vistorias.registrarAvaria(id ?? 0, { descricao, foto_id: ultima?.id ?? 0, vai_para_oficina: oficina });
    },
    onSuccess: guardar,
  });
  const remover = useMutation({ mutationFn: (a: AvariaDaVistoria) => vistorias.removerAvaria(id ?? 0, a.id), onSuccess: guardar });
  const concluir = useMutation({ mutationFn: () => vistorias.concluir(id ?? 0), onSuccess: guardar });

  const erroDeEdicao = [editar.error, foto.error, remover.error].find(Boolean);
  return {
    vistoria: consulta.data,
    consulta,
    editar,
    foto,
    avaria,
    remover,
    concluir,
    fotoEnviando,
    /** Texto do último erro de edição, foto ou avaria; `null` quando está tudo certo. */
    erro: erroDeEdicao ? mensagemDoErro(erroDeEdicao) : null,
  };
}

export type VistoriaEmEdicao = ReturnType<typeof useVistoriaEmEdicao>;
