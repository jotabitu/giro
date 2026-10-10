"use client";

import { useEffect, useState } from "react";
import { Panel, TextField } from "@/design-system";
import type { Vistoria } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, soDigitos } from "@/lib/formatos";
import { Avarias, DialogoDeAvaria, GradeDeFotos, ListaDeItens, NiveisDeCombustivel } from "./Campos";
import type { VistoriaEmEdicao } from "./useVistoriaEmEdicao";

const milhar = (n: number) => new Intl.NumberFormat("pt-BR").format(n);

/** Quilometragem e combustível. Na chegada, o km da saída aparece ao lado, travado, e o texto de comparação vem da API. */
export function PainelDeKmECombustivel({
  v,
  edicao,
  titulo,
  rotuloKm,
  rotuloCombustivel,
  kmNaSaida,
  dicaDoKm,
  desativado,
}: {
  v: Vistoria;
  edicao: VistoriaEmEdicao;
  titulo: string;
  rotuloKm: string;
  rotuloCombustivel: string;
  kmNaSaida?: number | null;
  dicaDoKm?: string;
  desativado?: boolean;
}) {
  const [texto, setTexto] = useState(v.km === null ? "" : milhar(v.km));
  // A resposta da API (km corrigido, vistoria refeita) manda no que está na tela.
  useEffect(() => setTexto(v.km === null ? "" : milhar(v.km)), [v.km]);
  const confirmar = () => {
    const digitos = soDigitos(texto);
    const km = digitos === "" ? null : Number(digitos);
    if (km !== v.km) edicao.editar.mutate({ km });
    else setTexto(km === null ? "" : milhar(km));
  };
  const dica = dicaDoKm ?? `Última leitura: ${milhar(v.km_ultima_leitura.km)} km em ${dataCurta(v.km_ultima_leitura.em)}`;
  return (
    <Panel titulo={titulo}>
      <div className="flex flex-col gap-4">
        <div className={kmNaSaida !== undefined ? "grid gap-4 md:grid-cols-2" : ""}>
          {kmNaSaida !== undefined && <TextField cheio rotulo="Km na saída" value={kmNaSaida === null ? "—" : milhar(kmNaSaida)} disabled readOnly />}
          <TextField
            cheio
            rotulo={rotuloKm}
            inputMode="numeric"
            value={texto}
            disabled={desativado}
            onChange={(e) => setTexto(e.target.value)}
            onBlur={confirmar}
            onKeyDown={(e) => e.key === "Enter" && confirmar()}
            dica={dica}
          />
        </div>
        <div>
          <div className="wl-field__label mb-2">{rotuloCombustivel}</div>
          <NiveisDeCombustivel valor={v.combustivel} desativado={desativado} aoMudar={(c) => edicao.editar.mutate({ combustivel: c })} />
        </div>
      </div>
    </Panel>
  );
}

/** Fotos obrigatórias da saída: o que já foi feito e o que falta. */
export function PainelDeFotos({ v, edicao, desativado }: { v: Vistoria; edicao: VistoriaEmEdicao; desativado?: boolean }) {
  return (
    <Panel titulo="Fotos" subtitulo={`${v.fotos_obrigatorias.feitas} de ${v.fotos_obrigatorias.total} obrigatórias · arraste arquivos ou use o celular`}>
      <GradeDeFotos fotos={v.fotos} enviando={edicao.fotoEnviando} desativado={desativado} aoEnviar={(posicao, arquivo) => edicao.foto.mutate({ posicao, arquivo })} />
    </Panel>
  );
}

/** Itens conferidos, avarias e observações. */
export function PainelDeItens({ v, edicao, desativado }: { v: Vistoria; edicao: VistoriaEmEdicao; desativado?: boolean }) {
  const [aberto, setAberto] = useState(false);
  const [observacoes, setObservacoes] = useState(v.observacoes ?? "");
  useEffect(() => setObservacoes(v.observacoes ?? ""), [v.observacoes]);
  return (
    <Panel titulo="Itens conferidos">
      <div className="flex flex-col gap-4">
        <ListaDeItens itens={v.itens} avarias={v.avarias.length} desativado={desativado} aoMudar={(codigo, ok) => edicao.editar.mutate({ itens: [{ codigo, ok }] })} />
        <Avarias avarias={v.avarias} desativado={desativado} aoRemover={(a) => edicao.remover.mutate(a)} aoRegistrar={() => setAberto(true)} />
        <div className="wl-field wl-field--cheio">
          <label className="wl-field__label" htmlFor="observacoes-da-vistoria">
            Observações
          </label>
          <textarea
            id="observacoes-da-vistoria"
            className="wl-input"
            rows={3}
            placeholder="Algo mais que o cliente deva saber"
            value={observacoes}
            disabled={desativado}
            onChange={(e) => setObservacoes(e.target.value)}
            onBlur={() => observacoes !== (v.observacoes ?? "") && edicao.editar.mutate({ observacoes })}
          />
        </div>
      </div>
      {aberto && (
        <DialogoDeAvaria
          chegada={v.tipo === "devolucao"}
          enviando={edicao.avaria.isPending}
          erro={edicao.avaria.isError ? mensagemDoErro(edicao.avaria.error) : null}
          aoFechar={() => {
            edicao.avaria.reset();
            setAberto(false);
          }}
          aoConfirmar={(dados) => edicao.avaria.mutate(dados, { onSuccess: () => setAberto(false) })}
        />
      )}
    </Panel>
  );
}
