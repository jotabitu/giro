"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Camera, Check, MapPin } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type ChangeEvent } from "react";
import { Aviso } from "@/components/acesso/Aviso";
import { CampoSelecao } from "@/components/lista/CampoSelecao";
import { Button, Icone, TextField } from "@/design-system";
import { ErroApi, movimentacoes, type Combustivel, type Movimentacao, type PosicaoDaFotoDaChegada } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro, horaCurta, km, placa, soDigitos } from "@/lib/formatos";
import { COMBUSTIVEIS_DA_CHEGADA, POSICOES_DA_CHEGADA, ROTA_DAS_MOVIMENTACOES } from "@/lib/movimentacoes";

// Referência: docs/telas/html/Movimentacao-Chegada-Mobile.dc.html (MOV-04, MOV-05, MOV-06).
// A API confere o km, o combustível, as 4 fotos e quem recebe, e devolve o erro no campo.

const kmComPontos = (t: string) => new Intl.NumberFormat("pt-BR").format(Number(soDigitos(t) || 0));

function Etapa({ marca, titulo, apoio, valor, destaque }: { marca: React.ReactNode; titulo: string; apoio: string; valor?: string; destaque?: boolean }) {
  return (
    <div className="flex items-center gap-3 border-b border-line py-[10px] text-body last:border-b-0">
      <span className="grid size-[26px] shrink-0 place-items-center rounded-pill bg-surface-sunken text-[12px] font-bold">{marca}</span>
      <div className="min-w-0 flex-1">
        {destaque ? <b>{titulo}</b> : titulo}
        <div className="text-caption text-ink-muted">{apoio}</div>
      </div>
      {valor && <span>{valor}</span>}
    </div>
  );
}

function Foto({ posicao, rotulo, feita, enviando, aoEscolher }: { posicao: PosicaoDaFotoDaChegada; rotulo: string; feita: boolean; enviando: boolean; aoEscolher: (p: PosicaoDaFotoDaChegada, f: File) => void }) {
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
        disabled={enviando}
        onClick={() => entrada.current?.click()}
        aria-label={feita ? `${rotulo}: foto enviada. Tirar de novo` : `${rotulo}: tirar foto`}
        className={`relative flex h-[92px] flex-col justify-end gap-[2px] rounded-[16px] px-3 py-[10px] text-left text-caption ${feita ? "bg-surface-sunken" : "items-center justify-center border-[1.5px] border-dashed border-line bg-surface text-ink-muted"}`}
      >
        {feita ? (
          <span aria-hidden="true" className="absolute top-2 right-2 grid size-6 place-items-center rounded-pill bg-success text-on-solid">
            <Icone de={Check} />
          </span>
        ) : (
          <Icone de={Camera} />
        )}
        {enviando ? "Enviando…" : rotulo}
      </button>
      <input ref={entrada} type="file" accept="image/jpeg,image/png" capture="environment" className="hidden" onChange={escolher} tabIndex={-1} aria-hidden="true" />
    </>
  );
}

