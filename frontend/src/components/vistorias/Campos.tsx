"use client";

import { Camera, Check, Info } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Button, Dialogo, Icone, StatusBadge, TextField } from "@/design-system";
import type { AvariaDaVistoria, Combustivel, FotoDaVistoria, ItemDaVistoria, PosicaoFoto } from "@/lib/api";
import { horaCurta } from "@/lib/formatos";
import { NIVEIS, POSICOES } from "@/lib/vistorias";

/** Nível do tanque em cinco botões. No celular os rótulos são curtos (R, 1/4, 1/2, 3/4, 4/4). */
export function NiveisDeCombustivel({ valor, aoMudar, desativado }: { valor: Combustivel | null; aoMudar: (c: Combustivel) => void; desativado?: boolean }) {
  return (
    <div role="group" aria-label="Nível de combustível" className="flex gap-2">
      {NIVEIS.map((n) => (
        <button
          key={n.valor}
          type="button"
          aria-pressed={valor === n.valor}
          disabled={desativado}
          onClick={() => aoMudar(n.valor)}
          className={`min-h-[44px] flex-1 rounded-md px-2 text-body ${valor === n.valor ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}
        >
          <span className="hidden md:inline">{n.rotulo}</span>
          <span className="md:hidden">{n.curto}</span>
        </button>
      ))}
    </div>
  );
}

function Foto({ posicao, rotulo, foto, enviando, desativado, aoEscolher }: { posicao: PosicaoFoto; rotulo: string; foto: FotoDaVistoria | undefined; enviando: boolean; desativado?: boolean; aoEscolher: (p: PosicaoFoto, f: File) => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const escolher = (e: ChangeEvent<HTMLInputElement>) => {
    const arquivo = e.target.files?.[0];
    if (arquivo) aoEscolher(posicao, arquivo);
    e.target.value = "";
  };
  return (
    <>
      <button
        type="button"
        disabled={desativado || enviando}
        onClick={() => entrada.current?.click()}
        aria-label={foto ? `${rotulo}: foto de ${horaCurta(foto.tirada_em)}. Tirar de novo` : `${rotulo}: tirar foto`}
        className={`flex min-h-[88px] flex-col items-center justify-center gap-1 rounded-lg px-2 py-3 text-body ${foto ? "bg-surface-sunken text-ink" : "border border-dashed border-line text-ink-muted"}`}
      >
        {foto ? (
          <span aria-hidden="true" className="grid h-6 w-6 place-items-center rounded-pill bg-success-soft text-success-ink">
            <Icone de={Check} />
          </span>
        ) : (
          <Icone de={Camera} />
        )}
        <span>{enviando ? "Enviando…" : rotulo}</span>
        {foto && <small className="text-caption text-ink-muted">{horaCurta(foto.tirada_em)}</small>}
      </button>
      <input ref={entrada} type="file" accept="image/jpeg,image/png" capture="environment" className="hidden" onChange={escolher} tabIndex={-1} aria-hidden="true" />
    </>
  );
}

/** As seis posições de foto: feitas (com a hora) e por fazer. A de avaria aceita várias, a de posição fixa troca a anterior. */
export function GradeDeFotos({ fotos, aoEnviar, enviando, desativado }: { fotos: FotoDaVistoria[]; aoEnviar: (p: PosicaoFoto, f: File) => void; enviando: PosicaoFoto | null; desativado?: boolean }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
      {POSICOES.map((p) => (
        <Foto key={p.valor} posicao={p.valor} rotulo={p.rotulo} foto={[...fotos].reverse().find((f) => f.posicao === p.valor)} enviando={enviando === p.valor} desativado={desativado} aoEscolher={aoEnviar} />
      ))}
    </div>
  );
}

function Caixa({ marcado, indefinido, aoMudar, desativado, rotulo }: { marcado: boolean; indefinido: boolean; aoMudar: () => void; desativado?: boolean; rotulo: string }) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indefinido;
  }, [indefinido]);
  return <input ref={ref} type="checkbox" aria-label={rotulo} className="h-5 w-5 shrink-0" checked={marcado} disabled={desativado} onChange={aoMudar} />;
}

/** Itens conferidos. Sem resposta fica indefinido (traço); marcar é "ok", desmarcar é "com problema". */
export function ListaDeItens({ itens, avarias, aoMudar, desativado }: { itens: ItemDaVistoria[]; avarias: number; aoMudar: (codigo: string, ok: boolean) => void; desativado?: boolean }) {
  return (
    <div className="flex flex-col">
      {itens.map((i) => (
        <label key={i.codigo} className="flex min-h-[44px] items-center gap-3 border-b border-line py-2 text-body last:border-b-0">
          <Caixa marcado={i.ok === true} indefinido={i.ok === null} aoMudar={() => aoMudar(i.codigo, i.ok !== true)} desativado={desativado} rotulo={i.rotulo} />
          <span className="flex-1">{i.rotulo}</span>
          {i.codigo === "riscos" && avarias > 0 && (
            <StatusBadge tom="alerta" compacto>
              {avarias} {avarias === 1 ? "avaria" : "avarias"}
            </StatusBadge>
          )}
          {i.ok === false && i.codigo !== "riscos" && (
            <StatusBadge tom="alerta" compacto>
              Com problema
            </StatusBadge>
          )}
        </label>
      ))}
    </div>
  );
}

/** Avarias da vistoria: as antigas (não cobradas) e as novas, com o botão de registrar. */
export function Avarias({ avarias, aoRemover, aoRegistrar, desativado }: { avarias: AvariaDaVistoria[]; aoRemover: (a: AvariaDaVistoria) => void; aoRegistrar: () => void; desativado?: boolean }) {
  return (
    <div className="flex flex-col gap-3">
      {avarias.map((a) => (
        <div key={a.id} className="flex items-start gap-3 rounded-md bg-surface-sunken px-4 py-3 text-body">
          <Icone de={Info} />
          <span className="flex-1">
            <strong className="font-semibold">{a.descricao}.</strong> {a.origem ?? (a.vai_para_oficina ? "Vai para a oficina." : "Avaria nova, registrada nesta vistoria.")}
          </span>
          {!a.preexistente && !desativado && (
            <Button compacto variante="quieto" onClick={() => aoRemover(a)}>
              Remover
            </Button>
          )}
        </div>
      ))}
      {!desativado && (
        <div>
          <Button compacto onClick={aoRegistrar}>
            Registrar avaria
          </Button>
        </div>
      )}
    </div>
  );
}

/** Registrar uma avaria: a foto é obrigatória. Na chegada, marque se o veículo vai para a oficina; o valor se dá no acerto. */
export function DialogoDeAvaria({ chegada, enviando, erro, aoFechar, aoConfirmar }: { chegada: boolean; enviando: boolean; erro: string | null; aoFechar: () => void; aoConfirmar: (dados: { descricao: string; arquivo: File; oficina: boolean }) => void }) {
  const [descricao, setDescricao] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [oficina, setOficina] = useState(false);
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      fecharAoClicarFora={false}
      titulo="Registrar avaria"
      descricao={chegada ? "A foto é obrigatória. O valor a cobrar é dado no acerto, por quem fecha a conta." : "A avaria registrada na saída não é cobrada do cliente na devolução."}
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Voltar
          </Button>
          <Button variante="solido" disabled={!descricao.trim() || !arquivo || enviando} onClick={() => arquivo && aoConfirmar({ descricao, arquivo, oficina })}>
            {enviando ? "Registrando…" : "Registrar avaria"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextField cheio data-autofocus rotulo="O que aconteceu" value={descricao} onChange={(e) => setDescricao(e.target.value)} dica="Ex.: Retrovisor esquerdo riscado" />
        <div className="wl-field wl-field--cheio">
          <label className="wl-field__label" htmlFor="foto-da-avaria">
            Foto da avaria
          </label>
          <input id="foto-da-avaria" type="file" accept="image/jpeg,image/png" capture="environment" className="wl-input" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
        </div>
        {chegada && (
          <label className="flex min-h-[44px] items-center gap-3 text-body">
            <input type="checkbox" className="h-5 w-5" checked={oficina} onChange={(e) => setOficina(e.target.checked)} />
            O veículo vai para a oficina
          </label>
        )}
        {erro && (
          <p role="alert" className="text-body text-critical">
            {erro}
          </p>
        )}
      </div>
    </Dialogo>
  );
}
