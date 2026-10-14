"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { Button, Contador, Gaveta, Icone, StatusBadge } from "@/design-system";
import { Confirmacao } from "@/components/financeiro/Comuns";
import { Paginacao } from "@/components/lista/Paginacao";
import { usuarios, type SituacaoDeUsuarios, type UsuarioDaLista } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { mensagemDoErro } from "@/lib/erros";
import { useFiltrosNaUrl } from "@/lib/filtros-url";
import { dataCurta, iniciais } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { filiaisDoUsuario, ROTULO_DO_PERFIL, situacaoDoUsuario, TOM_DO_PERFIL, ultimoAcesso } from "@/lib/usuarios";
import { ConvidarPessoa } from "./ConvidarPessoa";
import { PainelDoUsuario } from "./PainelDoUsuario";

// Referência: docs/telas/html/Admin-Usuarios-Desktop.dc.html e Admin-Usuarios-Mobile.dc.html.
// Plano, contagens e situação vêm da API (USR-01 a USR-09, PLT-03); a tela não decide quem conta no plano.

type Aba = "todos" | SituacaoDeUsuarios;

const ABAS: { valor: Aba; rotulo: string; curto: string; chave: "todos" | "ativos" | "convites" | "desativados" }[] = [
  { valor: "todos", rotulo: "Todos", curto: "Todos", chave: "todos" },
  { valor: "ativos", rotulo: "Ativos", curto: "Ativos", chave: "ativos" },
  { valor: "convites", rotulo: "Convites pendentes", curto: "Pendentes", chave: "convites" },
  { valor: "desativados", rotulo: "Desativados", curto: "Desativados", chave: "desativados" },
];

const consultaDesktop = "(min-width: 768px)";
function useEhDesktop(): boolean {
  return useSyncExternalStore(
    (aviso) => {
      const m = window.matchMedia(consultaDesktop);
      m.addEventListener("change", aviso);
      return () => m.removeEventListener("change", aviso);
    },
    () => window.matchMedia(consultaDesktop).matches,
    () => true,
  );
}

