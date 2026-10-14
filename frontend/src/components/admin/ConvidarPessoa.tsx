"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { usuarios, type Eu, type Perfil, type PermissaoExtra } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { mascaraCelular, soDigitos } from "@/lib/formatos";
import { PERFIS } from "@/lib/usuarios";
import { FiliaisDoAcesso, PermissoesExtras } from "./PermissoesExtras";

const CAMPOS = ["email", "nome", "celular", "perfil", "filiais", "permissoes_extras"];

/** Convite (USR-01): sai por e-mail e, com celular, também por WhatsApp. O limite do plano (PLT-03) é conferido pela API. */
export function ConvidarPessoa({ eu, aoFechar, aoConcluir }: { eu: Eu; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [celular, setCelular] = useState("");
  const [perfil, setPerfil] = useState<Perfil>("vendedor");
  const [filiais, setFiliais] = useState<number[]>(eu.filiais.length === 1 ? eu.filiais.map((f) => f.id) : []);
  const [extras, setExtras] = useState<PermissaoExtra[]>([]);
  const ehAdmin = perfil === "administrador";

  const convidar = useMutation({
    mutationFn: () =>
      usuarios.convidar({
        email: email.trim(),
        nome: nome.trim() || undefined,
        celular: soDigitos(celular) || undefined,
        perfil,
        filiais: ehAdmin ? undefined : filiais,
        permissoes_extras: extras,
      }),
    onSuccess: async (u) => {
      await cliente.invalidateQueries({ queryKey: ["usuarios"] });
      aoConcluir(`Convite enviado a ${u.email}. Ele vale por 7 dias.`);
      aoFechar();
    },
  });
  const completo = email.trim() !== "" && (ehAdmin || filiais.length > 0);
  const erroGeral = convidar.isError && !CAMPOS.some((c) => campoDoErro(convidar.error, c));

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Convidar pessoa"
      descricao="A pessoa recebe um link por e-mail, e por WhatsApp se você informar o celular, para criar a senha."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!completo || convidar.isPending} onClick={() => convidar.mutate()}>
            {convidar.isPending ? "Enviando…" : "Enviar convite"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField cheio data-autofocus type="email" rotulo="E-mail" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} erro={campoDoErro(convidar.error, "email")} dica="É o login da pessoa." />
        <TextField cheio rotulo="Nome (opcional)" value={nome} onChange={(e) => setNome(e.target.value)} erro={campoDoErro(convidar.error, "nome")} />
        <TextField cheio rotulo="Celular (opcional)" inputMode="tel" value={celular} onChange={(e) => setCelular(mascaraCelular(e.target.value))} erro={campoDoErro(convidar.error, "celular")} />
        <CampoSelecao rotulo="Perfil" value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)} opcoes={PERFIS} erro={campoDoErro(convidar.error, "perfil")} />
        {ehAdmin ? (
          <p className="text-caption text-ink-muted">Administrador tem acesso a todas as filiais.</p>
        ) : (
          <FiliaisDoAcesso opcoes={eu.filiais} marcadas={filiais} aoMudar={setFiliais} erro={campoDoErro(convidar.error, "filiais")} />
        )}
        {!ehAdmin && (
          <PermissoesExtras
            permissoes={(["aprovar_desconto", "cancelar_contrato", "relatorios_todas_filiais"] as const).map((chave) => ({ chave, marcada: extras.includes(chave), padrao_do_perfil: false }))}
            perfil={perfil}
            marcadas={extras}
            filiais={eu.filiais.filter((f) => filiais.includes(f.id)).map((f) => f.nome)}
            aoMudar={setExtras}
          />
        )}
        {erroGeral && (
          <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
            {mensagemDoErro(convidar.error)}
          </p>
        )}
      </div>
    </Dialogo>
  );
}
