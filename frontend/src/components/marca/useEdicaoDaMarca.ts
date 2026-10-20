"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { marca as marcaApi, type MarcaEmpresa, type MarcaSimulada } from "@/lib/api";
import { campoDoErro } from "@/lib/erros";
import { corpoDaSimulacao, corpoDoSalvar, edicaoInicial, ESPERA_DA_COR_MS, logoVisivel, mudou, normalizarCor, type EdicaoDaMarca } from "@/lib/marca-edicao";

/**
 * Estado de quem edita a marca (Empresa e marca e passo Marca do assistente): o que está escolhido, a prévia
 * que a API calculou e o salvar. A tela não faz conta de cor: sem simulação, mostra a marca salva.
 */
export function useEdicaoDaMarca(guardada: MarcaEmpresa) {
  const cliente = useQueryClient();
  const [edicao, setEdicao] = useState<EdicaoDaMarca>(() => edicaoInicial(guardada));
  // Cor digitada espera 300 ms depois da última tecla; escolher uma das cores simula na hora.
  const [simulada, setSimulada] = useState({ nome: guardada.nome_exibicao, cor: guardada.cor });
  const imediato = useRef(false);
  const [urlLocal, setUrlLocal] = useState<string | null>(null);
  const arquivo = edicao.logo.tipo === "novo" ? edicao.logo.arquivo : null;

  useEffect(() => {
    if (!arquivo) {
      setUrlLocal(null);
      return;
    }
    const url = URL.createObjectURL(arquivo);
    setUrlLocal(url);
    return () => URL.revokeObjectURL(url);
  }, [arquivo]);

  useEffect(() => {
    if (imediato.current) {
      imediato.current = false;
      setSimulada({ nome: edicao.nome, cor: edicao.cor });
      return;
    }
    const t = setTimeout(() => setSimulada({ nome: edicao.nome, cor: edicao.cor }), ESPERA_DA_COR_MS);
    return () => clearTimeout(t);
  }, [edicao.nome, edicao.cor]);

  const corpo = useMemo(() => corpoDaSimulacao(simulada), [simulada]);
  const previa = useQuery({
    queryKey: ["marca-simulada", corpo?.cor ?? null, corpo?.nome_exibicao ?? null],
    queryFn: () => marcaApi.simular(corpo!),
    enabled: corpo !== null,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const salvar = useMutation({
    mutationFn: () => marcaApi.salvar(corpoDoSalvar(guardada, edicao)),
    onSuccess: async (nova) => {
      cliente.setQueryData(["marca"], nova);
      await cliente.invalidateQueries({ queryKey: ["marca"] });
      setEdicao(edicaoInicial(nova));
      imediato.current = true;
    },
  });

  const mostrada: MarcaSimulada = previa.data ?? {
    nome_exibicao: guardada.nome_exibicao,
    iniciais: guardada.iniciais,
    cor: guardada.cor,
    cor_sobre: guardada.cor_sobre,
    cor_suave: guardada.cor_suave,
    cor_suave_escuro: guardada.cor_suave_escuro,
  };

  const escolherCor = (hex: string) => {
    imediato.current = true;
    salvar.reset();
    setEdicao((e) => ({ ...e, cor: hex }));
  };
  const digitarCor = (texto: string) => {
    salvar.reset();
    setEdicao((e) => ({ ...e, cor: texto }));
  };
  const mudarNome = (nome: string) => {
    salvar.reset();
    setEdicao((e) => ({ ...e, nome }));
  };
  const escolherLogo = (a: File) => {
    salvar.reset();
    setEdicao((e) => ({ ...e, logo: { tipo: "novo", arquivo: a } }));
  };
  const removerLogo = () => {
    salvar.reset();
    setEdicao((e) => ({ ...e, logo: { tipo: "removido" } }));
  };
  const descartar = () => {
    salvar.reset();
    imediato.current = true;
    setEdicao(edicaoInicial(guardada));
  };

  const erro = (campo: string) => campoDoErro(salvar.error, campo) ?? (campo === "cor" || campo === "nome_exibicao" ? campoDoErro(previa.error, campo) : undefined);
  const algumErroDeCampo = ["cor", "nome_exibicao", "logo"].some((c) => erro(c));

  return {
    edicao,
    corNormalizada: normalizarCor(edicao.cor),
    previa: mostrada,
    logoUrl: logoVisivel(guardada, edicao.logo, urlLocal),
    mudou: mudou(guardada, edicao),
    salvar,
    erro,
    erroGeral: salvar.isError && !algumErroDeCampo ? salvar.error : null,
    escolherCor,
    digitarCor,
    mudarNome,
    escolherLogo,
    removerLogo,
    descartar,
  };
}
