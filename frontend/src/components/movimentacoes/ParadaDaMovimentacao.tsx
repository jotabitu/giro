"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, MapPin } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Aviso } from "@/components/acesso/Aviso";
import { Button, Icone, TextField } from "@/design-system";
import { ErroApi, movimentacoes, type Movimentacao } from "@/lib/api";
import { TAMANHO_MAXIMO_DA_NOTA } from "@/lib/despesas";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro, horaCurta, km, placa } from "@/lib/formatos";
import { ROTA_DAS_MOVIMENTACOES } from "@/lib/movimentacoes";
import { centavosDoTexto } from "@/lib/veiculos";
import { Etapa } from "./RegistrarChegada";

// Referências: Movimentacao-Parada-Chegada-Mobile (Cheguei) e Movimentacao-Parada-Mobile / -Desktop (saída com o valor pago e a nota, MOV-04).
// O estado e o botão vêm da API: `acoes.chegar_parada` mostra o Cheguei, `acoes.sair_parada` mostra a saída. A tela não calcula nada.

function Percurso({ m, atual }: { m: Movimentacao; atual: number | null }) {
  return (
    <section aria-label="Percurso" className="rounded-lg bg-surface px-4 py-2">
      <Etapa marca={<Icone de={Check} />} titulo={m.filial_saida.nome} apoio={`${m.iniciada_em ? `saiu ${horaCurta(m.iniciada_em)}` : "saída"}${m.km_saida !== null ? ` · ${km(m.km_saida)}` : ""}`} />
      {m.paradas.map((p) => (
        <Etapa
          key={p.id}
          marca={p.saiu_em ? <Icone de={Check} /> : <Icone de={MapPin} />}
          titulo={p.local.nome}
          apoio={[p.servico.toLowerCase(), p.saiu_em ? "saiu" : p.chegou_em ? `chegou ${horaCurta(p.chegou_em)}` : p.id === atual ? "próxima parada" : null].filter(Boolean).join(" · ")}
          valor={p.valor_pago_centavos ? dinheiro(p.valor_pago_centavos) : undefined}
          destaque={p.id === atual}
        />
      ))}
      <Etapa marca="B" titulo={m.destino.nome} apoio={m.transferencia ? "destino · transferência" : "destino"} />
    </section>
  );
}

