"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, StatusBadge, TextField } from "@/design-system";
import { contas, ErroApi, type Eu, type Perfil } from "@/lib/api";
import { useTokenDoFragmento } from "@/lib/fragmento";
import { aparelhoAtual, campoDoErro, mensagemDoErro } from "@/lib/erros";
import { regrasDeSenha } from "@/lib/senha";
import { useGuardarSessao } from "@/lib/sessao";
import { Ativar2fa } from "./Ativar2fa";
import { Aviso } from "./Aviso";
import { PaginaAcesso, Passo } from "./PaginaAcesso";
import { RegrasDeSenha } from "./RegrasDeSenha";

const ROTULO_PERFIL: Record<Perfil, string> = {
  administrador: "Administrador",
  gerente: "Gerente",
  vendedor: "Vendedor",
  vistoriador: "Vistoriador",
  financeiro: "Financeiro",
};

const esquema = z.object({ nome: z.string().trim().min(1, "Informe seu nome"), senha: z.string().min(1, "Crie uma senha") });
type Campos = z.infer<typeof esquema>;

function Fato({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-line py-3 text-body last:border-b-0">
      <span className="text-ink-muted">{rotulo}</span>
      <span className="text-right">{children}</span>
    </div>
  );
}

/** Aceite do convite (Convite-Desktop|Mobile, passo 2): confere os dados e cria a senha. */
export function AceitarConvite() {
  const { pronto, token } = useTokenDoFragmento();
  const router = useRouter();
  const guardar = useGuardarSessao();
  const [erro, setErro] = useState<string | null>(null);
  const [configurar, setConfigurar] = useState<string | null>(null);

  const convite = useQuery({ queryKey: ["convite"], queryFn: () => contas.consultarConvite({ token: token! }), enabled: token !== null, retry: false });
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Campos>({ resolver: zodResolver(esquema), values: { nome: convite.data?.nome ?? "", senha: "" } });

  function concluir(usuario: Eu) {
    guardar(usuario);
    router.replace("/inicio");
  }

  async function criar(v: Campos) {
    setErro(null);
    try {
      const r = await contas.aceitarConvite({ token: token!, nome: v.nome, senha: v.senha, aparelho: aparelhoAtual() });
      if (r.etapa === "pronto") concluir(r.usuario);
      else if (r.etapa === "configurar_2fa") setConfigurar(r.token_pre_2fa);
    } catch (e) {
      const doCampo = campoDoErro(e, "senha");
      if (doCampo) setError("senha", { message: doCampo });
      else setErro(mensagemDoErro(e));
    }
  }

  if (configurar) return <Ativar2fa tokenPre={configurar} exige aoConcluir={concluir} />;

  if (pronto && token === null) {
    return (
      <PaginaAcesso titulo="Convite não encontrado">
        <Aviso tipo="erro">Este link não tem o convite. Abra o link completo do e-mail ou peça um novo ao administrador.</Aviso>
        <Link href="/entrar" className="text-caption font-medium underline">
          Ir para entrar
        </Link>
      </PaginaAcesso>
    );
  }

  if (!pronto || convite.isPending) {
    return (
      <PaginaAcesso titulo="Crie seu acesso">
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando o convite…
        </p>
      </PaginaAcesso>
    );
  }

  if (convite.isError) {
    const vencido = convite.error instanceof ErroApi && convite.error.status === 410;
    return (
      <PaginaAcesso titulo={vencido ? "Convite vencido" : "Convite não encontrado"}>
        <Aviso tipo="erro">{mensagemDoErro(convite.error)}</Aviso>
        <Link href="/entrar" className="text-caption font-medium underline">
          Ir para entrar
        </Link>
      </PaginaAcesso>
    );
  }

  const c = convite.data;
  return (
    <PaginaAcesso titulo="Crie seu acesso" descricao="Confira os dados do convite e escolha sua senha.">
      <Passo numero={1} titulo="Dados do convite">
        <div>
          <Fato rotulo="Empresa">{c.empresa}</Fato>
          <Fato rotulo="Perfil">
            <StatusBadge tom="solido" compacto>
              {ROTULO_PERFIL[c.perfil]}
            </StatusBadge>
          </Fato>
          <Fato rotulo={c.filiais.length > 1 ? "Filiais" : "Filial"}>{c.filiais.map((f) => f.nome).join(", ")}</Fato>
          <Fato rotulo="Convidado por">{c.convidado_por}</Fato>
        </div>
      </Passo>
      <Passo numero={2} titulo="Seu acesso">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit(criar)} noValidate>
          <TextField cheio rotulo="Seu nome" autoComplete="name" erro={errors.nome?.message} {...register("nome")} />
          <TextField
            cheio
            rotulo="Senha"
            type="password"
            autoComplete="new-password"
            dica={c.exige_2fa ? "12 caracteres ou mais. Seu perfil ativa a verificação em duas etapas a seguir." : "12 caracteres ou mais."}
            erro={errors.senha?.message}
            {...register("senha")}
          />
          <RegrasDeSenha regras={regrasDeSenha(watch("senha"), c.email)} />
          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          <div className="grid md:flex">
            <Button type="submit" variante="solido" disabled={isSubmitting}>
              {isSubmitting ? "Criando…" : "Criar acesso e entrar"}
            </Button>
          </div>
        </form>
      </Passo>
    </PaginaAcesso>
  );
}
