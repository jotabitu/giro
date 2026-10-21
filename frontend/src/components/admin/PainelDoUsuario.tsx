"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { usuarios, type Eu, type LinkDoConvite, type Perfil, type PermissaoExtra, type UsuarioDetalhado } from "@/lib/api";
import { copiarQuandoChegar } from "@/lib/area-de-transferencia";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCurta, dataHoraCurta, iniciais } from "@/lib/formatos";
import { PERFIS } from "@/lib/usuarios";
import { FiliaisDoAcesso, PermissoesExtras } from "./PermissoesExtras";

type Confirmacao = "desativar" | "redefinir" | null;

const igual = <T,>(a: T[], b: T[]) => a.length === b.length && a.every((x) => b.includes(x));

function Edicao({ u, eu, aoConcluir }: { u: UsuarioDetalhado; eu: Eu; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const marcadasAntes = u.permissoes_extras.filter((p) => p.marcada && !p.padrao_do_perfil).map((p) => p.chave);
  const [perfil, setPerfil] = useState<Perfil>(u.perfil);
  const [filiais, setFiliais] = useState<number[]>(u.filiais.map((f) => f.id));
  const [extras, setExtras] = useState<PermissaoExtra[]>(marcadasAntes);
  const [confirmar, setConfirmar] = useState<Confirmacao>(null);
  const [motivo, setMotivo] = useState("");

  const depois = async (mensagem: string) => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["usuarios"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
    setConfirmar(null);
    setMotivo("");
    aoConcluir(mensagem);
  };

  const salvar = useMutation({
    mutationFn: () => usuarios.alterar(u.id, { perfil, filiais: perfil === "administrador" ? undefined : filiais, permissoes_extras: extras }),
    onSuccess: () => depois(`Alterações de ${u.nome} salvas.`),
  });
  const desativar = useMutation({ mutationFn: () => usuarios.desativar(u.id, motivo.trim() || undefined), onSuccess: () => depois(`${u.nome} não tem mais acesso. O histórico continua guardado.`) });
  const reativar = useMutation({
    mutationFn: () => usuarios.reativar(u.id),
    onSuccess: (r) => depois(r.status === "convite_pendente" ? `Novo convite enviado a ${u.email}.` : `${u.nome} voltou a ter acesso.`),
  });
  const redefinir = useMutation({ mutationFn: () => usuarios.redefinir2fa(u.id, motivo.trim()), onSuccess: () => depois(`A verificação em 2 etapas de ${u.nome} foi apagada. No próximo acesso ela configura de novo.`) });
  const reenviar = useMutation({ mutationFn: () => usuarios.reenviarConvite(u.id), onSuccess: () => depois(`Convite reenviado a ${u.email}. O link anterior deixou de valer.`) });
  // O link só existe aqui dentro: vai direto para a área de transferência e não fica em estado nem em cache (USR-01).
  // A cópia começa no clique, antes da resposta: o Safari recusa gravar depois de esperar a rede (T-252).
  const copiarLink = useMutation({
    mutationFn: async ({ pedido, copia }: { pedido: Promise<LinkDoConvite>; copia: Promise<void> }) => {
      const r = await pedido;
      try {
        await copia;
      } catch {
        throw new Error("Não deu para copiar o link. Toque em Copiar link do convite de novo.");
      }
      return r.aviso;
    },
    onSuccess: (aviso) => depois(`Link do convite de ${u.nome} copiado. ${aviso}`),
  });
  const aoCopiarLink = () => {
    const pedido = usuarios.copiarLinkDoConvite(u.id);
    const copia = copiarQuandoChegar(pedido.then((r) => r.link));
    copia.catch(() => undefined); // se a API falhar, o erro que vale é o dela, lido em `pedido`
    copiarLink.mutate({ pedido, copia });
  };
  const cancelar = useMutation({ mutationFn: () => usuarios.cancelarConvite(u.id), onSuccess: () => depois(`Convite de ${u.email} cancelado.`) });

  const ativo = u.status === "ativo";
  const pendente = u.status === "convite_pendente";
  const sessoes = useQuery({ queryKey: ["usuarios", "sessoes", u.id], queryFn: () => usuarios.sessoes(u.id), enabled: ativo });
  const encerrar = useMutation({ mutationFn: (sid: number) => usuarios.encerrarSessao(u.id, sid), onSuccess: () => cliente.invalidateQueries({ queryKey: ["usuarios", "sessoes", u.id] }) });

  const editavel = ativo || pendente;
  const mudou =
    perfil !== u.perfil ||
    !igual(
      filiais,
      u.filiais.map((f) => f.id),
    ) ||
    !igual(extras, marcadasAntes);
  const ocupado = [salvar, desativar, reativar, redefinir, reenviar, copiarLink, cancelar].some((m) => m.isPending);
  const erroDaAcao = [desativar, reativar, redefinir, reenviar, copiarLink, cancelar].find((m) => m.isError)?.error;
  const nomesDasFiliais = eu.filiais.filter((f) => filiais.includes(f.id)).map((f) => f.nome);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="grid size-12 shrink-0 place-items-center rounded-full bg-surface-sunken text-body font-semibold" aria-hidden="true">
          {iniciais(u.nome)}
        </div>
        <div className="min-w-0">
          <div className="text-heading font-semibold">{u.nome}</div>
          <div className="text-caption text-ink-muted">
            {u.email}
            {u.entrou_em ? ` · Entrou em ${dataCurta(u.entrou_em)}` : pendente ? " · Convite pendente" : ""}
            {ativo && u.dois_fatores_ativo ? " · 2FA ativa" : ""}
          </div>
        </div>
      </div>

      {editavel && (
        <>
          <CampoSelecao rotulo="Perfil" value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)} opcoes={PERFIS} erro={campoDoErro(salvar.error, "perfil")} />
          {perfil === "administrador" ? (
            <p className="text-caption text-ink-muted">Administrador tem acesso a todas as filiais.</p>
          ) : (
            <FiliaisDoAcesso opcoes={eu.filiais} marcadas={filiais} aoMudar={setFiliais} erro={campoDoErro(salvar.error, "filiais")} />
          )}
          <PermissoesExtras permissoes={u.permissoes_extras} perfil={perfil} marcadas={extras} filiais={nomesDasFiliais} aoMudar={setExtras} />
          {salvar.isError && !["perfil", "filiais"].some((c) => campoDoErro(salvar.error, c)) && (
            <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
              {mensagemDoErro(salvar.error)}
            </p>
          )}
          <Button variante="solido" disabled={!mudou || ocupado || (perfil !== "administrador" && filiais.length === 0)} onClick={() => salvar.mutate()}>
            <span className="mx-auto">{salvar.isPending ? "Salvando…" : "Salvar alterações"}</span>
          </Button>
        </>
      )}

      {pendente && (
        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2">
            {u.acoes.reenviar_convite && (
              <Button compacto variante="quieto" disabled={ocupado} onClick={() => reenviar.mutate()}>
                Reenviar convite
              </Button>
            )}
            {u.acoes.cancelar_convite && (
              <Button compacto variante="quieto" disabled={ocupado} onClick={() => cancelar.mutate()}>
                Cancelar convite
              </Button>
            )}
          </div>
          {u.acoes.copiar_link_convite && (
            <>
              <Button compacto variante="quieto" disabled={ocupado} onClick={aoCopiarLink}>
                {copiarLink.isPending ? "Copiando…" : "Copiar link do convite"}
              </Button>
              <p className="text-caption leading-[18px] text-ink-muted">Gera um link novo, sem enviar e-mail. O link anterior deixa de valer.</p>
            </>
          )}
        </div>
      )}

      {u.status === "desativado" && (
        <>
          <p className="text-caption text-ink-muted">Sem acesso. O histórico do que a pessoa fez continua guardado. Quem nunca chegou a entrar recebe um convite novo ao voltar.</p>
          <Button variante="solido" disabled={ocupado} onClick={() => reativar.mutate()}>
            <span className="mx-auto">{reativar.isPending ? "Reativando…" : "Reativar acesso"}</span>
          </Button>
        </>
      )}

      {ativo && (
        <section aria-label="Sessões" className="flex flex-col gap-2 border-t border-line pt-4">
          <h3 className="text-body font-medium">Sessões abertas</h3>
          {sessoes.isPending && <p className="text-caption text-ink-muted">Carregando as sessões…</p>}
          {sessoes.data?.length === 0 && <p className="text-caption text-ink-muted">Nenhuma sessão aberta.</p>}
          {sessoes.data?.map((s) => (
            <div key={s.id} className="flex items-center gap-3">
              <span className="min-w-0 flex-1 text-caption">
                {s.aparelho}
                <span className="block text-ink-muted">Último uso {dataHoraCurta(s.ultimo_uso)}</span>
              </span>
              <Button compacto variante="quieto" disabled={encerrar.isPending} onClick={() => encerrar.mutate(s.id)}>
                Encerrar
              </Button>
            </div>
          ))}
          {u.dois_fatores_ativo && !u.eu && (
            <div>
              <Button compacto variante="quieto" disabled={ocupado} onClick={() => setConfirmar("redefinir")}>
                Redefinir 2 etapas
              </Button>
            </div>
          )}
        </section>
      )}

      {confirmar && (
        <div className="flex flex-col gap-3 rounded-md bg-surface-sunken p-4">
          <TextField
            cheio
            data-autofocus
            rotulo={confirmar === "desativar" ? "Motivo (opcional)" : "Motivo da redefinição"}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            erro={campoDoErro(redefinir.error, "motivo")}
            dica={confirmar === "redefinir" ? "Apaga o autenticador e os códigos de recuperação e encerra as sessões da pessoa." : undefined}
          />
          <div className="grid grid-cols-2 gap-2">
            <Button
              compacto
              variante="quieto"
              onClick={() => {
                setConfirmar(null);
                setMotivo("");
              }}
            >
              Voltar
            </Button>
            <Button compacto variante="solido" disabled={ocupado || (confirmar === "redefinir" && motivo.trim() === "")} onClick={() => (confirmar === "desativar" ? desativar.mutate() : redefinir.mutate())}>
              {confirmar === "desativar" ? "Desativar" : "Redefinir"}
            </Button>
          </div>
        </div>
      )}

      {erroDaAcao != null && (
        <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
          {mensagemDoErro(erroDaAcao)}
        </p>
      )}

      {ativo && !u.eu && !confirmar && (
        <div className="border-t border-line pt-[14px]">
          <button type="button" disabled={ocupado} onClick={() => setConfirmar("desativar")} className="wl-btn wl-btn--sm bg-critical-soft text-critical-ink">
            Desativar acesso
          </button>
          <p className="mt-2 text-caption leading-[18px] text-ink-muted">A pessoa sai do sistema na hora. O histórico do que fez continua guardado.</p>
        </div>
      )}
    </div>
  );
}

/** Painel da pessoa escolhida: perfil, filiais, permissões extras e as ações do estado dela (docs/api/contas.md). */
export function PainelDoUsuario({ id, eu, aoConcluir }: { id: number; eu: Eu; aoConcluir: (mensagem: string) => void }) {
  const consulta = useQuery({ queryKey: ["usuarios", "detalhe", id], queryFn: () => usuarios.obter(id) });
  if (consulta.isPending)
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando a pessoa…
      </p>
    );
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  // Troca de pessoa ou dados novos da API recomeçam o formulário.
  return <Edicao key={`${consulta.data.id}-${consulta.dataUpdatedAt}`} u={consulta.data} eu={eu} aoConcluir={aoConcluir} />;
}
