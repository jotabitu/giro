"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { contas } from "@/lib/api";
import { useTokenDoFragmento } from "@/lib/fragmento";
import { useGuardarSessao } from "@/lib/sessao";
import { TEXTO_SAIU_DO_SUPORTE, TEXTO_SUPORTE_TERMINOU } from "@/lib/suporte";
import { Aviso } from "./Aviso";
import { PaginaAcesso } from "./PaginaAcesso";

// Contrato: docs/api/contas.md, "Página de entrada e faixa no frontend". Referência: Plat-Suporte-Acesso (lado da plataforma) e Modo-Suporte.

/**
 * `/suporte/entrar#<token>`: lê o token do fragmento (que `useTokenDoFragmento` apaga da barra antes de qualquer chamada),
 * guarda só em memória, confere com `GET /api/auth/eu/` e entra no início. Sem token, ou com 401, mostra que o acesso terminou:
 * o suporte não tem login na empresa, então não há botão de entrar.
 */
export function EntradaDoSuporte() {
  const { pronto, token } = useTokenDoFragmento();
  const saiu = useSearchParams().get("saiu") === "1";
  const router = useRouter();
  const guardarSessao = useGuardarSessao();
  const [falhou, setFalhou] = useState(false);
  const iniciou = useRef(false);

  useEffect(() => {
    if (!token || iniciou.current) return;
    iniciou.current = true;
    contas
      .entrarComoSuporte(token)
      .then((eu) => {
        guardarSessao(eu);
        router.replace(eu.navegacao.inicio.rota);
      })
      .catch(() => setFalhou(true));
  }, [token, guardarSessao, router]);

  const entrando = !pronto || (token !== null && !falhou);
  if (entrando) {
    return (
      <PaginaAcesso titulo="Modo suporte">
        <p className="text-body text-ink-muted" aria-busy="true">
          Entrando no modo suporte…
        </p>
      </PaginaAcesso>
    );
  }

  const saida = saiu && !falhou;
  return (
    <PaginaAcesso titulo={saida ? TEXTO_SAIU_DO_SUPORTE : TEXTO_SUPORTE_TERMINOU}>
      <Aviso>
        {saida
          ? "Seu acesso de suporte foi encerrado. Para entrar de novo, abra um novo acesso pelo Giro."
          : "Para entrar de novo, abra um novo acesso pelo Giro. O suporte não tem login na empresa."}
      </Aviso>
    </PaginaAcesso>
  );
}