/** Cheguei na parada e saída da parada, numa tela só: a movimentação diz em qual das duas ela está. */
export function ParadaDaMovimentacao({ id }: { id: number }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const consulta = useQuery({ queryKey: ["movimentacoes", "detalhe", id], queryFn: () => movimentacoes.obter(id) });
  const m = consulta.data;
  const atual = m?.proxima_etapa?.startsWith("parada:") ? Number(m.proxima_etapa.slice("parada:".length)) : null;
  const parada = m?.paradas.find((p) => p.id === atual);

  const [valor, setValor] = useState("");
  const [nota, setNota] = useState<File | null>(null);
  const [erroDaNota, setErroDaNota] = useState<string | null>(null);
  const arquivo = useRef<HTMLInputElement>(null);

  const chegar = useMutation({
    mutationFn: () => movimentacoes.chegarNaParada(id, atual ?? 0),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["movimentacoes"] });
    },
  });
  const sair = useMutation({
    mutationFn: () => movimentacoes.sairDaParada(id, atual ?? 0, { valor_pago_centavos: centavosDoTexto(valor) ?? 0, nota: nota ?? undefined }),
    onSuccess: async () => {
      await cliente.invalidateQueries({ queryKey: ["movimentacoes"] });
      router.push(ROTA_DAS_MOVIMENTACOES);
    },
  });

  function escolherNota(f: File | null) {
    if (f && f.size > TAMANHO_MAXIMO_DA_NOTA) {
      setErroDaNota("A nota pode ter até 10 MB. Escolha um arquivo menor.");
      setNota(null);
      if (arquivo.current) arquivo.current.value = "";
      return;
    }
    setErroDaNota(null);
    setNota(f);
  }

  if (consulta.isPending)
    return (
      <p role="status" className="m-0 text-body text-ink-muted">
        Carregando a movimentação…
      </p>
    );
  if (consulta.isError || !m) return <Aviso tipo="erro">{mensagemDoErro(consulta.error)}</Aviso>;

  const chegando = m.acoes.chegar_parada && parada;
  const saindo = m.acoes.sair_parada && parada;
  const titulo = saindo ? "Sair da parada" : "Chegada na parada";
  const campoDoValor = sair.error instanceof ErroApi ? sair.error.campos?.valor_pago_centavos : undefined;
  const campoDaNota = sair.error instanceof ErroApi ? sair.error.campos?.nota : undefined;
  const erroDaAcao = chegar.error ?? sair.error;
  const erroGeral = erroDaAcao && !campoDoValor && !campoDaNota ? mensagemDoErro(erroDaAcao) : null;

  return (
    <div className="flex flex-col gap-4 md:mx-auto md:w-full md:max-w-[480px]">
      <header className="flex items-center gap-3">
        <Link href={ROTA_DAS_MOVIMENTACOES} aria-label="Voltar" className="wl-icon-btn wl-icon-btn--sm size-[44px]">
          <Icone de={ArrowLeft} />
        </Link>
        <div className="min-w-0">
          <h1 className="m-0 text-title">{titulo}</h1>
          <div className="text-caption text-ink-muted">
            <span className="wl-mono">{m.codigo}</span> · {m.veiculo.modelo} · <span className="wl-mono">{placa(m.veiculo.placa)}</span>
          </div>
        </div>
      </header>

      <Percurso m={m} atual={atual} />

      {!chegando && !saindo && <Aviso>Esta movimentação não espera uma parada agora.</Aviso>}

      {chegando && parada && (
        <section className="flex flex-col gap-3 rounded-lg bg-surface p-4">
          <div>
            <div className="text-heading">{parada.local.nome}</div>
            <div className="text-body text-ink-muted">{parada.servico}</div>
            {parada.valor_previsto_centavos !== undefined && <div className="text-caption text-ink-muted">Valor previsto {dinheiro(parada.valor_previsto_centavos)}</div>}
          </div>
          <p className="m-0 text-caption text-ink-muted">
            Toque em Cheguei quando estacionar no local. A hora fica registrada, e o veículo aparece em &quot;No local de apoio&quot; no quadro. O valor pago e a nota ficam para a saída.
          </p>
          {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}
          <Button variante="solido" disabled={chegar.isPending} onClick={() => chegar.mutate()}>
            Cheguei ao {parada.local.nome}
          </Button>
        </section>
      )}

      {saindo && parada && (
        <form
          className="flex flex-col gap-3 rounded-lg bg-surface p-4"
          onSubmit={(e) => {
            e.preventDefault();
            sair.mutate();
          }}
        >
          <TextField
            rotulo="Valor pago"
            mono
            cheio
            inputMode="decimal"
            placeholder="0,00"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            dica={parada.valor_previsto_centavos !== undefined ? `Confira com o recibo. Previsto na criação: ${dinheiro(parada.valor_previsto_centavos)}.` : "Confira com o recibo."}
            erro={campoDoValor ?? (valor !== "" && centavosDoTexto(valor) === null ? "Informe um valor, como 35,00." : undefined)}
          />
          <div className="flex flex-col gap-1">
            <span className="wl-field__label">Nota</span>
            <input ref={arquivo} type="file" accept="image/*,application/pdf" aria-label="Nota" onChange={(e) => escolherNota(e.target.files?.[0] ?? null)} className="min-h-[44px] text-body" />
            <span className="text-caption text-ink-muted">Foto ou PDF, até 10 MB. Sem a nota, a despesa é gerada e fica marcada &quot;sem nota&quot;; você anexa depois em Despesas.</span>
            {(erroDaNota || campoDaNota) && (
              <span role="alert" className="text-caption text-critical-ink">
                {erroDaNota ?? campoDaNota}
              </span>
            )}
          </div>
          <p className="m-0 text-caption text-ink-muted">
            Valor acima de zero lança uma despesa de {placa(m.veiculo.placa)}, com vencimento hoje. Acima do limite da empresa, ela espera aprovação. Valor zero não lança despesa.
          </p>
          {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}
          <div className="flex gap-2">
            <Link href={ROTA_DAS_MOVIMENTACOES} className="wl-btn">
              Cancelar
            </Link>
            <Button type="submit" variante="solido" disabled={sair.isPending || valor === "" || centavosDoTexto(valor) === null}>
              Confirmar saída
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
