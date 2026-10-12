"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ChangeEvent } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { Panel, SegmentedControl, TextField } from "@/design-system";
import { clientes, ErroApi, type ClienteCompleto } from "@/lib/api";
import { esquemaCliente, paraCorpo, VALORES_INICIAIS, type ValoresCliente } from "@/lib/clientes";
import { mensagemDoErro } from "@/lib/erros";
import { mascaraCelular, mascaraCep, mascaraCnpj, mascaraCpf } from "@/lib/formatos";
import { AnaliseDoCadastro } from "./AnaliseDoCadastro";
import { BotaoDocumento } from "./BotaoDocumento";

type Nome = FieldPath<ValoresCliente>;

const CATEGORIAS = ["A", "B", "AB", "C", "D", "E", "ACC"];

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <Panel titulo={titulo}>
      <div className="grid gap-4 md:grid-cols-2">{children}</div>
    </Panel>
  );
}

/** Novo cliente (Cliente-Desktop|Mobile): só nome, documento e celular são obrigatórios; o resto pode ficar para depois (CLI-03). */
export function NovoClienteForm() {
  const router = useRouter();
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [existente, setExistente] = useState<{ id: number; nome: string } | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors },
  } = useForm<ValoresCliente>({ resolver: zodResolver(esquemaCliente), defaultValues: VALORES_INICIAIS });
  const tipo = watch("tipo");
  const pj = tipo === "pj";

  // A análise roda sobre o que já foi digitado, sem gravar nada (POST /api/clientes/analisar/).
  const valores = watch();
  const [para, setPara] = useState(() => paraCorpo(VALORES_INICIAIS));
  const chaveAnalise = JSON.stringify(valores);
  useEffect(() => {
    const t = setTimeout(() => setPara(paraCorpo(valores)), 500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `chaveAnalise` resume `valores`
  }, [chaveAnalise]);
  const analise = useQuery({
    queryKey: ["clientes", "analisar", para],
    queryFn: () => clientes.analisar(para),
    enabled: para.documento.length > 0,
    placeholderData: (anterior) => anterior,
  });

  const salvar = useMutation({ mutationFn: (v: ValoresCliente) => clientes.criar(paraCorpo(v)) });

  /** Campos com a máscara de digitação; a API recebe só os dígitos. */
  function comMascara(nome: Nome, mascara: (t: string) => string) {
    const r = register(nome);
    return {
      ...r,
      onChange: (e: ChangeEvent<HTMLInputElement>) => {
        e.target.value = mascara(e.target.value);
        return r.onChange(e);
      },
    };
  }
  const erro = (nome: Nome) => {
    const partes = nome.split(".");
    let atual: unknown = errors;
    for (const p of partes) atual = (atual as Record<string, unknown> | undefined)?.[p];
    return (atual as { message?: string } | undefined)?.message;
  };

  async function enviar(v: ValoresCliente, depois: (c: ClienteCompleto) => void) {
    setErroGeral(null);
    setExistente(null);
    try {
      depois(await salvar.mutateAsync(v));
    } catch (e) {
      if (e instanceof ErroApi && e.status === 409 && e.codigo === "CLI-01") {
        const id = Number(e.detalhes?.cliente_id);
        setExistente(id ? { id, nome: String(e.detalhes?.nome ?? "") } : null);
        setError("documento", { message: e.message });
      } else if (e instanceof ErroApi && e.campos) {
        for (const [campo, mensagem] of Object.entries(e.campos)) setError(campo as Nome, { message: mensagem });
        setErroGeral(e.message);
      } else {
        setErroGeral(mensagemDoErro(e));
      }
    }
  }

  const salvarEFicha = handleSubmit((v) => enviar(v, (c) => router.push(`/clientes/${c.id}`)));
  // "Salvar e iniciar locação" (CLI-08) é o mesmo POST; depois abre a nova locação com o cliente.
  const salvarEAlugar = handleSubmit((v) => enviar(v, (c) => router.push(`/locacoes/nova?cliente=${c.id}`)));
  const ocupado = salvar.isPending;

  return (
    <form onSubmit={salvarEFicha} noValidate className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div>
          <nav aria-label="Caminho" className="text-body text-ink-muted">
            <Link href="/clientes" className="text-ink">
              Clientes
            </Link>{" "}
            / Novo
          </nav>
          <h1 className="mt-1 text-title md:text-display">Novo cliente</h1>
        </div>
        <div className="md:ml-auto">
          <SegmentedControl
            rotulo="Tipo de cliente"
            valor={tipo}
            aoMudar={(v) => setValue("tipo", v, { shouldDirty: true })}
            opcoes={[
              { valor: "pf", rotulo: "Pessoa física" },
              { valor: "pj", rotulo: "Pessoa jurídica" },
            ]}
          />
        </div>
      </header>

      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {erroGeral}
        </p>
      )}
      {existente && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {existente.nome ? `${existente.nome} já está cadastrado com este documento. ` : ""}
          <Link href={`/clientes/${existente.id}`} className="underline">
            Abrir o cadastro existente
          </Link>
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Secao titulo={pj ? "Dados da empresa" : "Dados pessoais"}>
            <TextField cheio rotulo={pj ? "Razão social" : "Nome completo"} autoComplete="off" erro={erro("nome")} {...register("nome")} />
            <TextField cheio mono rotulo={pj ? "CNPJ" : "CPF"} inputMode="numeric" erro={erro("documento")} {...comMascara("documento", pj ? mascaraCnpj : mascaraCpf)} />
            {!pj && <TextField cheio mono type="date" rotulo="Data de nascimento" erro={erro("nascimento")} {...register("nascimento")} />}
            <TextField cheio rotulo="Celular e WhatsApp" inputMode="tel" erro={erro("celular")} {...comMascara("celular", mascaraCelular)} />
            <TextField cheio rotulo="E-mail" type="email" inputMode="email" erro={erro("email")} {...register("email")} />
            {!pj && <TextField cheio rotulo="Profissão" erro={erro("profissao")} {...register("profissao")} />}
          </Secao>

          {pj && (
            <Secao titulo="Responsável pela empresa">
              <TextField cheio rotulo="Nome" erro={erro("responsavel.nome")} {...register("responsavel.nome")} />
              <TextField cheio mono rotulo="CPF" inputMode="numeric" erro={erro("responsavel.cpf")} {...comMascara("responsavel.cpf", mascaraCpf)} />
              <TextField cheio rotulo="Celular" inputMode="tel" erro={erro("responsavel.celular")} {...comMascara("responsavel.celular", mascaraCelular)} />
            </Secao>
          )}

          <Panel titulo={pj ? "Carteira de motorista do condutor" : "Carteira de motorista"}>
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono rotulo="Número da CNH" inputMode="numeric" erro={erro("cnh.numero")} {...register("cnh.numero")} />
              <div className={`wl-field wl-field--cheio ${erro("cnh.categoria") ? "wl-field--error" : ""}`}>
                <label className="wl-field__label" htmlFor="cnh-categoria">
                  Categoria
                </label>
                <select id="cnh-categoria" className="wl-input" aria-invalid={erro("cnh.categoria") ? true : undefined} {...register("cnh.categoria")}>
                  <option value="">Escolha</option>
                  {CATEGORIAS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                {erro("cnh.categoria") && <span className="wl-field__hint">{erro("cnh.categoria")}</span>}
              </div>
              <TextField cheio mono type="date" rotulo="Validade" erro={erro("cnh.validade")} {...register("cnh.validade")} />
              <TextField cheio mono type="date" rotulo="Primeira habilitação" erro={erro("cnh.primeira_habilitacao")} {...register("cnh.primeira_habilitacao")} />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <BotaoDocumento tipo="cnh_frente" enviado={false} />
              <BotaoDocumento tipo="cnh_verso" enviado={false} />
              <BotaoDocumento tipo="selfie_documento" enviado={false} />
            </div>
          </Panel>

          <Panel titulo="Endereço">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono rotulo="CEP" inputMode="numeric" erro={erro("endereco.cep")} {...comMascara("endereco.cep", mascaraCep)} />
              <TextField cheio rotulo="Rua" erro={erro("endereco.logradouro")} {...register("endereco.logradouro")} />
              <TextField cheio rotulo="Número" erro={erro("endereco.numero")} {...register("endereco.numero")} />
              <TextField cheio rotulo="Bairro" erro={erro("endereco.bairro")} {...register("endereco.bairro")} />
              <TextField cheio rotulo="Cidade" erro={erro("endereco.cidade")} {...register("endereco.cidade")} />
              <TextField cheio rotulo="UF" maxLength={2} erro={erro("endereco.uf")} {...register("endereco.uf")} />
            </div>
            <div className="mt-4 md:max-w-[50%]">
              <BotaoDocumento tipo="comprovante_residencia" enviado={false} />
            </div>
          </Panel>

          <Secao titulo="Referência pessoal">
            <TextField cheio rotulo="Nome" erro={erro("referencia.nome")} {...register("referencia.nome")} />
            <TextField cheio rotulo="Parentesco" erro={erro("referencia.parentesco")} {...register("referencia.parentesco")} />
            <TextField cheio rotulo="Telefone" inputMode="tel" erro={erro("referencia.telefone")} {...comMascara("referencia.telefone", mascaraCelular)} />
          </Secao>
        </div>

        <aside className="flex flex-col gap-6">
          <AnaliseDoCadastro analise={analise.data} carregando={analise.isFetching} />
          <section className="wl-panel flex flex-col gap-4">
            <label className="flex items-start gap-3 text-body">
              <input type="checkbox" className="wl-marcar" {...register("consentimento")} />
              <span>O cliente autorizou o uso dos dados para locação e cobrança, conforme a política de privacidade da empresa.</span>
            </label>
            <button type="button" disabled={ocupado} onClick={() => void salvarEAlugar()} className="wl-btn wl-btn--solid">
              Salvar e iniciar locação
            </button>
            <button type="submit" disabled={ocupado} className="wl-btn wl-btn--quiet">
              Salvar cliente
            </button>
            <Link href="/clientes" className="wl-btn wl-btn--quiet">
              Cancelar
            </Link>
          </section>
        </aside>
      </div>
    </form>
  );
}
