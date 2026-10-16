"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Dialogo, TextField } from "@/design-system";
import { assinatura as api, filiais, type DadosFiscais, type EnderecoDaNota } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { mascaraCep, mascaraCnpj, soDigitos } from "@/lib/formatos";

// Referência: "Dados da nota fiscal" das telas Admin-Assinatura (PLT-15). O CNPJ não muda por aqui; o endereço vai inteiro.

const VAZIO: EnderecoDaNota = { cep: "", logradouro: "", numero: "", complemento: null, bairro: "", cidade: "", uf: "" };

export function linhaDoEndereco(e: EnderecoDaNota | null): string | null {
  if (!e) return null;
  return `${e.logradouro}, ${e.numero}${e.complemento ? ` ${e.complemento}` : ""} · ${e.bairro} · ${e.cidade}, ${e.uf} · CEP ${mascaraCep(e.cep)}`;
}

function Edicao({ dados, aoFechar, aoConcluir }: { dados: DadosFiscais; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const [razao, setRazao] = useState(dados.razao_social);
  const [email, setEmail] = useState(dados.email_cobranca);
  const [e, setE] = useState<EnderecoDaNota>(dados.endereco ?? VAZIO);
  const [cepAviso, setCepAviso] = useState<string | null>(null);
  const ultimoCep = useRef("");
  const definir = <K extends keyof EnderecoDaNota>(campo: K, valor: EnderecoDaNota[K]) => setE((x) => ({ ...x, [campo]: valor }));

  async function buscarCep(texto: string) {
    const cep = soDigitos(texto);
    if (cep.length !== 8 || cep === ultimoCep.current) return;
    ultimoCep.current = cep;
    try {
      const r = await filiais.cep(cep);
      setCepAviso(null);
      setE((x) => ({ ...x, logradouro: r.logradouro, bairro: r.bairro, cidade: r.cidade, uf: r.uf }));
    } catch {
      setCepAviso("Não achamos esse CEP. Preencha o endereço à mão.");
    }
  }

  const salvar = useMutation({
    mutationFn: () => api.editarDadosFiscais({ razao_social: razao.trim(), email_cobranca: email.trim(), endereco: { ...e, cep: soDigitos(e.cep), uf: e.uf.trim().toUpperCase(), complemento: e.complemento?.trim() || null } }),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["assinatura"] });
      aoConcluir("Dados da nota fiscal salvos. Valem a partir da próxima fatura.");
      aoFechar();
    },
  });
  const erro = (campo: string) => campoDoErro(salvar.error, campo);

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Dados da nota fiscal"
      descricao="Aparecem na nota fiscal da sua assinatura. As faturas já emitidas não mudam."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variante="solido" disabled={salvar.isPending} onClick={() => salvar.mutate()}>
            {salvar.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        {salvar.isError && !["razao_social", "email_cobranca", "endereco", "cnpj"].some((c) => erro(c)) && (
          <p role="alert" className="rounded-md bg-critical-soft p-3 text-caption text-critical-ink md:col-span-2">
            {mensagemDoErro(salvar.error)}
          </p>
        )}
        <TextField cheio rotulo="Razão social" value={razao} onChange={(x) => setRazao(x.target.value)} erro={erro("razao_social")} />
        <TextField cheio mono rotulo="CNPJ" value={mascaraCnpj(dados.cnpj ?? "")} readOnly dica="O CNPJ não muda por aqui. Fale com o suporte." />
        <TextField cheio rotulo="E-mail de cobrança" type="email" inputMode="email" value={email} onChange={(x) => setEmail(x.target.value)} erro={erro("email_cobranca")} dica="Recebe faturas, boletos e notas." />
        <TextField
          cheio
          mono
          rotulo="CEP"
          inputMode="numeric"
          value={mascaraCep(e.cep)}
          onChange={(x) => {
            definir("cep", x.target.value);
            void buscarCep(x.target.value);
          }}
          erro={cepAviso ?? erro("endereco")}
        />
        <TextField cheio rotulo="Rua" value={e.logradouro} onChange={(x) => definir("logradouro", x.target.value)} />
        <TextField cheio rotulo="Número" value={e.numero} onChange={(x) => definir("numero", x.target.value)} />
        <TextField cheio rotulo="Complemento" value={e.complemento ?? ""} onChange={(x) => definir("complemento", x.target.value)} />
        <TextField cheio rotulo="Bairro" value={e.bairro} onChange={(x) => definir("bairro", x.target.value)} />
        <TextField cheio rotulo="Cidade" value={e.cidade} onChange={(x) => definir("cidade", x.target.value)} />
        <TextField cheio rotulo="UF" maxLength={2} value={e.uf} onChange={(x) => definir("uf", x.target.value)} />
      </div>
    </Dialogo>
  );
}

/** Razão social, CNPJ, e-mail de cobrança e endereço da nota. Editar só aparece com `acoes.editar_dados_fiscais`. */
export function DadosFiscaisDaAssinatura({ dados, pode, aoConcluir }: { dados: DadosFiscais; pode: boolean; aoConcluir: (mensagem: string) => void }) {
  const [editando, setEditando] = useState(false);
  const endereco = linhaDoEndereco(dados.endereco);
  return (
    <section className="wl-panel" aria-label="Dados da nota fiscal">
      <div className="mb-3 flex items-center gap-3">
        <h2 className="text-heading">Dados da nota fiscal</h2>
        {pode && (
          <Button compacto variante="quieto" onClick={() => setEditando(true)}>
            Editar
          </Button>
        )}
      </div>
      <dl className="m-0 flex flex-col gap-1 text-body">
        <dd className="m-0 font-medium">{dados.razao_social}</dd>
        <dd className="m-0 text-ink-muted">CNPJ {mascaraCnpj(dados.cnpj ?? "")}</dd>
        <dd className="m-0 text-ink-muted">{dados.email_cobranca}</dd>
        <dd className="m-0 text-ink-muted">{endereco ?? "Endereço ainda não informado. Edite para completar a nota."}</dd>
      </dl>
      {editando && <Edicao dados={dados} aoFechar={() => setEditando(false)} aoConcluir={aoConcluir} />}
    </section>
  );
}
