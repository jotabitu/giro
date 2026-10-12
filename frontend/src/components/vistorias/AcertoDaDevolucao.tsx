"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Icone, Panel, TextField } from "@/design-system";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { vistorias, type AcertoDaDevolucao, type DevolucaoCompleta, type FormaDevolucaoAcerto, type ItemDoAcerto } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dinheiro } from "@/lib/formatos";
import { centavosDoTexto } from "@/lib/veiculos";

// O acerto é recalculado pela API a cada leitura e a cada mudança. A tela mostra os itens, o saldo, o texto e o botão que ela devolve;
// só os itens `informado` (avaria, multa de trânsito, combustível sem tanque ou preço) têm valor editável.

const FORMAS: { valor: FormaDevolucaoAcerto; rotulo: string }[] = [
  { valor: "pix", rotulo: "Pix" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
  { valor: "estorno_cartao", rotulo: "Estorno no cartão" },
];

const emReais = (centavos: number) => (centavos / 100).toFixed(2).replace(".", ",");

function Linha({ rotulo, valor, forte }: { rotulo: string; valor: string; forte?: boolean }) {
  return (
    <div className={`flex justify-between gap-3 border-b border-line py-[11px] text-body last:border-b-0 ${forte ? "font-semibold" : ""}`}>
      <span className={forte ? "" : "text-ink-muted"}>{rotulo}</span>
      <span className={forte ? "" : "font-medium"}>{valor}</span>
    </div>
  );
}

export const tituloDoResultado = (tipo: AcertoDaDevolucao["resultado"]["tipo"]) => (tipo === "devolver" ? "Devolver ao cliente" : tipo === "cobrar" ? "Cobrar do cliente" : "Saldo zerado");

/** Combustível sem o nível da chegada: a API devolve R$ 0,00 e a descrição "(falta o nível na chegada)"; a tela pede o nível. */
function LinhaDoItem({ item, semNivel }: { item: ItemDoAcerto; semNivel: boolean }) {
  if (semNivel && item.tipo === "combustivel") return <Linha rotulo="Combustível" valor="Informe o nível na chegada" />;
  return <Linha rotulo={item.descricao} valor={dinheiro(item.valor_centavos)} />;
}

/** Os itens do acerto em linhas, a caução e o resultado, como na referência (somente leitura). `semNivel`: a chegada ainda não tem o combustível. */
export function ResumoDoAcerto({ acerto, semNivel = false }: { acerto: AcertoDaDevolucao; semNivel?: boolean }) {
  const r = acerto.resultado;
  return (
    <div>
      <div>
        {acerto.itens.map((i) => (
          <LinhaDoItem key={i.id} item={i} semNivel={semNivel} />
        ))}
        {acerto.creditos.map((c) => (
          <Linha key={c.id} rotulo={c.descricao} valor={`+ ${dinheiro(c.valor_centavos)}`} />
        ))}
        <Linha rotulo="Caução a devolver" valor={`− ${dinheiro(acerto.caucao_centavos)}`} />
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-3 rounded-md bg-surface-sunken px-4 py-3">
        <span className="text-body font-medium">{tituloDoResultado(r.tipo)}</span>
        <span className="text-title font-semibold">{dinheiro(r.valor_centavos)}</span>
      </div>
      <div className="mt-2 text-caption text-ink-muted">{r.texto}</div>
    </div>
  );
}

/** DEV-07 manda pedir o encerramento ao gerente; quem encerra (administrador, gerente) não recebe esse aviso. */
export function AvisosDoAcerto({ acerto }: { acerto: AcertoDaDevolucao }) {
  const { eu } = useSessao();
  const podeEncerrar = eu.pode.locacoes_cancelar === "sim" || eu.pode.locacoes_cancelar === "aprova";
  const avisos = acerto.avisos.filter((a) => !(a.codigo === "DEV-07" && podeEncerrar));
  if (avisos.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2">
      {avisos.map((a) => (
        <li key={a.codigo} className="flex items-start gap-3 rounded-md bg-warning-soft px-4 py-3 text-body text-warning-ink">
          <Icone de={Info} />
          <span>{a.mensagem}</span>
        </li>
      ))}
    </ul>
  );
}

function ValorEditavel({ item, aoSalvar, desativado, erro }: { item: ItemDoAcerto; aoSalvar: (centavos: number) => void; desativado: boolean; erro?: string }) {
  const [texto, setTexto] = useState(emReais(item.valor_centavos));
  useEffect(() => setTexto(emReais(item.valor_centavos)), [item.valor_centavos]);
  const confirmar = () => {
    const c = centavosDoTexto(texto);
    if (c === null) return setTexto(emReais(item.valor_centavos));
    if (c !== item.valor_centavos) aoSalvar(c);
  };
  return <TextField cheio rotulo={item.descricao} inputMode="decimal" value={texto} disabled={desativado} onChange={(e) => setTexto(e.target.value)} onBlur={confirmar} onKeyDown={(e) => e.key === "Enter" && confirmar()} dica="Valor em reais, dado por quem fecha a conta" erro={erro} />;
}

/** Etapa 2 · Acerto: itens calculados, valores informados, multa de trânsito e forma de devolução. */
export function EtapaDoAcerto({ d, aoMudar, semNivel = false }: { d: DevolucaoCompleta; aoMudar: () => void; semNivel?: boolean }) {
  const cache = useQueryClient();
  const acerto = d.acerto;
  const concluido = d.status === "concluida";
  const guardar = (nova: DevolucaoCompleta) => {
    cache.setQueryData(["devolucao", d.id], nova);
    aoMudar();
  };
  const editar = useMutation({ mutationFn: ({ id, centavos }: { id: number; centavos: number }) => vistorias.editarItem(d.id, id, { valor_centavos: centavos }), onSuccess: guardar });
  const remover = useMutation({ mutationFn: (id: number) => vistorias.removerItem(d.id, id), onSuccess: guardar });
  const adicionar = useMutation({ mutationFn: (c: { descricao: string; valor_centavos: number }) => vistorias.adicionarItem(d.id, { tipo: "multa_transito", ...c }), onSuccess: guardar });
  const forma = useMutation({ mutationFn: (f: FormaDevolucaoAcerto) => vistorias.definirForma(d.id, f), onSuccess: guardar });
  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  if (!acerto) return null;
  const centavos = centavosDoTexto(valor);
  const erro = [editar.error, remover.error, forma.error].find(Boolean);

  return (
    <div className="flex flex-col gap-6">
      <Panel titulo="Itens do acerto" subtitulo="O que o sistema calcula não se edita. Avaria e multa de trânsito têm o valor dado por você.">
        <div className="flex flex-col gap-4">
          <div>
            {acerto.itens
              .filter((i) => i.modo === "calculado")
              .map((i) => (
                <LinhaDoItem key={i.id} item={i} semNivel={semNivel} />
              ))}
            {acerto.creditos.map((c) => (
              <Linha key={c.id} rotulo={c.descricao} valor={`+ ${dinheiro(c.valor_centavos)}`} />
            ))}
          </div>
          {acerto.itens
            .filter((i) => i.modo === "informado")
            .map((i) => (
              <div key={i.id} className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <ValorEditavel item={i} desativado={concluido} aoSalvar={(c) => editar.mutate({ id: i.id, centavos: c })} erro={editar.isError ? campoDoErro(editar.error, "valor_centavos") : undefined} />
                </div>
                {!concluido && i.tipo === "multa_transito" && (
                  <Button variante="quieto" compacto onClick={() => remover.mutate(i.id)}>
                    Remover
                  </Button>
                )}
              </div>
            ))}
          {!concluido && (
            <div className="grid items-start gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto]">
              <TextField cheio rotulo="Multa de trânsito" placeholder="Descreva a multa" value={descricao} onChange={(e) => setDescricao(e.target.value)} erro={adicionar.isError ? campoDoErro(adicionar.error, "descricao") : undefined} />
              <TextField cheio rotulo="Valor" inputMode="decimal" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} erro={adicionar.isError ? campoDoErro(adicionar.error, "valor_centavos") : undefined} />
              <div className="md:pt-[26px]">
                <Button
                  disabled={!descricao.trim() || centavos === null || adicionar.isPending}
                  onClick={() => centavos !== null && adicionar.mutate({ descricao, valor_centavos: centavos }, { onSuccess: () => (setDescricao(""), setValor("")) })}
                >
                  Adicionar
                </Button>
              </div>
            </div>
          )}
          {erro && (
            <p role="alert" className="text-body text-critical">
              {mensagemDoErro(erro)}
            </p>
          )}
        </div>
      </Panel>

      {acerto.resultado.tipo === "devolver" && (
        <Panel titulo="Devolução do saldo">
          <CampoSelecao
            rotulo="Forma de devolução"
            value={acerto.forma_devolucao ?? ""}
            disabled={concluido}
            vazio="Escolha como devolver"
            onChange={(e) => e.target.value && forma.mutate(e.target.value as FormaDevolucaoAcerto)}
            opcoes={FORMAS.map((f) => ({ valor: f.valor, rotulo: f.rotulo }))}
            dica="Pix: a locadora faz a transferência e marca como feita. Dinheiro sai do caixa do dia."
          />
        </Panel>
      )}
    </div>
  );
}
