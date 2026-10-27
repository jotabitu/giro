"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";
import { Button, StatusBadge, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { filiais } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { corpoDaFilial, filialCompleta, mascaraTelefone, UFS, VALORES_INICIAIS_DA_FILIAL, type HorarioDoFormulario, type ValoresDaFilial } from "@/lib/filiais";
import { mascaraCep, soDigitos } from "@/lib/formatos";
import { RodapeDoPasso } from "./RodapeDoPasso";

// Referência: docs/telas/html/Onboarding-Filial-Desktop.dc.html e Onboarding-Filial-Mobile.dc.html.
// Lê GET /api/filiais/ (se já há matriz, o passo já está feito) e grava POST /api/filiais/ com `matriz: true` (docs/api/plataforma.md).
// Os dois horários prontos são atalhos; o horário por dia e os feriados ficam em Administração › Filiais.

const COMERCIAL: HorarioDoFormulario = { semana: { fechado: false, abre: "08:00", fecha: "18:00" }, sab: { fechado: false, abre: "08:00", fecha: "12:00" }, dom: { fechado: true, abre: "08:00", fecha: "12:00" } };
const ESTENDIDO: HorarioDoFormulario = { semana: { fechado: false, abre: "07:00", fecha: "20:00" }, sab: { fechado: false, abre: "07:00", fecha: "20:00" }, dom: { fechado: true, abre: "08:00", fecha: "12:00" } };
const HORARIOS = [
  { chave: "comercial", rotulo: "Comercial", detalhe: "Seg a sex 8h às 18h, sáb 8h às 12h", valor: COMERCIAL },
  { chave: "estendido", rotulo: "Estendido", detalhe: "Seg a sáb 7h às 20h", valor: ESTENDIDO },
] as const;

const GRADE = "grid grid-cols-1 gap-x-5 gap-y-4 md:grid-cols-[repeat(auto-fit,minmax(200px,1fr))]";

/** Passo "Primeira filial" do assistente: a matriz. Se a empresa já tem matriz, mostra ela e segue. */
export function PassoFilial({ voltarPara, pularPara, aoContinuar }: { voltarPara: string; pularPara: string; aoContinuar: () => void }) {
  const cliente = useQueryClient();
  const lista = useQuery({ queryKey: ["filiais-admin", "lista"], queryFn: () => filiais.listar() });
  const [v, setV] = useState<ValoresDaFilial>({ ...VALORES_INICIAIS_DA_FILIAL, matriz: true });
  const [horario, setHorario] = useState<(typeof HORARIOS)[number]["chave"]>("comercial");
  const [cepAviso, setCepAviso] = useState<string | null>(null);
  const ultimoCep = useRef("");
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
    mutationFn: () => filiais.criar(corpoDaFilial({ ...v, matriz: true, horario: HORARIOS.find((h) => h.chave === horario)!.valor })),
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["filiais-admin"] }), cliente.invalidateQueries({ queryKey: ["filiais-minhas"] }), cliente.invalidateQueries({ queryKey: ["implantacao"] })]);
      aoContinuar();
    },
  });
  const erro = (campo: string) => campoDoErro(salvar.error, campo);
  const camposComErro = ["nome", "nome_curto", "endereco", "contato", "horario"];
  const erroGeral = salvar.isError && !camposComErro.some((c) => erro(c));
  const matriz = lista.data?.resultados.find((f) => f.matriz && f.ativo);
  const plano = lista.data?.plano;
  const pode = filialCompleta(v) && !salvar.isPending;

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-labelledby="passo-filial-titulo">
      <div>
        <h1 id="passo-filial-titulo" className="text-title md:text-display">
          Onde fica sua loja principal?
        </h1>
        <p className="mt-1.5 mb-0 text-body text-ink-muted">Ela vira a matriz. Veículos, contratos e caixa ficam ligados a ela; outras filiais você cadastra depois.</p>
      </div>

      {lista.isPending && (
        <p className="m-0 text-body text-ink-muted" aria-busy="true">
          Carregando as filiais…
        </p>
      )}
      {lista.isError && (
        <p role="alert" className="m-0 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(lista.error)}
        </p>
      )}

      {matriz && (
        <>
          <section aria-label="Matriz cadastrada" className="flex flex-wrap items-center gap-3 rounded-[20px] bg-surface-sunken p-4">
            <div className="min-w-0 flex-1">
              <div className="font-medium">{matriz.nome}</div>
              <div className="text-caption text-ink-muted">
                {matriz.endereco.logradouro}, {matriz.endereco.numero} · {matriz.endereco.bairro} · {matriz.endereco.cidade}, {matriz.endereco.uf}
              </div>
            </div>
            <StatusBadge tom="solido" compacto>
              Matriz
            </StatusBadge>
          </section>
          <p className="m-0 text-caption text-ink-muted">
            A matriz já está cadastrada. Para mudar endereço, horário ou feriados, ou abrir outra filial, use <Link href="/admin/filiais" className="underline">Administração › Filiais</Link>.
          </p>
        </>
      )}

      {lista.isSuccess && !matriz && (
        <form
          className="flex flex-col gap-6"
          aria-label="Nova matriz"
          onSubmit={(e) => {
            e.preventDefault();
            if (pode) salvar.mutate();
          }}
        >
          {erroGeral && (
            <p role="alert" className="rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
              {mensagemDoErro(salvar.error)}
            </p>
          )}
          <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
            <legend className="mb-1 text-heading">Endereço</legend>
            <div className={GRADE}>
              <TextField
                cheio
                mono
                rotulo="CEP"
                inputMode="numeric"
                autoComplete="postal-code"
                value={mascaraCep(v.cep)}
                onChange={(e) => {
                  definir("cep", e.target.value);
                  void buscarCep(e.target.value);
                }}
                erro={cepAviso ?? undefined}
              />
              <TextField cheio rotulo="Rua" value={v.logradouro} onChange={(e) => definir("logradouro", e.target.value)} />
              <TextField cheio rotulo="Número" inputMode="numeric" value={v.numero} onChange={(e) => definir("numero", e.target.value)} />
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
            <p className="m-0 text-caption text-ink-muted">Este endereço também vai na nota fiscal da sua assinatura. Você muda só a nota em Administração › Assinatura.</p>
            <div className={GRADE}>
              <TextField cheio rotulo="Nome da filial" value={v.nome} onChange={(e) => definir("nome", e.target.value)} erro={erro("nome")} />
              <TextField cheio rotulo="Nome curto no seletor" maxLength={30} value={v.nomeCurto} onChange={(e) => definir("nomeCurto", e.target.value)} erro={erro("nome_curto")} />
              <TextField cheio rotulo="WhatsApp de atendimento" inputMode="tel" value={mascaraTelefone(v.whatsapp)} onChange={(e) => definir("whatsapp", e.target.value)} erro={erro("contato")} />
            </div>
          </fieldset>

          <fieldset className="m-0 flex flex-col gap-3 border-0 p-0">
            <legend className="mb-1 text-heading">Horário de funcionamento</legend>
            <div role="radiogroup" aria-label="Horário" className="grid gap-2 md:grid-cols-2">
              {HORARIOS.map((h) => (
                <button
                  key={h.chave}
                  type="button"
                  role="radio"
                  aria-checked={horario === h.chave}
                  onClick={() => setHorario(h.chave)}
                  className={`flex flex-col rounded-[16px] bg-surface px-3.5 py-3 text-left ${horario === h.chave ? "ring-2 ring-ink ring-inset" : "ring-1 ring-line ring-inset"}`}
                >
                  <span className="text-body font-medium">{h.rotulo}</span>
                  <small className="text-caption text-ink-muted">{h.detalhe}</small>
                </button>
              ))}
            </div>
            {erro("horario") && (
              <p role="alert" className="m-0 text-caption text-critical-ink">
                {erro("horario")}
              </p>
            )}
            <p className="m-0 text-caption text-ink-muted">Usado para lembretes de devolução e para não contar atraso quando a loja está fechada. Horário por dia você ajusta em Administração › Filiais.</p>
          </fieldset>

          {plano && (
            <p className="m-0 text-caption text-ink-muted">
              Seu plano: {plano.nome_plano}. Filiais: {plano.limite === null ? plano.usado : `${plano.usado} de ${plano.limite}`}.
            </p>
          )}

          <div>
            <Button type="submit" variante="solido" disabled={!pode}>
              {salvar.isPending ? "Salvando…" : "Salvar matriz"}
            </Button>
          </div>
        </form>
      )}

      <RodapeDoPasso voltarPara={voltarPara} pularPara={pularPara} podeContinuar={Boolean(matriz)} aoContinuar={aoContinuar} />
    </section>
  );
}