/** Registrar chegada no destino (celular): km, combustível e 4 fotos da vistoria rápida, e quem recebe na transferência. */
export function RegistrarChegada({ id }: { id: number }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const agora = useAgora();
  const [kmTexto, setKmTexto] = useState("");
  const [combustivel, setCombustivel] = useState<Combustivel | null>(null);
  const [recebidoPor, setRecebidoPor] = useState("");
  const [enviando, setEnviando] = useState<PosicaoDaFotoDaChegada | null>(null);
  const [erroDaFoto, setErroDaFoto] = useState<string | null>(null);

  const consulta = useQuery({ queryKey: ["movimentacoes", "detalhe", id], queryFn: () => movimentacoes.obter(id) });
  const m: Movimentacao | undefined = consulta.data;
  const quemRecebe = useQuery({ queryKey: ["movimentacoes", "recebem", m?.destino.id], queryFn: () => movimentacoes.quemPodeReceber(m?.destino.id ?? 0), enabled: m?.transferencia === true });

  const foto = useMutation({
    mutationFn: ({ posicao, arquivo }: { posicao: PosicaoDaFotoDaChegada; arquivo: File }) => movimentacoes.enviarFotoDaChegada(id, posicao, arquivo),
    onMutate: ({ posicao }) => (setEnviando(posicao), setErroDaFoto(null)),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["movimentacoes", "detalhe", id] }),
    onError: (e) => setErroDaFoto(mensagemDoErro(e)),
    onSettled: () => setEnviando(null),
  });
  const confirmar = useMutation({
    mutationFn: () => movimentacoes.registrarChegada(id, { km: Number(soDigitos(kmTexto)), combustivel: combustivel ?? undefined, recebido_por_id: recebidoPor ? Number(recebidoPor) : undefined }),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["movimentacoes"] });
      router.push(ROTA_DAS_MOVIMENTACOES);
    },
  });

  const erro = confirmar.error;
  const campo = (nome: string) => (erro instanceof ErroApi ? erro.campos?.[nome] : undefined);
  // O 422 `VEI-01` (km menor que o atual) fala do km; o texto vem da API.
  const erroDoKm = erro instanceof ErroApi && erro.codigo === "VEI-01" ? erro.message : undefined;
  const erroGeral = erro && !campo("combustivel") && !campo("fotos") && !campo("recebido_por_id") && !erroDoKm && !(erro instanceof ErroApi && erro.campos) ? mensagemDoErro(erro) : null;

  if (consulta.isPending) return <p role="status" className="m-0 text-body text-ink-muted">Carregando a movimentação…</p>;
  if (consulta.isError || !m) return <Aviso tipo="erro">{mensagemDoErro(consulta.error)}</Aviso>;

  const fotos = m.fotos_chegada ?? [];
  const aberta = m.acoes.registrar_chegada;

  return (
    <div className="flex flex-col gap-4 md:mx-auto md:w-full md:max-w-[480px]">
      <header className="flex items-center gap-3">
        <Link href={ROTA_DAS_MOVIMENTACOES} aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-[44px]">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0">
          <h1 className="m-0 text-title">Registrar chegada</h1>
          <div className="text-caption text-ink-muted">
            <span className="wl-mono">{m.codigo}</span> · {m.veiculo.modelo} · <span className="wl-mono">{placa(m.veiculo.placa)}</span>
          </div>
        </div>
      </header>

      <section aria-label="Percurso" className="rounded-lg bg-surface px-4 py-2">
        <Etapa marca={<Icone de={Check} />} titulo={m.filial_saida.nome} apoio={`${m.iniciada_em ? `saiu ${horaCurta(m.iniciada_em)}` : "saída"}${m.km_saida !== null ? ` · ${km(m.km_saida)}` : ""}`} />
        {m.paradas.map((p) => (
          <Etapa
            key={p.id}
            marca={<Icone de={MapPin} />}
            titulo={p.local.nome}
            apoio={[p.servico.toLowerCase(), p.chegou_em && p.saiu_em ? `${horaCurta(p.chegou_em)} a ${horaCurta(p.saiu_em)}` : null, p.despesa ? (p.despesa.sem_nota ? "despesa lançada, sem nota" : "despesa lançada") : null].filter(Boolean).join(" · ")}
            valor={p.valor_pago_centavos ? dinheiro(p.valor_pago_centavos) : undefined}
          />
        ))}
        <Etapa marca="B" titulo={m.destino.nome} apoio={`chegando agora · ${horaCurta(agora.toISOString())}`} destaque />
      </section>

      {!aberta && <Aviso>Esta movimentação não espera chegada agora.</Aviso>}

      {aberta && (
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            confirmar.mutate();
          }}
          className="flex flex-col gap-4"
        >
          <TextField rotulo="Km na chegada" mono cheio inputMode="numeric" value={kmTexto} onChange={(e) => setKmTexto(e.target.value === "" ? "" : kmComPontos(e.target.value))} dica={m.km_saida !== null ? `não pode ser menor que ${kmComPontos(String(m.km_saida))}` : undefined} erro={erroDoKm} />

          {m.vistoria_rapida && (
            <>
              <div>
                <div className="wl-field__label">Combustível</div>
                <div role="group" aria-label="Combustível" className="mt-2 grid grid-cols-5 gap-[6px]">
                  {COMBUSTIVEIS_DA_CHEGADA.map((c) => (
                    <button key={c.valor} type="button" aria-pressed={combustivel === c.valor} onClick={() => setCombustivel(c.valor)} className={`h-[44px] rounded-[12px] text-caption ${combustivel === c.valor ? "bg-solid text-on-solid" : "bg-surface-sunken text-ink"}`}>
                      {c.rotulo}
                    </button>
                  ))}
                </div>
                {campo("combustivel") && <span className="text-caption text-critical-ink">{campo("combustivel")}</span>}
              </div>
              <div>
                <div className="wl-field__label">Fotos · {fotos.length} de 4</div>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  {POSICOES_DA_CHEGADA.map((p) => (
                    <Foto key={p.valor} posicao={p.valor} rotulo={p.rotulo} feita={fotos.some((f) => f.posicao === p.valor)} enviando={enviando === p.valor} aoEscolher={(posicao, arquivo) => foto.mutate({ posicao, arquivo })} />
                  ))}
                </div>
                {(campo("fotos") || erroDaFoto) && <span className="text-caption text-critical-ink">{erroDaFoto ?? campo("fotos")}</span>}
              </div>
            </>
          )}

          {m.transferencia && (
            <CampoSelecao
              rotulo="Recebido por"
              vazio="Escolha quem recebe"
              dica={`Usuário da ${m.destino.nome}.`}
              opcoes={(quemRecebe.data ?? []).map((p) => ({ valor: String(p.id), rotulo: p.nome }))}
              value={recebidoPor}
              onChange={(e) => setRecebidoPor(e.target.value)}
              erro={campo("recebido_por_id")}
            />
          )}

          {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}
          <p className="m-0 text-caption text-ink-muted">
            {m.transferencia
              ? `Ao confirmar, o ${placa(m.veiculo.placa)} passa a ser da ${m.destino.nome} e o km é atualizado. Ele volta a ficar disponível se os documentos estiverem em dia.`
              : "Ao confirmar, o km é atualizado e o veículo volta a ficar disponível se os documentos estiverem em dia."}
          </p>
          <Button type="submit" variante="solido" disabled={confirmar.isPending || kmTexto === ""}>
            Confirmar chegada
          </Button>
        </form>
      )}
    </div>
  );
}
