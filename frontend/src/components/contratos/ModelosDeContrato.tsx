"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useState } from "react";
import { Button, Dialogo, Icone, StatusBadge } from "@/design-system";
import { modelosContrato as api, type ModeloDeContrato, type ModeloDeContratoDaLista } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { podePublicar, rotuloDePublicar, rotuloDeUso, rotuloDoModelo } from "@/lib/contratos";
import { dataCurta } from "@/lib/formatos";
import { DialogoDoModelo } from "./DialogoDoModelo";
import { DialogoNovoModelo } from "./DialogoNovoModelo";
import { PreviaDoModelo } from "./PreviaDoModelo";

export type ModelosDeContratoProps = {
  /** Abre o diálogo de modelo novo (o botão fica no cabeçalho da tela ou do passo do assistente). */
  criando: boolean;
  aoFecharCriacao: () => void;
  aoAvisar: (aviso: string) => void;
  /** Chamado depois de publicar; o passo do assistente usa para seguir adiante (IMP-04). */
  aoPublicar?: (modelo: ModeloDeContrato) => void;
};

const tomDe = (m: ModeloDeContratoDaLista) => (m.arquivado ? "neutro" : m.status === "publicado" ? "sucesso" : "alerta");

function Detalhe({ resumo, aoAvisar, aoPublicar }: { resumo: ModeloDeContratoDaLista; aoAvisar: (a: string) => void; aoPublicar?: (m: ModeloDeContrato) => void }) {
  const cliente = useQueryClient();
  const [editando, setEditando] = useState(false);
  const [previa, setPrevia] = useState(false);
  const [confirmaArquivar, setConfirmaArquivar] = useState(false);
  const consulta = useQuery({ queryKey: ["contratos", "modelo", resumo.id, resumo.editado_em], queryFn: () => api.obter(resumo.id) });
  const m = consulta.data;

  const publicar = useMutation({
    mutationFn: () => api.publicar(resumo.id),
    onSuccess: async (novo) => {
      await cliente.invalidateQueries({ queryKey: ["contratos"] });
      aoAvisar(`Versão ${novo.versao_publicada} publicada. Vale para os contratos novos.`);
      aoPublicar?.(novo);
    },
  });
  const arquivar = useMutation({
    mutationFn: () => api.arquivar(resumo.id),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["contratos"] });
      setConfirmaArquivar(false);
      aoAvisar("Modelo arquivado. Ele sai do uso, mas não é apagado.");
    },
  });

  return (
    <section className="wl-panel" aria-label={resumo.nome}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="m-0 text-heading font-semibold">{resumo.nome}</h2>
        <StatusBadge tom={tomDe(resumo)} compacto>
          {rotuloDoModelo(resumo)}
        </StatusBadge>
        {resumo.tem_rascunho && resumo.status === "publicado" && (
          <StatusBadge tom="alerta" compacto>
            Rascunho da versão {(resumo.versao_publicada ?? 0) + 1}
          </StatusBadge>
        )}
      </div>

      {!resumo.arquivado && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button compacto onClick={() => setPrevia(true)}>
            Ver com dados reais
          </Button>
          <Button compacto onClick={() => setEditando(true)} disabled={!m}>
            Editar texto
          </Button>
          {podePublicar(resumo) && (
            <Button compacto variante="marca" disabled={publicar.isPending} onClick={() => publicar.mutate()}>
              {publicar.isPending ? "Publicando…" : rotuloDePublicar(resumo)}
            </Button>
          )}
          <Button compacto variante="quieto" onClick={() => setConfirmaArquivar(true)}>
            Arquivar
          </Button>
        </div>
      )}
      {publicar.isError && (
        <p role="alert" className="m-0 mt-3 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(publicar.error)}
        </p>
      )}

      {consulta.isPending && (
        <p className="mt-4 text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="mt-4 rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}

      {m && (
        <>
          <div className="mt-4">
            <div className="text-caption text-ink-muted">Campos automáticos</div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {m.marcadores_usados.length === 0 && <span className="text-caption text-ink-muted">Nenhum campo automático neste texto.</span>}
              {m.marcadores_usados.map((c) => (
                <span key={c} className="wl-mono rounded-full bg-surface-sunken px-2.5 py-1 text-caption">
                  {c}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-4">
            <PreviaDoModelo modeloId={m.id} titulo={m.nome} />
          </div>
          {m.versao_publicada !== null && (
            <p className="m-0 mt-3 text-caption text-ink-muted">Versão {m.versao_publicada} está em uso. Contratos já assinados continuam com o texto da versão em que foram assinados.</p>
          )}
          {m.versoes.length > 0 && (
            <ol className="m-0 mt-3 flex list-none flex-col gap-1 p-0" aria-label="Versões publicadas">
              {m.versoes.map((v) => (
                <li key={v.versao} className="flex justify-between gap-3 text-caption">
                  <span>
                    Versão {v.versao} · {dataCurta(v.publicado_em)}
                  </span>
                  <span className="text-ink-muted">{v.contratos_gerados} {v.contratos_gerados === 1 ? "contrato" : "contratos"}</span>
                </li>
              ))}
            </ol>
          )}
        </>
      )}

      {editando && m && (
        <DialogoDoModelo
          modelo={m}
          aoFechar={() => setEditando(false)}
          aoConcluir={(aviso) => {
            setEditando(false);
            aoAvisar(aviso);
          }}
        />
      )}
      {previa && (
        <Dialogo
          aberto
          aoFechar={() => setPrevia(false)}
          titulo={`Ver com dados reais · ${resumo.nome}`}
          descricao="Prévia com os dados de exemplo. Nada é gravado."
          acoes={
            <Button variante="solido" onClick={() => setPrevia(false)}>
              Fechar
            </Button>
          }
        >
          <PreviaDoModelo modeloId={resumo.id} titulo={resumo.nome} />
        </Dialogo>
      )}
      {confirmaArquivar && (
        <Dialogo
          aberto
          aoFechar={() => setConfirmaArquivar(false)}
          titulo={`Arquivar ${resumo.nome}`}
          descricao="O modelo sai do uso em contratos novos. Ele não é apagado e os contratos já assinados não mudam."
          acoes={
            <>
              <Button variante="quieto" onClick={() => setConfirmaArquivar(false)}>
                Voltar
              </Button>
              <Button variante="solido" disabled={arquivar.isPending} onClick={() => arquivar.mutate()}>
                {arquivar.isPending ? "Arquivando…" : "Arquivar modelo"}
              </Button>
            </>
          }
        >
          {arquivar.isError && (
            <p role="alert" className="m-0 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
              {mensagemDoErro(arquivar.error)}
            </p>
          )}
        </Dialogo>
      )}
    </section>
  );
}

/** Lista de modelos de contrato e o modelo escolhido, com prévia, edição, publicação e arquivamento (IMP-04, S-09, LOC-15). Reaproveitado pelo passo Modelo de contrato do assistente. */
export function ModelosDeContrato({ criando, aoFecharCriacao, aoAvisar, aoPublicar }: ModelosDeContratoProps) {
  const [escolhido, setEscolhido] = useState<number | null>(null);
  const consulta = useQuery({ queryKey: ["contratos", "modelos"], queryFn: () => api.listar() });
  const lista = consulta.data ?? [];
  const atual = lista.find((m) => m.id === escolhido) ?? lista.find((m) => !m.arquivado) ?? lista[0];

  return (
    <div className="flex flex-col gap-6">
      {consulta.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando…
        </p>
      )}
      {consulta.isError && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          {mensagemDoErro(consulta.error)}
        </p>
      )}
      {consulta.isSuccess && lista.length === 0 && <p className="m-0 text-body text-ink-muted">Nenhum modelo ainda. Use o botão Novo modelo para começar por um modelo pronto.</p>}

      {lista.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Modelos de contrato">
          {lista.map((m) => {
            const ativo = atual?.id === m.id;
            return (
              <li key={m.id}>
                <button
                  type="button"
                  aria-pressed={ativo}
                  onClick={() => setEscolhido(m.id)}
                  className={`wl-panel flex w-full items-center gap-3.5 text-left ${ativo ? "ring-2 ring-ink ring-inset" : ""} ${m.arquivado ? "opacity-70" : ""}`}
                >
                  <span className="grid size-[52px] shrink-0 place-items-center rounded-[14px] bg-surface-sunken text-ink-muted" aria-hidden="true">
                    <Icone de={FileText} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{m.nome}</span>
                    <span className="block text-caption text-ink-muted">{rotuloDeUso(m)}</span>
                  </span>
                  <StatusBadge tom={tomDe(m)} compacto>
                    {rotuloDoModelo(m)}
                  </StatusBadge>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {atual && <Detalhe key={atual.id} resumo={atual} aoAvisar={aoAvisar} aoPublicar={aoPublicar} />}

      {criando && (
        <DialogoNovoModelo
          aoFechar={aoFecharCriacao}
          aoCriar={(m) => {
            aoFecharCriacao();
            setEscolhido(m.id);
            aoAvisar("Modelo criado como rascunho. Edite o texto e publique quando estiver pronto.");
          }}
        />
      )}
    </div>
  );
}
