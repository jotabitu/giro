"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, Icone, StatusBadge, TextField } from "@/design-system";
import { contas, type Eu } from "@/lib/api";
import { aparelhoAtual, mensagemDoErro } from "@/lib/erros";
import { useEnderecoSemEmpresa } from "@/lib/endereco";
import { useGuardarSessao } from "@/lib/sessao";
import { Aviso } from "./Aviso";
import { Ativar2fa } from "./Ativar2fa";
import { CabecalhoMarca, RodapeGiro } from "./CabecalhoMarca";
import { EnderecoSemEmpresa } from "./EnderecoSemEmpresa";
import { VerificarCodigo } from "./VerificarCodigo";

const esquema = z.object({
  email: z.string().trim().min(1, "Informe o e-mail").email("Confira o e-mail"),
  senha: z.string().min(1, "Informe a senha"),
});
type Campos = z.infer<typeof esquema>;

type Etapa = { nome: "credenciais" } | { nome: "verificar"; token: string } | { nome: "configurar"; token: string };

/** Login (Login-Desktop|Mobile). Segue a `etapa` que a API devolve; não decide quem precisa de 2 etapas (USR-02). */
export function FluxoEntrar() {
  const router = useRouter();
  const guardar = useGuardarSessao();
  const semEmpresa = useEnderecoSemEmpresa();
  const [etapa, setEtapa] = useState<Etapa>({ nome: "credenciais" });
  const [erro, setErro] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Campos>({ resolver: zodResolver(esquema), defaultValues: { email: "", senha: "" } });

  function concluir(usuario: Eu) {
    guardar(usuario);
    router.replace("/inicio");
  }

  async function entrar(v: Campos) {
    setErro(null);
    try {
      const r = await contas.entrar({ email: v.email, senha: v.senha, aparelho: aparelhoAtual() });
      if (r.etapa === "pronto") concluir(r.usuario);
      else if (r.etapa === "verificar_2fa") setEtapa({ nome: "verificar", token: r.token_pre_2fa });
      else setEtapa({ nome: "configurar", token: r.token_pre_2fa });
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  if (semEmpresa) return <EnderecoSemEmpresa />;

  if (etapa.nome === "configurar") {
    return <Ativar2fa tokenPre={etapa.token} exige aoConcluir={concluir} />;
  }

  return (
    <div className="flex min-h-screen flex-col gap-4 bg-canvas p-4 md:flex-row md:gap-6 md:p-6">
      <section className="flex flex-1 flex-col rounded-xl bg-surface p-6 md:basis-[480px] md:p-10">
        <div className="hidden md:block">
          <CabecalhoMarca />
        </div>
        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-6 md:py-10">
          {etapa.nome === "verificar" ? (
            <VerificarCodigo tokenPre={etapa.token} aoConcluir={concluir} aoVoltar={() => setEtapa({ nome: "credenciais" })} />
          ) : (
            <form className="flex flex-col gap-5" onSubmit={handleSubmit(entrar)} noValidate>
              <div>
                <h1 className="text-title md:text-display">Entrar</h1>
                <p className="mt-2 hidden text-body text-ink-muted md:block">Acesse a gestão da sua frota, contratos e caixa.</p>
              </div>
              <TextField cheio rotulo="E-mail" type="email" placeholder="voce@empresa.com.br" autoComplete="username" erro={errors.email?.message} {...register("email")} />
              <div className="flex flex-col gap-2">
                <TextField cheio rotulo="Senha" type="password" placeholder="Sua senha" autoComplete="current-password" erro={errors.senha?.message} {...register("senha")} />
                <Link href="/entrar/esqueci" className="self-end text-caption font-medium underline">
                  Esqueci a senha
                </Link>
              </div>
              {erro && <Aviso tipo="erro">{erro}</Aviso>}
              <div className="grid">
                <Button type="submit" variante="solido" disabled={isSubmitting}>
                  {isSubmitting ? "Entrando…" : "Entrar"}
                </Button>
              </div>
              <div className="hidden items-center gap-2 rounded-md bg-surface-sunken p-4 text-caption text-ink-muted md:flex">
                <Icone de={Lock} />
                Perfis de administrador e financeiro pedem o código do aplicativo autenticador no próximo passo.
              </div>
            </form>
          )}
        </div>
        <RodapeGiro />
      </section>

      <section className="order-first flex h-[248px] flex-col justify-between rounded-xl bg-brand p-6 text-on-brand md:order-none md:h-auto md:min-h-[600px] md:flex-1 md:basis-[520px] md:p-10">
        <div className="md:hidden">
          <CabecalhoMarca />
        </div>
        <p className="max-w-[480px] text-title md:text-display">Sua frota, seus contratos e seu caixa no mesmo lugar.</p>
        <div className="hidden flex-wrap gap-2 md:flex" aria-hidden="true">
          {["Locação", "Venda", "Manutenção", "Financeiro"].map((t) => (
            <StatusBadge key={t} tom="superficie">
              {t}
            </StatusBadge>
          ))}
        </div>
      </section>
    </div>
  );
}
