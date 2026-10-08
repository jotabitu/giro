"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, Icone, TextField } from "@/design-system";
import { contas, ErroApi } from "@/lib/api";
import { useTokenDoFragmento } from "@/lib/fragmento";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { regrasDeSenha } from "@/lib/senha";
import { Aviso } from "./Aviso";
import { PaginaAcesso, Passo } from "./PaginaAcesso";
import { RegrasDeSenha } from "./RegrasDeSenha";

const esquema = z
  .object({ senha: z.string().min(1, "Crie uma senha"), repita: z.string().min(1, "Repita a senha") })
  .refine((v) => v.senha === v.repita, { path: ["repita"], message: "As senhas não são iguais" });
type Campos = z.infer<typeof esquema>;

/** Esqueci a senha, estados 3 e 4 (Esqueci-Senha): nova senha com o token do e-mail, ou link vencido. */
export function RedefinirSenha() {
  const { pronto, token } = useTokenDoFragmento();
  const router = useRouter();
  const [vencido, setVencido] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Campos>({ resolver: zodResolver(esquema), defaultValues: { senha: "", repita: "" } });

  async function salvar(v: Campos) {
    setErro(null);
    try {
      await contas.redefinirSenha({ token: token!, senha_nova: v.senha });
      router.replace("/entrar");
    } catch (e) {
      if (e instanceof ErroApi && e.codigo === "link_expirado") setVencido(true);
      else if (campoDoErro(e, "senha_nova")) setError("senha", { message: campoDoErro(e, "senha_nova") });
      else setErro(mensagemDoErro(e));
    }
  }

  if (!pronto) {
    return (
      <PaginaAcesso titulo="Crie a nova senha">
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      </PaginaAcesso>
    );
  }

  if (vencido || token === null) {
    return (
      <PaginaAcesso titulo="Esqueci a senha">
        <Passo numero={<Icone de={TriangleAlert} />} titulo="Link vencido">
          <Aviso tipo="erro">Este link venceu. Peça outro.</Aviso>
          <div className="grid md:flex">
            <Link className="wl-btn wl-btn--solid" href="/entrar/esqueci">
              Pedir novo link
            </Link>
          </div>
          <Link href="/entrar" className="text-caption font-medium underline">
            Voltar para entrar
          </Link>
        </Passo>
      </PaginaAcesso>
    );
  }

  return (
    <PaginaAcesso titulo="Crie a nova senha">
      <Passo numero={3} titulo="Crie a nova senha">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit(salvar)} noValidate>
          <TextField cheio rotulo="Nova senha" type="password" autoComplete="new-password" erro={errors.senha?.message} {...register("senha")} />
          <RegrasDeSenha regras={regrasDeSenha(watch("senha"))} />
          <TextField cheio rotulo="Repita a senha" type="password" autoComplete="new-password" erro={errors.repita?.message} {...register("repita")} />
          <Aviso>Ao salvar, sua conta sai de todos os aparelhos. Se você usa a verificação em 2 etapas, continua precisando do código do aplicativo.</Aviso>
          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          <div className="grid md:flex">
            <Button type="submit" variante="solido" disabled={isSubmitting}>
              {isSubmitting ? "Salvando…" : "Salvar nova senha"}
            </Button>
          </div>
        </form>
      </Passo>
    </PaginaAcesso>
  );
}