function Chips({ abas, aba, contagens, aoMudar, curto }: { abas: typeof ABAS; aba: Aba; contagens?: Record<string, number>; aoMudar: (v: Aba) => void; curto?: boolean }) {
  return (
    <div role="group" aria-label="Situação" className="flex gap-2 overflow-x-auto pb-1">
      {abas.map((a) => {
        const ativo = a.valor === aba;
        return (
          <button
            key={a.valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => aoMudar(a.valor)}
            className={`inline-flex h-[44px] shrink-0 items-center gap-2 rounded-pill py-0 pr-[6px] pl-4 text-body whitespace-nowrap md:h-10 ${ativo ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
          >
            {curto ? a.curto : a.rotulo}
            {contagens && (
              <span className={ativo ? "[&_.wl-count]:!bg-brand [&_.wl-count]:!text-on-brand" : "[&_.wl-count]:!bg-surface"}>
                <Contador>{contagens[a.chave] ?? 0}</Contador>
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Avatar({ nome, tamanho = "p", apagado }: { nome: string; tamanho?: "p" | "g"; apagado?: boolean }) {
  return (
    <span aria-hidden="true" className={`grid shrink-0 place-items-center rounded-full bg-surface-sunken text-caption font-semibold ${tamanho === "g" ? "size-10" : "size-9"} ${apagado ? "text-ink-muted" : ""}`}>
      {iniciais(nome)}
    </span>
  );
}

/** Cartão do celular: pendente leva Reenviar e Cancelar logo abaixo; os demais abrem a edição. */
function CartaoDoUsuario({ u, agora, aoAbrir, aoReenviar, aoCancelar, ocupado }: { u: UsuarioDaLista; agora: Date; aoAbrir: (u: UsuarioDaLista) => void; aoReenviar: (u: UsuarioDaLista) => void; aoCancelar: (u: UsuarioDaLista) => void; ocupado: boolean }) {
  const pendente = u.status === "convite_pendente";
  const desativado = u.status === "desativado";
  const quando = pendente ? "convite enviado" : desativado ? (u.ultimo_acesso_em ? `desativado em ${dataCurta(u.ultimo_acesso_em)}` : "desativado") : ultimoAcesso(u.ultimo_acesso_em, agora);
  const linha = [ROTULO_DO_PERFIL[u.perfil], u.todas_filiais ? "todas as filiais" : filiaisDoUsuario(u), quando].filter(Boolean).join(" · ");
  return (
    <article className={`flex flex-col gap-2.5 rounded-lg bg-surface px-4 py-[14px] ${desativado ? "opacity-70" : ""}`}>
      <button type="button" onClick={() => aoAbrir(u)} className="flex min-h-[44px] items-center gap-3 text-left text-ink">
        <Avatar nome={u.nome} tamanho="g" apagado={desativado} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body font-medium">
            {u.nome}
            {u.eu ? " (você)" : ""}
          </span>
          <span className="block text-caption text-ink-muted">{linha}</span>
        </span>
        {pendente ? (
          <StatusBadge tom="info" compacto>
            Pendente
          </StatusBadge>
        ) : desativado ? (
          <StatusBadge compacto>Inativo</StatusBadge>
        ) : u.dois_fatores_ativo ? (
          <StatusBadge tom="sucesso" compacto>
            2FA
          </StatusBadge>
        ) : null}
      </button>
      {pendente && (
        <div className="grid grid-cols-2 gap-2">
          <Button compacto variante="quieto" disabled={ocupado} onClick={() => aoReenviar(u)}>
            Reenviar
          </Button>
          <Button compacto variante="quieto" disabled={ocupado} onClick={() => aoCancelar(u)}>
            Cancelar
          </Button>
        </div>
      )}
    </article>
  );
}

/** Administração › Usuários: plano, abas por situação, lista e o painel da pessoa escolhida. */
export function ListaUsuarios() {
  const { eu } = useSessao();
  const cliente = useQueryClient();
  const { valor, definir } = useFiltrosNaUrl();
  const aba = (valor("aba") ?? "todos") as Aba;
  const cursor = valor("cursor") ?? undefined;
  const agora = useAgora();
  const desktop = useEhDesktop();
  const [escolhido, setEscolhido] = useState<number | null>(null);
  const [convidando, setConvidando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const podeVer = eu.pode.administracao;
  const consulta = useQuery({
    queryKey: ["usuarios", { aba, cursor }],
    queryFn: () => usuarios.listar({ situacao: aba === "todos" ? undefined : aba, cursor }),
    placeholderData: (anterior) => anterior,
    enabled: podeVer,
  });
  const d = podeVer ? consulta.data : undefined;
  const gente = d?.resultados ?? [];
  const plano = d?.plano;

  const depois = (mensagem: string) => async () => {
    await Promise.all([cliente.invalidateQueries({ queryKey: ["usuarios"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
    setAviso(mensagem);
  };
  const reenviar = useMutation({ mutationFn: (u: UsuarioDaLista) => usuarios.reenviarConvite(u.id).then(() => u), onSuccess: (u) => depois(`Convite reenviado a ${u.email}. O link anterior deixou de valer.`)() });
  const cancelar = useMutation({ mutationFn: (u: UsuarioDaLista) => usuarios.cancelarConvite(u.id).then(() => u), onSuccess: (u) => depois(`Convite de ${u.email} cancelado.`)() });
  const ocupado = reenviar.isPending || cancelar.isPending;

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa Usuários.
      </p>
    );

  const textoDoPlano = plano ? (plano.limite === null ? `${plano.usado} no plano` : `${plano.usado} de ${plano.limite} no plano`) : null;
  const semVaga = plano?.bloqueado === true;
  const abrir = (u: UsuarioDaLista) => setEscolhido(u.id);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3 md:items-end">
        <Link href="/mais" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1 md:flex-none">
          <div className="text-caption text-ink-muted md:text-body">Administração</div>
          <h1 className="text-title md:mt-1.5 md:text-display">Usuários</h1>
        </div>
        {textoDoPlano && (
          <span className="wl-badge hidden bg-surface md:ml-auto md:inline-flex" style={{ background: "var(--surface)" }}>
            {textoDoPlano}
          </span>
        )}
        <span className="md:hidden">
          <button type="button" aria-label="Convidar pessoa" disabled={semVaga} onClick={() => setConvidando(true)} className="wl-icon-btn size-11 bg-solid text-on-solid">
            <Icone de={Plus} />
          </button>
        </span>
        <span className="hidden md:inline">
          <Button variante="solido" disabled={semVaga} onClick={() => setConvidando(true)}>
            Convidar pessoa
          </Button>
        </span>
      </header>

      {plano && (
        <div className="flex items-center gap-2.5 rounded-lg bg-surface-sunken px-4 py-3 text-caption text-ink-muted md:hidden">
          <span className="flex-1">Usuários do plano</span>
          <StatusBadge tom="superficie" compacto>
            {plano.limite === null ? String(plano.usado) : `${plano.usado} de ${plano.limite}`}
          </StatusBadge>
        </div>
      )}
      {semVaga && (
        <p role="note" className="rounded-md bg-warning-soft p-4 text-caption text-warning-ink">
          O plano chegou ao limite de usuários. Desative alguém ou mude de plano para convidar mais gente.
        </p>
      )}
      {plano?.aviso && !semVaga && (
        <p role="note" className="rounded-md bg-surface-sunken p-4 text-caption text-ink-muted">
          O plano está perto do limite de usuários.
        </p>
      )}

      {aviso && <Confirmacao>{aviso}</Confirmacao>}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <section className="md:wl-panel flex min-w-0 flex-col gap-3 md:flex-[999_1_560px] md:gap-0" aria-label="Pessoas da empresa">
          <div className="md:mb-5">
            <div className="hidden md:block">
              <Chips abas={ABAS} aba={aba} contagens={d?.contagens} aoMudar={(v) => definir({ aba: v === "todos" ? null : v })} />
            </div>
            <div className="md:hidden">
              <Chips abas={ABAS} aba={aba} contagens={d?.contagens} aoMudar={(v) => definir({ aba: v === "todos" ? null : v })} curto />
            </div>
          </div>

          {consulta.isError && (
            <p role="alert" className="text-body">
              {mensagemDoErro(consulta.error)}
            </p>
          )}
          {consulta.isPending && (
            <p className="text-body text-ink-muted" aria-busy="true">
              Carregando as pessoas…
            </p>
          )}
          {(reenviar.isError || cancelar.isError) && (
            <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
              {mensagemDoErro(reenviar.error ?? cancelar.error)}
            </p>
          )}
          {d && gente.length === 0 && <p className="py-6 text-center text-body text-ink-muted">Ninguém nesta situação.</p>}

          {d && gente.length > 0 && (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="wl-table min-w-[720px]" aria-label="Pessoas da empresa">
                  <thead>
                    <tr>
                      <th scope="col">Pessoa</th>
                      <th scope="col">Perfil</th>
                      <th scope="col">Filial</th>
                      <th scope="col">Último acesso</th>
                      <th scope="col">Situação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gente.map((u) => {
                      const s = situacaoDoUsuario(u);
                      const selecionado = escolhido === u.id;
                      return (
                        <tr
                          key={u.id}
                          data-clicavel=""
                          tabIndex={0}
                          aria-selected={selecionado}
                          className={selecionado ? "[&>td]:!bg-brand-soft" : undefined}
                          onClick={() => abrir(u)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              abrir(u);
                            }
                          }}
                        >
                          <td>
                            <div className="flex items-center gap-3">
                              <Avatar nome={u.nome} apagado={u.status === "desativado"} />
                              <div>
                                <span className={`wl-cell-main ${u.status === "desativado" ? "text-ink-muted" : ""}`}>
                                  {u.nome}
                                  {u.eu ? " (você)" : ""}
                                </span>
                                <span className="wl-cell-sub">{u.email}</span>
                              </div>
                            </div>
                          </td>
                          <td>
                            <StatusBadge tom={TOM_DO_PERFIL[u.perfil]} compacto>
                              {ROTULO_DO_PERFIL[u.perfil]}
                            </StatusBadge>
                          </td>
                          <td>{filiaisDoUsuario(u)}</td>
                          <td>{u.eu ? "agora" : ultimoAcesso(u.ultimo_acesso_em, agora)}</td>
                          <td>
                            <span className="inline-flex flex-wrap items-center gap-2">
                              <StatusBadge tom={s.tom} compacto>
                                {s.rotulo}
                              </StatusBadge>
                              {u.status === "convite_pendente" && (
                                <button
                                  type="button"
                                  disabled={ocupado}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    reenviar.mutate(u);
                                  }}
                                  className="wl-btn wl-btn--quiet wl-btn--sm"
                                >
                                  Reenviar
                                </button>
                              )}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-3 md:hidden">
                {gente.map((u) => (
                  <CartaoDoUsuario key={u.id} u={u} agora={agora} aoAbrir={abrir} aoReenviar={(x) => reenviar.mutate(x)} aoCancelar={(x) => cancelar.mutate(x)} ocupado={ocupado} />
                ))}
              </div>
              <Paginacao texto={`Mostrando ${gente.length}`} anterior={d.anterior} proximo={d.proximo} aoIr={(cur) => definir({ cursor: cur })} />
            </>
          )}
        </section>

        {desktop && escolhido !== null && (
          <aside className="wl-panel flex min-w-0 flex-col gap-4 md:flex-[1_1_320px]" aria-label="Pessoa escolhida">
            <PainelDoUsuario id={escolhido} eu={eu} aoConcluir={setAviso} />
          </aside>
        )}
        {desktop && escolhido === null && gente.length > 0 && (
          <aside className="wl-panel min-w-0 md:flex-[1_1_320px]" aria-label="Pessoa escolhida">
            <p className="text-body text-ink-muted">Escolha uma pessoa na lista para mudar perfil, filiais e permissões.</p>
          </aside>
        )}
      </div>

      {!desktop && escolhido !== null && (
        <Gaveta aberto aoFechar={() => setEscolhido(null)} titulo="Pessoa" lado="baixo">
          <PainelDoUsuario
            id={escolhido}
            eu={eu}
            aoConcluir={(m) => {
              setAviso(m);
              setEscolhido(null);
            }}
          />
        </Gaveta>
      )}
      {convidando && <ConvidarPessoa eu={eu} aoFechar={() => setConvidando(false)} aoConcluir={setAviso} />}
    </div>
  );
}
