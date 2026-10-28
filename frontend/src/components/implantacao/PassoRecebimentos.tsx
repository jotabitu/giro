"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, StatusBadge, TextField, type TomStatus } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { CampoDeDinheiro } from "@/components/precos/CampoDeDinheiro";
import { recebimentos, type CorpoDosRecebimentos, type Recebimentos, type SituacaoDosRecebimentos, type TipoDeEmpresa } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { mascaraCelular, mascaraCep, mascaraCnpj, mascaraCpf, soDigitos } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";
import { RodapeDoPasso } from "./RodapeDoPasso";

// Referência: docs/telas/html/Onboarding-Recebimentos-Desktop.dc.html e Onboarding-Recebimentos-Mobile.dc.html (passo 10 da implantação).
// Lê GET /api/recebimentos/ e grava POST /api/recebimentos/ (docs/api/plataforma.md, "Recebimentos da empresa").
// A referência pede banco, agência, chave Pix e interruptores de formas de cobrança; a API não tem nada disso no MVP, então o formulário só leva os campos do corpo.
// O passo só conta como feito quando o parceiro aprova (IMP-07): quem marca é a API, e "Continuar" vale depois disso.

const TIPOS: { valor: TipoDeEmpresa; rotulo: string }[] = [
  { valor: "LIMITED", rotulo: "Sociedade Limitada (LTDA)" },
  { valor: "MEI", rotulo: "Microempreendedor Individual (MEI)" },
  { valor: "INDIVIDUAL", rotulo: "Empresário Individual" },
  { valor: "ASSOCIATION", rotulo: "Associação" },
];

const TOM: Record<SituacaoDosRecebimentos, TomStatus> = { desconectado: "neutro", pendente: "alerta", aprovada: "sucesso", recusada: "critico" };

const GRADE = "grid grid-cols-1 gap-x-5 gap-y-4 md:grid-cols-[repeat(auto-fit,minmax(220px,1fr))]";
const MINUTO = 60_000;

const mascaraDocumento = (t: string) => (soDigitos(t).length > 11 ? mascaraCnpj(t) : mascaraCpf(t));

type Valores = { nome: string; documento: string; tipo: TipoDeEmpresa; faturamento: string; email: string; celular: string; cep: string; logradouro: string; numero: string; complemento: string; bairro: string };

function valoresIniciais(r: Recebimentos): Valores {
  const s = r.sugestao;
  return {
    nome: s?.nome ?? "",
    documento: s?.documento ?? "",
    tipo: "LIMITED",
    faturamento: "",
    email: s?.email ?? "",
    celular: s?.celular ?? "",
    cep: s?.cep ?? "",
    logradouro: s?.logradouro ?? "",
    numero: s?.numero ?? "",
    complemento: s?.complemento ?? "",
    bairro: s?.bairro ?? "",
  };
}

/** Corpo do POST: só dígitos nos campos numéricos; o valor digitado em reais vira centavos aqui e a API confere o resto. */
export function corpoDosRecebimentos(v: Valores): CorpoDosRecebimentos | null {
  const faturamento = centavosDoTexto(v.faturamento);
  if (faturamento === null) return null;
  return {
    nome: v.nome.trim(),
    documento: soDigitos(v.documento),
    email: v.email.trim(),
    celular: soDigitos(v.celular),
    cep: soDigitos(v.cep),
    logradouro: v.logradouro.trim(),
    numero: v.numero.trim(),
    complemento: v.complemento.trim(),
    bairro: v.bairro.trim(),
    faturamento_mensal_centavos: faturamento,
    tipo_empresa: v.tipo,
  };
}

