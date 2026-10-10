"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { aplicarMarca } from "@/design-system";
import type { Eu, MarcaEmpresa } from "@/lib/api";

// Ainda não existe contrato de marca da empresa (logo e cor: tela Admin-Marca, app `empresas`). Até lá o nome vem de
// `eu.empresa.nome_exibicao`, a cor fica a do design system e a tela de login, sem sessão, usa o texto neutro abaixo.
const SEM_SESSAO: MarcaEmpresa = { nome: "Sua locadora" };

/** Marca da locadora (logo, cor, nome): aplica --brand, --on-brand e --brand-soft quando a API trouxer a cor. */
export function useMarcaDaEmpresa(): MarcaEmpresa {
  const { data } = useQuery<Eu>({ queryKey: ["eu"], enabled: false });
  const marca: MarcaEmpresa = data ? { nome: data.empresa.nome_exibicao } : SEM_SESSAO;
  useEffect(() => {
    if (marca.corHex) aplicarMarca(marca.corHex);
  }, [marca.corHex]);
  return marca;
}
