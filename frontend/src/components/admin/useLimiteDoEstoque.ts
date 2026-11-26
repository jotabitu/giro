"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { marca as marcaApi, ErroApi } from "@/lib/api";

const CHAVE = ["estoque-da-empresa"];

/**
 * VEI-19 (T-486): o "Limite de dias em estoque" de Empresa e marca, gravado pelo mesmo Salvar da tela. A faixa (1 a 365) é
 * da API: o valor vai como digitado, e o 422 `VEI-19` volta com a mensagem para o campo.
 */
export function useLimiteDoEstoque() {
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: CHAVE, queryFn: () => marcaApi.estoque(), staleTime: 60_000 });
  const [digitado, setDigitado] = useState<string | null>(null);
  const salvo = consulta.data?.limite_dias_parado;
  const texto = digitado ?? (salvo != null ? String(salvo) : "");
  const mudou = digitado !== null && digitado !== String(salvo ?? "");

  const salvar = useMutation({
    mutationFn: () => {
      const limpo = texto.trim();
      return marcaApi.salvarEstoque(/^\d+$/.test(limpo) ? Number(limpo) : limpo);
    },
    onSuccess: (novo) => {
      cliente.setQueryData(CHAVE, novo);
      setDigitado(null);
    },
  });

  return {
    carregado: consulta.data !== undefined,
    podeEditar: consulta.data?.pode_editar ?? false,
    texto,
    mudou,
    salvar,
    erro: salvar.error instanceof ErroApi && salvar.error.codigo === "VEI-19" ? salvar.error.message : undefined,
    erroGeral: salvar.isError && !(salvar.error instanceof ErroApi && salvar.error.codigo === "VEI-19") ? salvar.error : null,
    digitar: (valor: string) => {
      salvar.reset();
      setDigitado(valor);
    },
    descartar: () => {
      salvar.reset();
      setDigitado(null);
    },
  };
}