export function FormularioDeRecebimentos({ inicial, aoConectar }: { inicial: Recebimentos; aoConectar: (r: Recebimentos) => void }) {
  const [v, setV] = useState<Valores>(() => valoresIniciais(inicial));
  const definir = <K extends keyof Valores>(campo: K, valor: Valores[K]) => setV((x) => ({ ...x, [campo]: valor }));
  const corpo = corpoDosRecebimentos(v);
  const completo = corpo !== null && [corpo.nome, corpo.documento, corpo.email, corpo.celular, corpo.cep, corpo.logradouro, corpo.numero, corpo.bairro].every(Boolean);

  const enviar = useMutation({ mutationFn: (c: CorpoDosRecebimentos) => recebimentos.conectar(c), onSuccess: aoConectar });
  const erro = (campo: string) => campoDoErro(enviar.error, campo);
  const campos = ["nome", "documento", "email", "celular", "cep", "logradouro", "numero", "complemento", "bairro", "faturamento_mensal_centavos", "tipo_empresa"];
  const erroGeral = enviar.isError && !campos.some((c) => erro(c));
  const pode = completo && !enviar.isPending;

  return (
    <form
      className="flex flex-col gap-6"
      aria-label="Conectar recebimentos"
      onSubmit={(e) => {
        e.preventDefault();
        if (pode && corpo) enviar.mutate(corpo);
      }}
    >
      <p className="m-0 rounded-md bg-surface-sunken p-4 text-caption text-ink-muted">
        Os dados abaixo vão direto ao parceiro de pagamentos para abrir a conta de recebimento da empresa. O cadastro passa por análise, e o passo só conta como feito quando o parceiro aprova.
      </p>
      {erroGeral && (
        <p role="alert" className="m-0 rounded-md bg-critical-soft p-4 text-caption text-critical-ink">
          {mensagemDoErro(enviar.error)}
        </p>
      )}
      <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
        <legend className="mb-1 text-heading">Dados da empresa</legend>
        <div className={GRADE}>
          <TextField cheio rotulo="Razão social ou nome" autoComplete="organization" value={v.nome} onChange={(e) => definir("nome", e.target.value)} erro={erro("nome")} />
          <TextField cheio mono rotulo="CNPJ ou CPF" inputMode="numeric" autoComplete="off" value={mascaraDocumento(v.documento)} onChange={(e) => definir("documento", e.target.value)} erro={erro("documento")} />
          <CampoSelecao rotulo="Tipo de empresa" value={v.tipo} onChange={(e) => definir("tipo", e.target.value as TipoDeEmpresa)} opcoes={TIPOS} erro={erro("tipo_empresa")} />
          <CampoDeDinheiro rotulo="Faturamento mensal estimado (R$)" valor={v.faturamento} aoMudar={(x) => definir("faturamento", x)} erro={erro("faturamento_mensal_centavos")} />
        </div>
      </fieldset>
      <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
        <legend className="mb-1 text-heading">Contato para recebimentos</legend>
        <div className={GRADE}>
          <TextField cheio rotulo="E-mail financeiro" type="email" autoComplete="email" value={v.email} onChange={(e) => definir("email", e.target.value)} erro={erro("email")} />
          <TextField cheio mono rotulo="Celular com DDD" inputMode="tel" autoComplete="tel" value={mascaraCelular(v.celular)} onChange={(e) => definir("celular", e.target.value)} erro={erro("celular")} />
        </div>
      </fieldset>
      <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
        <legend className="mb-1 text-heading">Endereço da sede (matriz)</legend>
        <div className={GRADE}>
          <TextField cheio mono rotulo="CEP" inputMode="numeric" autoComplete="postal-code" value={mascaraCep(v.cep)} onChange={(e) => definir("cep", e.target.value)} erro={erro("cep")} />
          <TextField cheio rotulo="Logradouro" value={v.logradouro} onChange={(e) => definir("logradouro", e.target.value)} erro={erro("logradouro")} />
          <TextField cheio rotulo="Número" inputMode="numeric" value={v.numero} onChange={(e) => definir("numero", e.target.value)} erro={erro("numero")} />
          <TextField cheio rotulo="Complemento" value={v.complemento} onChange={(e) => definir("complemento", e.target.value)} erro={erro("complemento")} />
          <TextField cheio rotulo="Bairro" value={v.bairro} onChange={(e) => definir("bairro", e.target.value)} erro={erro("bairro")} />
        </div>
      </fieldset>
      <div>
        <Button type="submit" variante="solido" disabled={!pode}>
          {enviar.isPending ? "Enviando…" : "Conectar recebimentos"}
        </Button>
      </div>
    </form>
  );
}

/** Passo "Recebimentos" do assistente (só nos planos com `recebimento_parceiro`; o Essencial nem recebe o passo na lista). */
export function PassoRecebimentos({ feito, voltarPara, pularPara, aoContinuar }: { feito: boolean; voltarPara: string; pularPara: string; aoContinuar: () => void }) {
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["recebimentos"], queryFn: () => recebimentos.obter(), refetchInterval: (q) => (q.state.data?.situacao === "pendente" ? MINUTO : false) });
  const dados = consulta.data;
  const aprovada = dados?.situacao === "aprovada";

  // A aprovação marca o passo na API; relê o andamento para o "Continuar" e a lista de passos refletirem.
  useEffect(() => {
    if (aprovada && !feito) void cliente.invalidateQueries({ queryKey: ["implantacao"] });
  }, [aprovada, feito, cliente]);

  const conectado = (r: Recebimentos) => {
    cliente.setQueryData(["recebimentos"], r);
    void cliente.invalidateQueries({ queryKey: ["implantacao"] });
  };

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-6 md:wl-panel" aria-labelledby="passo-recebimentos-titulo">
      <div>
        <h1 id="passo-recebimentos-titulo" className="text-title md:text-display">
          Conectar recebimentos
        </h1>
        <p className="mt-1.5 mb-0 text-body text-ink-muted">Cadastre a conta da sua empresa no parceiro de pagamentos para emitir Pix e boleto com baixa automática.</p>
      </div>

      {consulta.isPending && (
        <p className="m-0 text-body text-ink-muted" aria-busy="true">
          Carregando os recebimentos…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="m-0 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}

      {dados && (
        <section aria-label="Situação dos recebimentos" className="flex flex-col gap-2 rounded-[20px] bg-surface-sunken p-4">
          <div>
            <StatusBadge tom={TOM[dados.situacao]}>{dados.rotulo}</StatusBadge>
          </div>
          <p className="m-0 text-body">{dados.mensagem}</p>
        </section>
      )}

      {dados?.acoes.conectar && <FormularioDeRecebimentos inicial={dados} aoConectar={conectado} />}

      {dados && dados.situacao !== "aprovada" && (
        <p className="m-0 text-caption text-ink-muted">Pode deixar para depois: enquanto a conta não estiver ligada, você registra os pagamentos à mão em Contas a receber.</p>
      )}

      <RodapeDoPasso voltarPara={voltarPara} pularPara={pularPara} podeContinuar={feito} aoContinuar={aoContinuar} />
    </section>
  );
}
