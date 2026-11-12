"use client";

import { Camera, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { Button, Icone, Panel, ProgressBar, StatusBadge } from "@/design-system";
import { ErroApi } from "@/lib/api";
import { FaltamFotos } from "./AvisoDeSaida";
import { FOTO_INVALIDA, mensagemDaRecusa } from "./GaleriaDoEditar";
import { BotaoApagar, CartaoDeFoto, ListaDeRecusas, ZonaDeEnvio, type RecusaDeFoto } from "./PecasDaGaleria";

// VEI-10, "Galeria no cadastro" (T-437, CA-437-01 a 11). Referência: Veiculo-Novo-Desktop|Mobile, "Fotos do veículo".
// Antes de salvar nada sobe: a pessoa escolhe, tira e marca a capa. Depois do 201 do cadastro, as fotos sobem uma de cada vez
// pela rota da galeria (POST /api/veiculos/{id}/fotos/, ADR 0036), a capa primeiro, porque a API faz da primeira enviada a capa.
// Formato, tamanho e limite também são conferidos na API; a recusa da escolha só adianta a mesma frase.

export const LIMITE_NO_CADASTRO = 20;
export { FOTO_INVALIDA };
export const PASSOU_DO_LIMITE = "O veículo pode ter até 20 fotos.";
export const SEM_CONEXAO = "Sem conexão. A foto não subiu.";
const DEZ_MB = 10 * 1024 * 1024;

export type FotoEscolhida = { chave: string; arquivo: File; url: string | null };

let proximaChave = 1;
const miniatura = (a: File): string | null => (typeof URL !== "undefined" && typeof URL.createObjectURL === "function" ? URL.createObjectURL(a) : null);
export const soltarMiniatura = (f: FotoEscolhida) => {
  if (f.url && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(f.url);
};

const fotoAceita = (a: File) => (a.type === "image/jpeg" || a.type === "image/png" || /\.(jpe?g|png)$/i.test(a.name)) && a.size <= DEZ_MB;

/** CA-437-03, 04: recusa formato e tamanho e não deixa a lista passar de 20. As que não entram não ganham miniatura. */
export function escolherFotos(atuais: FotoEscolhida[], arquivos: File[], limite = LIMITE_NO_CADASTRO): { lista: FotoEscolhida[]; recusas: RecusaDeFoto[]; passouDoLimite: boolean } {
  const lista = [...atuais];
  const recusas: RecusaDeFoto[] = [];
  let passouDoLimite = false;
  for (const a of arquivos) {
    if (!fotoAceita(a)) {
      recusas.push({ chave: `recusa-${proximaChave++}`, nome: a.name, mensagem: FOTO_INVALIDA });
    } else if (lista.length >= limite) {
      passouDoLimite = true;
    } else {
      lista.push({ chave: `foto-${proximaChave++}`, arquivo: a, url: miniatura(a) });
    }
  }
  return { lista, recusas, passouDoLimite };
}

/** Sem escolha, a capa é a primeira da lista (VEI-10). */
export const capaDaLista = (lista: FotoEscolhida[], capa: string | null): string | null => (lista.some((f) => f.chave === capa) ? capa : (lista[0]?.chave ?? null));

/** CA-437-05: a capa sobe primeiro e as outras na ordem da escolha. */
export function ordemDeEnvio(lista: FotoEscolhida[], capa: string | null): FotoEscolhida[] {
  const c = capaDaLista(lista, capa);
  return [...lista.filter((f) => f.chave === c), ...lista.filter((f) => f.chave !== c)];
}

export type EstadoDaFoto = "fila" | "enviando" | "enviada" | "recusada" | "sem_conexao";
export type ItemDoEnvio = FotoEscolhida & { capa: boolean; estado: EstadoDaFoto; mensagem?: string };

export const itensDoEnvio = (lista: FotoEscolhida[], capa: string | null): ItemDoEnvio[] => ordemDeEnvio(lista, capa).map((f, i) => ({ ...f, capa: i === 0, estado: "fila" }));

/**
 * Envia, uma de cada vez, as que estão na fila ou caíram por conexão. A recusa do arquivo (400, 403, 409...) marca o item e
 * segue para a próxima (CA-437-09); a falha de conexão para a fila ali, e "Tentar de novo" retoma dali sem repetir as que
 * subiram (CA-437-10). `aoMudar` recebe a lista nova a cada passo.
 */
export async function enviarEmSequencia(itens: ItemDoEnvio[], enviar: (arquivo: File) => Promise<unknown>, aoMudar: (itens: ItemDoEnvio[]) => void): Promise<ItemDoEnvio[]> {
  let atual = itens.map((it) => (it.estado === "sem_conexao" ? { ...it, estado: "fila" as const, mensagem: undefined } : it));
  const trocar = (i: number, parte: Partial<ItemDoEnvio>) => {
    atual = atual.map((it, j) => (j === i ? { ...it, ...parte } : it));
    aoMudar(atual);
  };
  for (let i = 0; i < atual.length; i++) {
    if (atual[i]!.estado !== "fila") continue;
    trocar(i, { estado: "enviando" });
    try {
      await enviar(atual[i]!.arquivo);
      trocar(i, { estado: "enviada" });
    } catch (e) {
      if (e instanceof ErroApi && e.status === 0 && fotoAceita(atual[i]!.arquivo)) {
        trocar(i, { estado: "sem_conexao", mensagem: SEM_CONEXAO });
        break;
      }
      trocar(i, { estado: "recusada", mensagem: mensagemDaRecusa(e, atual[i]!.arquivo) });
    }
  }
  return atual;
}

/**
 * CA-437-05, 07, 08: grava o veículo e só depois do 201 envia as fotos. Se `criar` falha (409 VEI-01, 422 PLT-03, 400),
 * o erro sobe sem nenhuma foto enviada, e quem chamou continua com a lista escolhida. `aoCriar` roda entre os dois passos.
 */
export async function cadastrarComFotos<T extends { id: number }>(
  criar: () => Promise<T>,
  itens: ItemDoEnvio[],
  enviarFoto: (veiculoId: number, arquivo: File) => Promise<unknown>,
  aoCriar: (criado: T) => void,
  aoMudar: (itens: ItemDoEnvio[]) => void,
): Promise<{ criado: T; itens: ItemDoEnvio[] }> {
  const criado = await criar();
  aoCriar(criado);
  if (itens.length === 0) return { criado, itens };
  return { criado, itens: await enviarEmSequencia(itens, (a) => enviarFoto(criado.id, a), aoMudar) };
}

export const envioTerminouBem =(itens: ItemDoEnvio[]) => itens.every((it) => it.estado === "enviada");
const parouPorConexao = (itens: ItemDoEnvio[]) => itens.some((it) => it.estado === "sem_conexao");

/** VEI-10, T-462: as que ainda não subiram e vão subir (na fila, enviando ou paradas por conexão). A recusada não conta: não será enviada. */
export const fotosQueFaltam = (itens: ItemDoEnvio[]): number => itens.filter((it) => it.estado === "fila" || it.estado === "enviando" || it.estado === "sem_conexao").length;
const enviando = (itens: ItemDoEnvio[]) => itens.some((it) => it.estado === "enviando");

/** "Enviando fotos · 2 de 5" enquanto sobe; "parou na 2 de 5" quando a conexão cai; no fim com recusa, quantas subiram. */
export function andamentoDoEnvio(itens: ItemDoEnvio[]): string {
  const n = itens.length;
  const i = itens.findIndex((it) => it.estado === "enviando" || it.estado === "sem_conexao");
  if (i >= 0) return itens[i]!.estado === "enviando" ? `Enviando fotos · ${i + 1} de ${n}` : `Enviando fotos · parou na ${i + 1} de ${n}`;
  return `Fotos enviadas · ${itens.filter((it) => it.estado === "enviada").length} de ${n}`;
}

function CabecalhoDoBloco({ total, children }: { total: number; children: React.ReactNode }) {
  const contador = (
    <StatusBadge compacto tom={total >= LIMITE_NO_CADASTRO ? "alerta" : "neutro"}>
      {total} de {LIMITE_NO_CADASTRO} fotos
    </StatusBadge>
  );
  // Abaixo de 721 px o contador desce para baixo do título, e o subtítulo usa a largura toda.
  return (
    <Panel titulo="Fotos do veículo" subtitulo="Escolha agora. As fotos são enviadas logo depois de Salvar veículo, a capa primeiro." acao={<span className="hidden md:inline-flex">{contador}</span>}>
      <div className="flex flex-col gap-4">
        <span className="md:hidden">{contador}</span>
        {children}
      </div>
    </Panel>
  );
}

/** Tamanho do arquivo escolhido, só para a pessoa reconhecer a foto: "1,8 MB", ou "240 KB" abaixo de 1 MB. */
export const tamanho = (bytes: number) =>
  bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} MB`;

export type FotosEscolhidasProps = {
  fotos: FotoEscolhida[];
  capa: string | null;
  recusas: RecusaDeFoto[];
  passouDoLimite: boolean;
  aoEscolher: (arquivos: File[]) => void;
  aoTirar: (f: FotoEscolhida) => void;
  aoUsarComoCapa: (f: FotoEscolhida) => void;
  aoDispensarRecusas: () => void;
};

/** Antes de salvar (CA-437-01 a 04): miniaturas, Tirar, Usar como capa e o limite de 20. */
export function FotosEscolhidas({ fotos, capa, recusas, passouDoLimite, aoEscolher, aoTirar, aoUsarComoCapa, aoDispensarRecusas }: FotosEscolhidasProps) {
  const c = capaDaLista(fotos, capa);
  const cheia = fotos.length >= LIMITE_NO_CADASTRO;
  return (
    <CabecalhoDoBloco total={fotos.length}>
      {cheia ? (
        <p className="m-0 rounded-lg border-2 border-dashed border-line p-4 text-center text-body font-medium text-ink-muted">Tire uma foto da lista para escolher outra</p>
      ) : (
        <ZonaDeEnvio limite={LIMITE_NO_CADASTRO} rotulo="Escolher fotos" verbo="escolher" aoEscolher={aoEscolher} />
      )}
      {passouDoLimite && (
        <p role="status" className="m-0 flex items-center gap-2 rounded-md bg-warning-soft p-3 text-body text-warning-ink">
          <Icone de={TriangleAlert} className="size-4 shrink-0" />
          {PASSOU_DO_LIMITE}
        </p>
      )}
      <ListaDeRecusas recusas={recusas} aoDispensar={aoDispensarRecusas} />
      {fotos.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-1 gap-0 p-0 md:grid-cols-[repeat(auto-fill,minmax(200px,1fr))] md:gap-3">
          {fotos.map((f, i) => (
            <CartaoDeFoto
              key={f.chave}
              url={f.url}
              alt={`Miniatura de ${f.arquivo.name}`}
              posicao={i + 1}
              capa={f.chave === c}
              legenda={`${f.arquivo.name} · ${tamanho(f.arquivo.size)}`}
              acoes={
                <>
                  {f.chave !== c && (
                    <Button compacto variante="quieto" onClick={() => aoUsarComoCapa(f)}>
                      Usar como capa
                    </Button>
                  )}
                  <BotaoApagar rotulo="Tirar" aoClicar={() => aoTirar(f)} />
                </>
              }
            />
          ))}
        </ul>
      )}
      <p className="m-0 border-t border-line pt-3 text-caption text-ink-muted">
        Nada é enviado antes de Salvar veículo. Sem escolha, a capa é a primeira da lista. Se o cadastro falhar, as fotos continuam aqui e você salva de novo sem escolher outra vez.
      </p>
    </CabecalhoDoBloco>
  );
}

function SituacaoDoItem({ item, aoTentarDeNovo }: { item: ItemDoEnvio; aoTentarDeNovo: () => void }) {
  if (item.estado === "enviada") return <StatusBadge compacto tom="sucesso">Enviada</StatusBadge>;
  if (item.estado === "enviando") return <span className="text-caption font-medium">Enviando</span>;
  if (item.estado === "fila") return <span className="text-caption text-ink-muted">Na fila</span>;
  if (item.estado === "sem_conexao")
    return (
      <Button compacto variante="quieto" onClick={aoTentarDeNovo}>
        Tentar de novo
      </Button>
    );
  return null;
}

export type EnvioDasFotosProps = { itens: ItemDoEnvio[]; placa: string; veiculoId: number; aoTentarDeNovo: () => void };

/** Depois de Salvar veículo (CA-437-05, 09, 10, 11): o andamento, a situação de cada foto e, se parou, "Ir para o veículo". */
export function EnvioDasFotos({ itens, placa, veiculoId, aoTentarDeNovo }: EnvioDasFotosProps) {
  const subiram = itens.filter((it) => it.estado === "enviada").length;
  const parado = !enviando(itens) && !envioTerminouBem(itens);
  return (
    <CabecalhoDoBloco total={itens.length}>
      <div className="flex flex-col gap-2">
        <span role="status" className="text-body font-medium">
          {andamentoDoEnvio(itens)}
        </span>
        <FaltamFotos faltam={fotosQueFaltam(itens)} />
        <ProgressBar valor={(subiram / itens.length) * 100} rotulo="Envio das fotos" />
      </div>
      <ul className="m-0 list-none overflow-hidden rounded-md border border-line p-0">
        {itens.map((it) => {
          const erro = it.estado === "recusada" || it.estado === "sem_conexao";
          return (
            <li key={it.chave} className={`flex items-center gap-3 border-t border-line px-3 py-2 first:border-t-0 ${erro ? "bg-critical-soft" : ""}`}>
              <div className="relative grid size-11 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-sunken text-ink-muted">
                {it.url ? (
                  // Miniatura local do arquivo escolhido; nada vem do servidor.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={it.url} alt={`Miniatura de ${it.arquivo.name}`} className="size-full object-cover" />
                ) : (
                  <Icone de={Camera} className="size-5" />
                )}
              </div>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="wl-mono truncate font-medium">{it.arquivo.name}</span>
                  {it.capa && (
                    <StatusBadge compacto tom="solido">
                      Capa
                    </StatusBadge>
                  )}
                </span>
                {it.mensagem && <small className="text-caption text-critical-ink">{it.mensagem}</small>}
              </div>
              <SituacaoDoItem item={it} aoTentarDeNovo={aoTentarDeNovo} />
            </li>
          );
        })}
      </ul>
      {parado ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="min-w-0 flex-1 text-caption text-ink-muted">
            {parouPorConexao(itens) ? "Tentar de novo envia só as que faltam, sem repetir as que já subiram." : "O veículo está gravado com as fotos que subiram. A que ficou de fora se envia pelo editar."}
          </span>
          <Link href={`/veiculos/${veiculoId}`} className="wl-btn wl-btn--sm wl-btn--solid">
            Ir para o veículo
          </Link>
        </div>
      ) : (
        <p className="m-0 text-caption text-ink-muted">O veículo {placa} já está gravado. Se você sair agora, ele fica com as fotos que já subiram.</p>
      )}
    </CabecalhoDoBloco>
  );
}
