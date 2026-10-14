"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { avisoDoKmDaApi } from "@/lib/vistorias";
import { vistorias, type PendenciaDaVistoria, type AvariaDaVistoria, type EdicaoDaVistoria, type PosicaoFoto, type Vistoria } from "@/lib/api";
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

  // A vistoria só traz o código curto da pendência ("km"). A mensagem do VEI-01 ("O km informado é menor que o atual…") vem do 422 da conclusão,
  // então, com um km digitado que a API ainda aponta como pendência, a tela pergunta a ela e mostra a mensagem no campo do km.
  const [avisoDoKm, setAvisoDoKm] = useState<PendenciaDaVistoria | null>(null);
  const editar = useMutation({
    mutationFn: (patch: EdicaoDaVistoria) => vistorias.editar(id ?? 0, patch),
    onSuccess: (v, patch) => {
      guardar(v);
      if ("km" in patch) void avisoDoKmDaApi(v).then(setAvisoDoKm);
    },
  });
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
    /** A pendência `VEI-01` da API (km menor que o do veículo), para mostrar no campo do km; `null` quando não há. */
    avisoDoKm: consulta.data?.pendencias.includes("km") ? avisoDoKm : null,
    /** Texto do último erro de edição, foto ou avaria; `null` quando está tudo certo. */
    erro: erroDeEdicao ? mensagemDoErro(erroDeEdicao) : null,
  };
}

export type VistoriaEmEdicao = ReturnType<typeof useVistoriaEmEdicao>;
