"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Mail } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, Icone, TextField } from "@/design-system";
import { contas } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { Aviso } from "./Aviso";
import { PaginaAcesso, Passo } from "./PaginaAcesso";

const esquema = z.object({ email: z.string().trim().min(1, "Informe o e-mail").email("Confira o e-mail") });
type Campos = z.infer<typeof esquema>;

/** Esqueci a senha, estados 1 e 2 (Esqueci-Senha). A API responde 202 sempre: a mensagem é a mesma exista ou não o e-mail. */
export function EsqueciSenha() {
  const [enviadoPara, setEnviadoPara] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Campos>({ resolver: zodResolver(esquema), defaultValues: { email: "" } });

  async function enviar(v: Campos) {
    setErro(null);
    try {
      await contas.esqueciSenha(v.email);
      setEnviadoPara(v.email);
    } catch (e) {
      setErro(mensagemDoErro(e));
    }
  }

  return (
    <PaginaAcesso
      titulo="Esqueci a senha"
      descricao="Informe o e-mail do seu acesso. Enviamos um link para criar uma senha nova."
    >
      {enviadoPara === null ? (
        <Passo numero={1} titulo="Peça o link">
          <form className="flex flex-col gap-4" onSubmit={handleSubmit(enviar)} noValidate>
            <TextField
              cheio
              rotulo="E-mail"
              type="email"
              placeholder="voce@empresa.com.br"
              autoComplete="username"
              dica="Use o e-mail do seu acesso."
              erro={errors.email?.message}
              {...register("email")}
            />
            {erro && <Aviso tipo="erro">{erro}</Aviso>}
            <div className="grid md:flex">
              <Button type="submit" variante="solido" disabled={isSubmitting}>
                {isSubmitting ? "Enviando…" : "Enviar link"}
              </Button>
            </div>
            <Link href="/entrar" className="text-caption font-medium underline">
              Voltar para entrar
            </Link>
            <Aviso>O link vale 1 hora e só funciona uma vez. Você pode pedir até 3 links por hora.</Aviso>
          </form>
        </Passo>
      ) : (
        <Passo numero={<Icone de={Mail} />} titulo="Confira seu e-mail">
          <p className="text-body">
            Se este e-mail tiver acesso, enviamos o link para <span className="wl-mono">{enviadoPara}</span>.
          </p>
          <p className="text-caption text-ink-muted">Não achou? Olhe a caixa de spam. O link chega em poucos minutos e vale 1 hora.</p>
          <div className="grid md:flex">
            <Button
              variante="quieto"
              onClick={() => {
                void contas.esqueciSenha(enviadoPara);
              }}
            >
              Reenviar link
            </Button>
          </div>
          <Link href="/entrar" className="text-caption font-medium underline">
            Voltar para entrar
          </Link>
        </Passo>
      )}
    </PaginaAcesso>
  );
}
