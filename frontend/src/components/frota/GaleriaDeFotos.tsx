"use client";

import { Camera } from "lucide-react";
import { useRef, useState } from "react";
import { Button, Dialogo, Icone, Panel } from "@/design-system";
import type { FotoDaGaleria } from "@/lib/api";

// VEI-10, CA-414-01 a 09. Referência: Veiculo-Editar-Desktop|Mobile, "Galeria de fotos".
// Componente de apresentação: não chama a API. O editar do veículo liga as ações (GaleriaDoEditar) e o cadastro
// de veículo novo (T-437) pode ligar as próprias. Limite, formato e permissões são da API: aqui só se mostra o que ela devolve.

export type RecusaDeFoto = { chave: string; nome: string; mensagem: string };

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

const ACEITOS = "image/jpeg,image/png";

function Cartao({ foto, total, podeEditar, ocupado, aoTrocar, aoUsarComoCapa, aoPedirApagar }: { foto: FotoDaGaleria; total: number; podeEditar: boolean; ocupado: boolean; aoTrocar: (f: File) => void; aoUsarComoCapa: () => void; aoPedirApagar: () => void }) {
  const troca = useRef<HTMLInputElement>(null);
  return (
    <li className="flex min-w-0 flex-col gap-2">
      <div className="relative h-[120px] overflow-hidden rounded-md bg-surface-sunken">
        {foto.url ? (
          // A URL é assinada e vale 15 minutos (AUD-05).
          // eslint-disable-next-line @next/next/no-img-element
          <img src={foto.url} alt={`Foto ${foto.numero} de ${total}`} className="size-full object-cover" />
        ) : (
          <span aria-hidden="true" className="absolute inset-0 grid place-items-center text-ink-muted opacity-[.55]">
            <Icone de={Camera} className="size-[18px]" />
          </span>
        )}
        {foto.capa && <span className="absolute left-2 top-2 rounded-pill bg-surface px-2 py-[2px] text-[12px] font-medium">Capa</span>}
      </div>
      <div className="text-caption text-ink-muted">
        Foto {foto.numero} de {total}
      </div>
      {podeEditar && (
        <div className="flex flex-wrap gap-2">
          {!foto.capa && (
            <Button compacto variante="quieto" disabled={ocupado} onClick={aoUsarComoCapa}>
              Usar como capa
            </Button>
          )}
          <Button compacto variante="quieto" disabled={ocupado} onClick={() => troca.current?.click()}>
            Trocar
          </Button>
          <Button compacto variante="quieto" disabled={ocupado} onClick={aoPedirApagar}>
            Apagar
          </Button>
          <input
            ref={troca}
            type="file"
            accept={ACEITOS}
            className="hidden"
            aria-label={`Escolher a foto que troca a foto ${foto.numero}`}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) aoTrocar(f);
            }}
          />
        </div>
      )}
    </li>
  );
}

export function GaleriaDeFotos({ fotos, total, limite, podeEditar, motivo, ocupado = false, progresso, recusas = [], aoEnviar, aoTrocar, aoUsarComoCapa, aoApagar, aoDispensarRecusas }: GaleriaDeFotosProps) {
  const escolher = useRef<HTMLInputElement>(null);
  const [apagando, setApagando] = useState<FotoDaGaleria | null>(null);
  return (
    <Panel titulo="Galeria de fotos" subtitulo="Fotos próprias do veículo para o catálogo de vendas, o anúncio e a ficha." acao={<span className="text-caption text-ink-muted">{total} de {limite} fotos</span>}>
      <div className="flex flex-col gap-4">
        {podeEditar && (
          <div className="flex flex-col items-start gap-2 rounded-md border border-dashed border-line p-4">
            <Button variante="solido" compacto disabled={ocupado} onClick={() => escolher.current?.click()}>
              {ocupado ? "Enviando…" : "Selecionar fotos"}
            </Button>
            <input
              ref={escolher}
              type="file"
              multiple
              accept={ACEITOS}
              className="hidden"
              aria-label="Escolher as fotos para enviar"
              onChange={(e) => {
                const arquivos = Array.from(e.target.files ?? []);
                e.target.value = "";
                if (arquivos.length > 0) aoEnviar(arquivos);
              }}
            />
            <span className="text-caption text-ink-muted">JPG ou PNG de até 10 MB · até {limite} fotos no total · a localização (GPS) é removida</span>
            {progresso && (
              <span role="status" className="text-caption">
                {progresso}
              </span>
            )}
          </div>
        )}
        {!podeEditar && motivo && <p className="text-body text-ink-muted">{motivo}</p>}
        {recusas.length > 0 && (
          <div role="alert" className="flex flex-col gap-1 rounded-md bg-surface-sunken p-3">
            {recusas.map((r) => (
              <p key={r.chave} className="m-0 text-body text-critical-ink">
                <span className="wl-mono">{r.nome}</span>: {r.mensagem}
              </p>
            ))}
            {aoDispensarRecusas && (
              <Button compacto variante="quieto" onClick={aoDispensarRecusas}>
                Fechar o aviso
              </Button>
            )}
          </div>
        )}
        {fotos.length === 0 ? (
          <p className="text-body text-ink-muted">Nenhuma foto do veículo.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {fotos.map((f) => (
              <Cartao key={f.id} foto={f} total={total} podeEditar={podeEditar} ocupado={ocupado} aoTrocar={(a) => aoTrocar(f, a)} aoUsarComoCapa={() => aoUsarComoCapa(f)} aoPedirApagar={() => setApagando(f)} />
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
