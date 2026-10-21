"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type ReactNode } from "react";
import { Button, Icone, ProgressBar, SegmentedControl, StatusBadge, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { filiais, type FilialDetalhada } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { corpoDaFilial, filialCompleta, horarioPedeCuidado, mascaraTelefone, resumoDaLinha, UFS, valoresDaFilial, VALORES_INICIAIS_DA_FILIAL, type LinhaDeHorario, type ValoresDaFilial } from "@/lib/filiais";
import { mascaraCep, mascaraCnpj, soDigitos } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { FeriadosDaFilial } from "./FeriadosDaFilial";

// Referência: docs/telas/html/Filial-Desktop.dc.html e Filial-Mobile.dc.html (nova filial; a edição usa a mesma tela).

function Secao({ titulo, texto, children }: { titulo: string; texto?: string; children: ReactNode }) {
  return (
    <section className="wl-panel flex flex-col gap-4">
      <div>
        <h2 className="text-heading">{titulo}</h2>
        {texto && <p className="mt-1 mb-0 text-caption text-ink-muted">{texto}</p>}
      </div>
      {children}
    </section>
  );
}

const GRADE = "grid grid-cols-1 gap-x-5 gap-y-4 md:grid-cols-[repeat(auto-fit,minmax(220px,1fr))]";

const DIAS = [
  { chave: "semana", rotulo: "Segunda a sexta" },
  { chave: "sab", rotulo: "Sábado" },
  { chave: "dom", rotulo: "Domingo" },
] as const;

function Horarios({ valores, aoMudar, aviso, erro }: { valores: ValoresDaFilial["horario"]; aoMudar: (h: ValoresDaFilial["horario"]) => void; aviso: boolean; erro?: string }) {
  const [editando, setEditando] = useState(false);
  const mudar = (chave: (typeof DIAS)[number]["chave"], parte: Partial<LinhaDeHorario>) => {
    const proximo = { ...valores[chave], ...parte };
    if (!proximo.segundo) delete proximo.segundo;
    aoMudar({ ...valores, [chave]: proximo });
  };
  return (
    <div>
      <div className={editando ? "" : "hidden md:block"}>
        <div className="hidden grid-cols-[140px_1fr_1fr_auto] gap-3 pb-2 text-caption text-ink-muted md:grid">
          <span>Dias</span>
          <span>Abre</span>
          <span>Fecha</span>
          <span />
        </div>
        {DIAS.map((d) => {
          const l = valores[d.chave];
          return (
            <div key={d.chave}>
              <div className="grid grid-cols-[1fr_1fr] items-center gap-3 border-b border-line py-2.5 md:grid-cols-[140px_1fr_1fr_auto]">
                <span className="col-span-2 text-body md:col-span-1">{d.rotulo}</span>
                <input aria-label={`${d.rotulo}: abre`} type="time" className="wl-input wl-mono" value={l.fechado ? "" : l.abre} disabled={l.fechado} onChange={(e) => mudar(d.chave, { abre: e.target.value })} />
                <input aria-label={`${d.rotulo}: fecha`} type="time" className="wl-input wl-mono" value={l.fechado ? "" : l.fecha} disabled={l.fechado} onChange={(e) => mudar(d.chave, { fecha: e.target.value })} />
                <div className="col-span-2 flex min-h-[44px] flex-wrap items-center gap-3 md:col-span-1">
                  <label className="flex items-center gap-2 text-body">
                    <input type="checkbox" checked={l.fechado} onChange={(e) => mudar(d.chave, { fechado: e.target.checked, segundo: undefined })} className="size-5 accent-[var(--solid)]" />
                    Fechado
                  </label>
                  {!l.fechado && !l.segundo && (
                    <button
                      type="button"
                      onClick={() => mudar(d.chave, { fecha: l.fecha === "18:00" ? "12:00" : l.fecha, segundo: { abre: "14:00", fecha: "18:00" } })}
                      className="wl-btn wl-btn--quiet wl-btn--sm"
                    >
                      2º intervalo
                    </button>
                  )}
                </div>
              </div>
              {!l.fechado && l.segundo && (
                <div className="grid grid-cols-[1fr_1fr] items-center gap-3 border-b border-line py-2.5 md:grid-cols-[140px_1fr_1fr_auto]">
                  <span className="col-span-2 text-caption text-ink-muted md:col-span-1">2º intervalo</span>
                  <input aria-label={`${d.rotulo}: 2º intervalo abre`} type="time" className="wl-input wl-mono" value={l.segundo.abre} onChange={(e) => mudar(d.chave, { segundo: { ...l.segundo!, abre: e.target.value } })} />
                  <input aria-label={`${d.rotulo}: 2º intervalo fecha`} type="time" className="wl-input wl-mono" value={l.segundo.fecha} onChange={(e) => mudar(d.chave, { segundo: { ...l.segundo!, fecha: e.target.value } })} />
                  <button type="button" onClick={() => mudar(d.chave, { segundo: undefined })} className="wl-btn wl-btn--quiet wl-btn--sm col-span-2 justify-self-start md:col-span-1">
                    Remover
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className={editando ? "hidden" : "md:hidden"}>
        {DIAS.map((d) => {
          const l = valores[d.chave];
          return (
            <div key={d.chave} className="flex min-h-12 items-center justify-between border-b border-line text-body last:border-b-0">
              <span>{d.rotulo}</span>
              <span className={l.fechado ? "text-ink-muted" : "wl-mono"}>{resumoDaLinha(l)}</span>
            </div>
          );
        })}
        <div className="pt-3">
          <Button compacto variante="quieto" onClick={() => setEditando(true)}>
            Editar horários
          </Button>
        </div>
      </div>
      <p className="mt-2 mb-0 text-caption text-ink-muted">Cada dia aceita até 2 intervalos, para quem fecha no almoço.</p>
      {aviso && <p className="mt-2 mb-0 text-caption text-ink-muted">Esta filial tem horários diferentes durante a semana. Se você editar aqui, de segunda a sexta fica igual.</p>}
      {erro && (
        <p role="alert" className="mt-2 mb-0 text-caption text-critical-ink">
          {erro}
        </p>
      )}
    </div>
  );
}

function Formulario({ filial }: { filial?: FilialDetalhada }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const { eu } = useSessao();
  const [v, setV] = useState<ValoresDaFilial>(filial ? valoresDaFilial(filial) : VALORES_INICIAIS_DA_FILIAL);
  const [horarioMudou, setHorarioMudou] = useState(false);
  const [cepAviso, setCepAviso] = useState<string | null>(null);
  const ultimoCep = useRef("");
  const lista = useQuery({ queryKey: ["filiais-admin", "lista"], queryFn: () => filiais.listar(), enabled: eu.pode.administracao });
  const plano = lista.data?.plano;

  const definir = <K extends keyof ValoresDaFilial>(campo: K, valor: ValoresDaFilial[K]) => setV((x) => ({ ...x, [campo]: valor }));

  async function buscarCep(texto: string) {
    const cep = soDigitos(texto);
    if (cep.length !== 8 || cep === ultimoCep.current) return;
    ultimoCep.current = cep;
    try {
      const r = await filiais.cep(cep);
      setCepAviso(null);
      setV((x) => ({ ...x, logradouro: r.logradouro, bairro: r.bairro, cidade: r.cidade, uf: r.uf }));
    } catch {
      setCepAviso("Não achamos esse CEP. Preencha o endereço à mão.");
    }
  }

  const salvar = useMutation({
    mutationFn: () => {
      const corpo = corpoDaFilial(v);
      if (!filial) return filiais.criar(corpo);
      // A matriz muda por "Tornar matriz"; o horário só vai quando foi editado (a tela edita um intervalo por dia).
      const alteracao: Partial<typeof corpo> = { ...corpo };
      delete alteracao.matriz;
      if (!horarioMudou) delete alteracao.horario;
      return filiais.alterar(filial.id, alteracao);
    },
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["filiais-admin"] }), cliente.invalidateQueries({ queryKey: ["filiais-minhas"] })]);
      router.push(`/admin/filiais?ok=${filial ? "salva" : "criada"}`);
    },
  });
  const erro = (campo: string) => campoDoErro(salvar.error, campo);
  const camposComErro = ["nome", "nome_curto", "cnpj", "inscricao_estadual", "inscricao_municipal", "endereco", "contato", "preco_litro_centavos", "horario"];
  const erroGeral = salvar.isError && !camposComErro.some((c) => erro(c));
  const bloqueadaPeloPlano = !filial && plano?.bloqueado === true;
  const pode = filialCompleta(v) && !salvar.isPending && !bloqueadaPeloPlano;
  const titulo = filial ? filial.nome : "Nova filial";
  const nomeNoAside = filial ? null : v.nome.trim() || "Nova filial";

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (pode) salvar.mutate();
      }}
    >
      <header className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <Link href="/admin/filiais" aria-label="Voltar" className="wl-icon-btn size-11 md:hidden">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-caption text-ink-muted md:text-body">
            <span className="md:hidden">Administração · Filiais</span>
            <span className="hidden md:inline">
              Administração / <Link href="/admin/filiais" className="underline">Filiais</Link> / {filial ? filial.nome : "Nova"}
            </span>
          </div>
          <h1 className="text-title md:mt-1.5 md:text-display">{titulo}</h1>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/admin/filiais" className="wl-btn">
            Cancelar
          </Link>
          <Button type="submit" variante="solido" disabled={!pode}>
            {salvar.isPending ? "Salvando…" : "Salvar filial"}
          </Button>
        </div>
      </header>

      {plano && !filial && (
        <div className="flex items-center gap-2.5 rounded-lg bg-surface-sunken px-4 py-3 text-caption text-ink-muted md:hidden">
          <span className="flex-1">
            Plano {plano.nome_plano}: você usa {plano.usado}
            {plano.limite !== null ? ` das ${plano.limite} filiais incluídas` : " filiais"}.
          </span>
          <StatusBadge tom="solido" compacto>
            {plano.limite === null ? String(plano.usado) : `${plano.usado} de ${plano.limite}`}
          </StatusBadge>
        </div>
      )}
      {bloqueadaPeloPlano && (
        <p role="note" className="rounded-md bg-warning-soft p-4 text-caption text-warning-ink">
          O plano chegou ao limite de filiais. <Link href="/admin/assinatura" className="underline">Mude de plano</Link> para abrir outra.
        </p>
      )}
      {erroGeral && (
        <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
          {mensagemDoErro(salvar.error)}
        </p>
      )}

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <div className="flex min-w-0 flex-col gap-6 md:flex-[999_1_560px]">
          <Secao titulo="Identificação" texto="Como a filial aparece no seletor, nos contratos e nos recibos.">
            <div className={GRADE}>
              <TextField cheio rotulo="Nome da filial" value={v.nome} onChange={(e) => definir("nome", e.target.value)} erro={erro("nome")} />
              <TextField
                cheio
                rotulo="Nome curto no seletor"
                placeholder="Ex.: Messejana"
                maxLength={30}
                value={v.nomeCurto}
                onChange={(e) => definir("nomeCurto", e.target.value)}
                erro={erro("nome_curto")}
                dica="Até 30 caracteres. Aparece no seletor do topo."
              />
              <div className="wl-field">
                <span className="wl-field__label">Tipo</span>
                {filial ? (
                  <div>
                    <StatusBadge tom={filial.matriz ? "solido" : "neutro"}>{filial.matriz ? "Matriz" : "Filial"}</StatusBadge>
                  </div>
                ) : (
                  <SegmentedControl rotulo="Tipo de unidade" opcoes={[{ valor: "matriz", rotulo: "Matriz" }, { valor: "filial", rotulo: "Filial" }]} valor={v.matriz ? "matriz" : "filial"} aoMudar={(x) => definir("matriz", x === "matriz")} />
                )}
              </div>
              <TextField cheio mono rotulo="CNPJ" inputMode="numeric" value={mascaraCnpj(v.cnpj)} onChange={(e) => definir("cnpj", e.target.value)} erro={erro("cnpj")} dica={filial ? undefined : "Mesma raiz da matriz"} />
              <TextField cheio mono rotulo="Inscrição estadual" placeholder="Opcional" value={v.inscricaoEstadual} onChange={(e) => definir("inscricaoEstadual", e.target.value)} erro={erro("inscricao_estadual")} />
              <TextField cheio mono rotulo="Inscrição municipal" placeholder="Opcional" value={v.inscricaoMunicipal} onChange={(e) => definir("inscricaoMunicipal", e.target.value)} erro={erro("inscricao_municipal")} />
            </div>
          </Secao>

          <Secao titulo="Endereço" texto="Ao digitar o CEP, rua, bairro e cidade são preenchidos sozinhos.">
            <div className={GRADE}>
              <TextField
                cheio
                mono
                rotulo="CEP"
                inputMode="numeric"
                value={mascaraCep(v.cep)}
                onChange={(e) => {
                  definir("cep", e.target.value);
                  void buscarCep(e.target.value);
                }}
                erro={cepAviso ?? undefined}
              />
              <TextField cheio rotulo="Rua" value={v.logradouro} onChange={(e) => definir("logradouro", e.target.value)} />
              <TextField cheio rotulo="Número" value={v.numero} onChange={(e) => definir("numero", e.target.value)} />
              <TextField cheio rotulo="Complemento" placeholder="Loja, galpão, sala" value={v.complemento} onChange={(e) => definir("complemento", e.target.value)} />
              <TextField cheio rotulo="Bairro" value={v.bairro} onChange={(e) => definir("bairro", e.target.value)} />
              <TextField cheio rotulo="Cidade" value={v.cidade} onChange={(e) => definir("cidade", e.target.value)} />
              <CampoSelecao rotulo="UF" value={v.uf} onChange={(e) => definir("uf", e.target.value)} opcoes={UFS.map((u) => ({ valor: u, rotulo: u }))} />
            </div>
            {erro("endereco") && (
              <p role="alert" className="m-0 text-caption text-critical-ink">
                {erro("endereco")}
              </p>
            )}
          </Secao>

          <Secao titulo="Contato e funcionamento" texto="Usados nos lembretes ao cliente e para calcular atraso na devolução fora do horário.">
            <div className={GRADE}>
              <TextField cheio rotulo="Telefone" inputMode="tel" value={mascaraTelefone(v.telefone)} onChange={(e) => definir("telefone", e.target.value)} />
              <TextField cheio rotulo="WhatsApp de atendimento" inputMode="tel" value={mascaraTelefone(v.whatsapp)} onChange={(e) => definir("whatsapp", e.target.value)} />
              <TextField cheio rotulo="E-mail" type="email" inputMode="email" value={v.email} onChange={(e) => definir("email", e.target.value)} />
            </div>
            {erro("contato") && (
              <p role="alert" className="m-0 text-caption text-critical-ink">
                {erro("contato")}
              </p>
            )}
            <Horarios
              valores={v.horario}
              aoMudar={(h) => {
                setHorarioMudou(true);
                definir("horario", h);
              }}
              aviso={!!filial && !horarioMudou && horarioPedeCuidado(filial.horario)}
              erro={erro("horario")}
            />
            {filial ? (
              <FeriadosDaFilial filialId={filial.id} anoSeguintePendente={filial.feriados_ano_seguinte_pendentes} />
            ) : (
              <p className="m-0 border-t border-line pt-4 text-caption text-ink-muted">Feriados: depois de salvar a filial, o sistema sugere os nacionais do ano e você confirma ou acrescenta os locais.</p>
            )}
          </Secao>

          <Secao titulo="Operação" texto="Quem responde pela filial e o combustível da devolução. O recebimento é da empresa; o preço pode ser da empresa ou da filial.">
            <div className={GRADE}>
              <div className="wl-field wl-field--cheio">
                <label className="wl-field__label" htmlFor="gerente-da-filial">
                  Gerente responsável
                </label>
                <input id="gerente-da-filial" className="wl-input" disabled value={filial?.gerentes.length ? filial.gerentes.map((g) => g.nome).join(", ") : "Nenhum gerente ligado ainda"} readOnly />
                <span className="wl-field__hint">Quem gerencia é quem tem perfil gerente nesta filial, em Usuários.</span>
              </div>
              {eu.pode.administracao && (
                <TextField
                  cheio
                  mono
                  rotulo="Preço do litro do combustível"
                  placeholder="R$ 0,00"
                  inputMode="decimal"
                  value={v.precoLitro}
                  onChange={(e) => definir("precoLitro", e.target.value)}
                  erro={erro("preco_litro_centavos")}
                  dica="Usado no acerto de combustível da devolução. Sem preço, o acerto pede o valor à mão. Só o administrador altera."
                />
              )}
            </div>
          </Secao>

          <div className="grid grid-cols-2 gap-2 md:hidden">
            <Link href="/admin/filiais" className="wl-btn justify-center">
              Cancelar
            </Link>
            <Button type="submit" variante="solido" disabled={!pode}>
              <span className="mx-auto">{salvar.isPending ? "Salvando…" : "Salvar filial"}</span>
            </Button>
          </div>
        </div>

        <aside className="hidden min-w-0 flex-col gap-6 md:flex md:flex-[1_1_320px]">
          <Secao titulo="Filiais da empresa">
            <div>
              {lista.data?.resultados.map((f) => (
                <div key={f.id} className="flex items-center gap-3 border-b border-line py-3 last:border-b-0">
                  <span className="grid size-10 shrink-0 place-items-center rounded-md bg-surface-sunken" aria-hidden="true">
                    <Icone de={Building2} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-body font-medium">{f.nome}</div>
                    <div className="text-caption text-ink-muted">
                      {f.endereco.cidade}
                      {f.indicadores.veiculos !== null ? ` · ${f.indicadores.veiculos} veículos` : ""}
                    </div>
                  </div>
                  {f.matriz && (
                    <StatusBadge tom="solido" compacto>
                      Matriz
                    </StatusBadge>
                  )}
                </div>
              ))}
              {nomeNoAside && (
                <div className="flex items-center gap-3 py-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-md bg-surface-sunken" aria-hidden="true">
                    <Icone de={Building2} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-body font-medium">{nomeNoAside}</div>
                    <div className="text-caption text-ink-muted">nova</div>
                  </div>
                </div>
              )}
            </div>
          </Secao>

          {plano && (
            <section className="wl-panel flex flex-col gap-2" aria-label="Plano">
              <div className="flex justify-between text-body">
                <span className="font-medium">Plano {plano.nome_plano}</span>
                <span className="text-ink-muted">{plano.limite === null ? `${plano.usado} filiais` : `${plano.usado} de ${plano.limite} filiais`}</span>
              </div>
              {plano.limite !== null && <ProgressBar valor={(plano.usado / plano.limite) * 100} rotulo="Filiais do plano em uso" />}
              {!filial && plano.limite !== null && (
                <p className="m-0 text-caption text-ink-muted">
                  Ao salvar, são {plano.usado + 1} de {plano.limite} filiais.
                  {plano.usado + 1 >= plano.limite ? " Para abrir outra, mude de plano." : ""}
                </p>
              )}
            </section>
          )}

          <Secao titulo="O que é de cada filial">
            <div className="flex flex-col gap-3 text-caption">
              <div>
                <strong>Só desta filial:</strong> <span className="text-ink-muted">veículos, contratos, caixa do dia, vistorias e ordens de serviço.</span>
              </div>
              <div>
                <strong>Compartilhado na empresa:</strong> <span className="text-ink-muted">clientes, marca, modelos de contrato, plano de contas e usuários (com acesso escolhido por filial).</span>
              </div>
            </div>
          </Secao>
        </aside>
      </div>
    </form>
  );
}

/** Nova filial (sem `id`) ou edição de uma existente. Só o administrador. */
export function FormularioDaFilial({ id }: { id?: number }) {
  const { eu } = useSessao();
  const podeVer = eu.pode.administracao;
  const consulta = useQuery({ queryKey: ["filiais-admin", "detalhe", id], queryFn: () => filiais.obter(id ?? 0), enabled: podeVer && id !== undefined });

  if (!podeVer)
    return (
      <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
        Só o administrador acessa Filiais.
      </p>
    );
  if (id === undefined) return <Formulario />;
  if (consulta.isPending)
    return (
      <p className="text-body text-ink-muted" aria-busy="true">
        Carregando a filial…
      </p>
    );
  if (consulta.isError)
    return (
      <p role="alert" className="text-body">
        {mensagemDoErro(consulta.error)}
      </p>
    );
  return <Formulario key={`${consulta.data.id}-${consulta.dataUpdatedAt}`} filial={consulta.data} />;
}
