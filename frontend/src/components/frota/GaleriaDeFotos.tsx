"use client";

import { useRef, useState } from "react";
import { Button, Dialogo, Panel, StatusBadge } from "@/design-system";
import type { FotoDaGaleria } from "@/lib/api";
import { BotaoApagar, CartaoDeFoto, FORMATOS_ACEITOS, ListaDeRecusas, ZonaDeEnvio, type RecusaDeFoto } from "./PecasDaGaleria";

// VEI-10, CA-414-01 a 09. Referência: Veiculo-Editar-Desktop|Mobile, "Galeria de fotos".
// Galeria do veículo já cadastrado: monta as peças de PecasDaGaleria com as ações do servidor (capa, trocar, apagar).
// O cadastro novo (T-437) monta as mesmas peças com as próprias ações. Limite, formato e permissões são da API.

export type { RecusaDeFoto };

export type GaleriaDeFotosProps = {
  fotos: FotoDaGaleria[];
  total: number;
  limite: number;
  /** `editar` da API: sem ele não há botão nenhum. */
  podeEditar: boolean;
  /** Frase da API quando a galeria é só para ver (veículo vendido ou baixado). */
  motivo?: string | null;
  ocupado?: boolean;
  /** Mensagem do envio em andamento, por exemplo "Enviando 2 de 5…". */
  progresso?: string | null;
  recusas?: RecusaDeFoto[];
  aoEnviar: (arquivos: File[]) => void;
  aoTrocar: (foto: FotoDaGaleria, arquivo: File) => void;
  aoUsarComoCapa: (foto: FotoDaGaleria) => void;
  aoApagar: (foto: FotoDaGaleria) => void;
  aoDispensarRecusas?: () => void;
};

function Acoes({ foto, ocupado, aoTrocar, aoUsarComoCapa, aoPedirApagar }: { foto: FotoDaGaleria; ocupado: boolean; aoTrocar: (f: File) => void; aoUsarComoCapa: () => void; aoPedirApagar: () => void }) {
  const troca = useRef<HTMLInputElement>(null);
  return (
    <>
      {!foto.capa && (
        <Button compacto variante="quieto" disabled={ocupado} onClick={aoUsarComoCapa}>
          Usar como capa
        </Button>
      )}
      <Button compacto variante="quieto" disabled={ocupado} onClick={() => troca.current?.click()}>
        Trocar
      </Button>
      <BotaoApagar disabled={ocupado} aoClicar={aoPedirApagar} />
      <input
        ref={troca}
        type="file"
        accept={FORMATOS_ACEITOS}
        className="hidden"
        aria-label={`Escolher a foto que troca a foto ${foto.numero}`}
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (f) aoTrocar(f);
        }}
      />
    </>
  );
}

export function GaleriaDeFotos({ fotos, total, limite, podeEditar, motivo, ocupado = false, progresso, recusas = [], aoEnviar, aoTrocar, aoUsarComoCapa, aoApagar, aoDispensarRecusas }: GaleriaDeFotosProps) {
  const [apagando, setApagando] = useState<FotoDaGaleria | null>(null);
  return (
    <Panel
      titulo="Galeria de fotos"
      subtitulo="Fotos próprias do veículo para o catálogo de vendas, o anúncio e a ficha."
      acao={
        <StatusBadge compacto>
          {total} de {limite} fotos
        </StatusBadge>
      }
    >
      <div className="flex flex-col gap-4">
        {podeEditar && <ZonaDeEnvio limite={limite} ocupado={ocupado} progresso={progresso} aoEscolher={aoEnviar} />}
        {!podeEditar && motivo && <p className="text-body text-ink-muted">{motivo}</p>}
        <ListaDeRecusas recusas={recusas} aoDispensar={aoDispensarRecusas} />
        {fotos.length === 0 ? (
          <p className="text-body text-ink-muted">Nenhuma foto do veículo.</p>
        ) : (
          <ul className="m-0 grid list-none grid-cols-1 gap-0 p-0 md:grid-cols-4 md:gap-3">
            {fotos.map((f) => (
              <CartaoDeFoto
                key={f.id}
                url={f.url}
                alt={`Foto ${f.numero} de ${total}`}
                posicao={f.numero}
                capa={f.capa}
                legenda={`Foto ${f.numero} de ${total}`}
                acoes={podeEditar ? <Acoes foto={f} ocupado={ocupado} aoTrocar={(a) => aoTrocar(f, a)} aoUsarComoCapa={() => aoUsarComoCapa(f)} aoPedirApagar={() => setApagando(f)} /> : undefined}
              />
            ))}
          </ul>
        )}
      </div>
      {apagando && (
        <Dialogo
          aberto
          aoFechar={() => setApagando(null)}
          titulo="Apagar esta foto?"
          descricao="Ela sai da galeria e da ficha."
          tamanho="pequeno"
          acoes={
            <>
              <Button variante="quieto" onClick={() => setApagando(null)}>
                Voltar
              </Button>
              <Button
                variante="solido"
                onClick={() => {
                  aoApagar(apagando);
                  setApagando(null);
                }}
              >
                Apagar a foto
              </Button>
            </>
          }
        >
          <p className="text-body">Não dá para desfazer pela tela.</p>
        </Dialogo>
      )}
    </Panel>
  );
}
