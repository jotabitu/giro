"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet } from "lucide-react";
import { useRef, useState } from "react";
import { Button, Icone, StatusBadge, TextField } from "@/design-system";
import { importacao, type Eu, type Importacao, type LinhaDaImportacao, type TipoDeImportacao } from "@/lib/api";
import { ErroApi } from "@/lib/api";
import { emAndamento, plural, resumoDoArquivo, rotuloDoCampo, TAMANHO_MAXIMO_DA_PLANILHA, TIPOS_DE_IMPORTACAO } from "@/lib/importacao";
import { mensagemDoErro } from "@/lib/erros";
import { useFilial } from "@/lib/filial-escolhida";

const LIMITE_DA_LISTA = 10;

/** Baixa um arquivo que exige login: busca com o token e entrega ao navegador. */
function entregar(arquivo: Blob, nome: string) {
  const url = URL.createObjectURL(arquivo);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

function Falha({ erro }: { erro: unknown }) {
  const faltando = erro instanceof ErroApi ? (erro.detalhes?.colunas_faltando as string[] | undefined) : undefined;
  return (
    <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
      {mensagemDoErro(erro)}
      {faltando && faltando.length > 0 ? ` Faltam as colunas: ${faltando.join(", ")}.` : ""}
    </p>
  );
}

/** A linha com erro: a mensagem da API e, no modo "Corrigir aqui", o campo para ajustar o valor ou ignorar a linha. */
function LinhaComErro({ imp, linha, corrigindo }: { imp: Importacao; linha: LinhaDaImportacao; corrigindo: boolean }) {
  const cliente = useQueryClient();
  const erro = linha.erros[0];
  const [valor, setValor] = useState(erro ? (linha.dados[erro.campo] ?? "") : "");
  const depois = () => Promise.all([cliente.invalidateQueries({ queryKey: ["importacao"] })]);
  const salvar = useMutation({ mutationFn: () => importacao.corrigir(imp.id, linha.numero, { [erro?.campo ?? ""]: valor.trim() }), onSuccess: depois });
  const ignorar = useMutation({ mutationFn: () => importacao.ignorar(imp.id, linha.numero), onSuccess: depois });
  const ocupado = salvar.isPending || ignorar.isPending;
  return (
    <li className="flex flex-col gap-2 border-b border-line py-2 text-caption last:border-b-0">
      <div className="flex gap-2.5">
        <span className="wl-mono shrink-0">
          <span className="hidden md:inline">linha </span>
          <span className="md:hidden">L</span>
          {linha.numero}
        </span>
        <span>{linha.erros.map((e) => e.mensagem).join(". ") || "Linha com erro"}</span>
      </div>
      {corrigindo && erro && (
        <div className="flex flex-col gap-2 rounded-md bg-surface p-3">
          <TextField cheio rotulo={`Corrigir ${rotuloDoCampo(erro.campo)}`} value={valor} onChange={(e) => setValor(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button compacto variante="solido" disabled={ocupado || valor.trim() === ""} onClick={() => salvar.mutate()}>
              {salvar.isPending ? "Salvando…" : "Salvar a correção"}
            </Button>
            <Button compacto variante="quieto" disabled={ocupado} onClick={() => ignorar.mutate()}>
              Ignorar esta linha
            </Button>
          </div>
          {(salvar.isError || ignorar.isError) && <Falha erro={salvar.error ?? ignorar.error} />}
        </div>
      )}
    </li>
  );
}

function ListaDeErros({ imp, corrigindo }: { imp: Importacao; corrigindo: boolean }) {
  const linhas = useQuery({ queryKey: ["importacao", "linhas", imp.id, imp.contagens.com_erro, imp.contagens.prontas], queryFn: () => importacao.linhas(imp.id, "com_erro") });
  if (linhas.isPending) return <p className="m-0 text-caption text-ink-muted">Carregando as linhas com erro…</p>;
  if (linhas.isError) return <Falha erro={linhas.error} />;
  const lista = linhas.data;
  const mostradas = corrigindo ? lista : lista.slice(0, LIMITE_DA_LISTA);
  return (
    <>
      <ul className="m-0 list-none p-0" aria-label="Linhas com erro">
        {mostradas.map((l) => (
          <LinhaComErro key={l.numero} imp={imp} linha={l} corrigindo={corrigindo} />
        ))}
      </ul>
      {!corrigindo && lista.length > LIMITE_DA_LISTA && <p className="m-0 text-caption text-ink-muted">{`E mais ${lista.length - LIMITE_DA_LISTA}. Use "Corrigir aqui" para ver todas.`}</p>}
    </>
  );
}

/** Uma caixa do assistente (Veículos ou Clientes): enviar, conferir, corrigir as linhas com erro e importar as prontas (IMP-02, IMP-03). */
export function CaixaDeImportacao({ tipo, atual, eu }: { tipo: TipoDeImportacao; atual: Importacao | null; eu: Eu }) {
  const cliente = useQueryClient();
  const filial = useFilial();
  const meta = TIPOS_DE_IMPORTACAO.find((t) => t.tipo === tipo)!;
  const entrada = useRef<HTMLInputElement>(null);
  const [arrastando, setArrastando] = useState(false);
  const [corrigindo, setCorrigindo] = useState(false);
  const [recusa, setRecusa] = useState<string | null>(null);

  const atualizar = () => cliente.invalidateQueries({ queryKey: ["importacao"] });
  const enviar = useMutation({
    mutationFn: (arquivo: File) => {
      const escolhida = filial?.escolha && filial.escolha !== "todas" ? Number(filial.escolha) : (eu.filiais[0]?.id ?? undefined);
      return importacao.enviar({ tipo, arquivo, filial_id: tipo === "veiculos" ? escolhida : undefined });
    },
    onSuccess: atualizar,
  });
  const importar = useMutation({ mutationFn: () => importacao.importar(atual?.id ?? 0), onSuccess: atualizar });
  const cancelar = useMutation({
    mutationFn: () => importacao.cancelar(atual?.id ?? 0),
    onSuccess: async () => {
      setCorrigindo(false);
      await atualizar();
    },
  });
  const modelo = useMutation({ mutationFn: async () => entregar(await importacao.modelo(tipo), `modelo-${tipo}.xlsx`) });

  function escolher(arquivo: File | undefined) {
    if (!arquivo) return;
    setRecusa(null);
    if (!/\.(xlsx|csv)$/i.test(arquivo.name)) return setRecusa("Envie uma planilha .xlsx ou .csv.");
    if (arquivo.size > TAMANHO_MAXIMO_DA_PLANILHA) return setRecusa("A planilha pode ter até 5 MB. Divida em partes menores.");
    enviar.mutate(arquivo);
  }

  const c = atual?.contagens;
  const conferindo = atual ? emAndamento(atual) : false;
  const mostrandoLinhas = atual && (atual.status === "validada" || atual.status === "concluida") && c && c.com_erro > 0;

  return (
    <section className="flex flex-col gap-3.5 rounded-lg bg-surface p-4 md:bg-surface-sunken md:p-5" aria-label={meta.titulo}>
      <div className="flex items-center gap-3">
        <span className="grid size-[42px] shrink-0 place-items-center rounded-md bg-surface-sunken md:size-11 md:bg-surface" aria-hidden="true">
          <Icone de={FileSpreadsheet} />
        </span>
        <div className="min-w-0">
          <div className="text-body font-medium">{meta.titulo}</div>
          <div className="text-caption text-ink-muted">{atual ? resumoDoArquivo(atual) : meta.apoio}</div>
        </div>
      </div>

      {conferindo && (
        <p role="status" aria-busy="true" className="m-0 text-body text-ink-muted">
          {atual?.status === "importando" ? "Importando as linhas prontas…" : "Conferindo a planilha linha por linha…"}
        </p>
      )}

      {atual && c && !conferindo && atual.status !== "falhou" && (
        <>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tom="sucesso">{atual.status === "concluida" && c.prontas === 0 ? `${c.importadas} importados` : `${c.prontas} ${c.prontas === 1 ? "pronto" : "prontos"}`}</StatusBadge>
            {atual.status === "concluida" && c.prontas > 0 && <StatusBadge tom="neutro">{c.importadas} importados</StatusBadge>}
            {c.com_erro > 0 && <StatusBadge tom="critico">{c.com_erro} com erro</StatusBadge>}
            {c.acima_do_limite > 0 && <StatusBadge tom="alerta">{c.acima_do_limite} acima do limite</StatusBadge>}
          </div>
          {atual.aviso && (
            <p role="note" className="m-0 rounded-md bg-warning-soft p-3 text-caption text-warning-ink">
              {atual.aviso.mensagem}
            </p>
          )}
          {atual.plano && atual.plano.cabem !== null && c.prontas > atual.plano.cabem && !atual.aviso && (
            <p role="note" className="m-0 text-caption text-ink-muted">
              O plano comporta mais {plural(atual.plano.cabem, "veículo", "veículos")}. Importamos até o limite e avisamos o que ficou de fora.
            </p>
          )}
          {mostrandoLinhas && <ListaDeErros imp={atual} corrigindo={corrigindo} />}
          <div className="flex flex-wrap gap-2">
            {c.com_erro > 0 && (
              <Button compacto onClick={() => setCorrigindo((x) => !x)}>
                {corrigindo ? "Fechar correção" : "Corrigir aqui"}
              </Button>
            )}
            <Button compacto variante="solido" disabled={c.prontas === 0 || importar.isPending} onClick={() => importar.mutate()}>
              {importar.isPending ? "Importando…" : `Importar os ${c.prontas}`}
            </Button>
            {atual.status === "validada" && (
              <Button compacto variante="quieto" disabled={cancelar.isPending} onClick={() => cancelar.mutate()}>
                Trocar a planilha
              </Button>
            )}
          </div>
          {importar.isError && <Falha erro={importar.error} />}
          {cancelar.isError && <Falha erro={cancelar.error} />}
        </>
      )}

      {atual?.status === "falhou" && (
        <>
          <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
            Não conseguimos ler esta planilha. Confira o arquivo e envie de novo.
          </p>
          <div>
            <Button compacto onClick={() => entrada.current?.click()}>
              Enviar de novo
            </Button>
          </div>
        </>
      )}

      {(!atual || atual.status === "falhou") && (
        <div
          className={`flex h-[140px] flex-col items-center justify-center gap-1.5 rounded-[20px] border-[1.5px] border-dashed text-center text-caption text-ink-muted md:bg-surface ${arrastando ? "border-ink" : "border-line"}`}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastando(true);
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastando(false);
            escolher(e.dataTransfer.files[0]);
          }}
        >
          <span>
            <strong className="text-ink">Arraste a planilha aqui</strong>
            <br />
            ou clique para escolher (.xlsx ou .csv)
          </span>
          <Button compacto variante="quieto" disabled={enviar.isPending} onClick={() => entrada.current?.click()}>
            {enviar.isPending ? "Enviando…" : "Escolher planilha"}
          </Button>
        </div>
      )}
      <input ref={entrada} type="file" accept=".xlsx,.csv" className="sr-only" aria-label={`Planilha de ${meta.titulo.toLowerCase()}`} tabIndex={-1} onChange={(e) => escolher(e.target.files?.[0])} />
      {recusa && (
        <p role="alert" className="m-0 text-caption text-critical-ink">
          {recusa}
        </p>
      )}
      {enviar.isError && <Falha erro={enviar.error} />}

      <div>
        <button type="button" disabled={modelo.isPending} onClick={() => modelo.mutate()} className="min-h-[44px] text-left text-body underline">
          {meta.modelo}
        </button>
        {modelo.isError && <Falha erro={modelo.error} />}
      </div>
    </section>
  );
}
