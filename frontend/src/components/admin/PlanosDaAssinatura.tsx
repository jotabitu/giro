"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialogo, StatusBadge } from "@/design-system";
import { assinatura as api, ErroApi, type PlanoParaMudar, type SimulacaoDeMudanca } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCurta, dinheiro } from "@/lib/formatos";

// "Mudar de plano" e "Comparar planos" abrem a mesma lista (GET /api/assinatura/planos/). Quem pode escolher é `acoes.mudar_plano`;
// o que cabe, o que excede, o valor e a data em que vale vêm da API (PLT-04). A tela só mostra e confirma.

const limite = (n: number | null, singular: string, plural: string) => (n === null ? `${plural} sem limite` : `até ${n} ${n === 1 ? singular : plural}`);

/** O que impede a mudança, nas palavras da API (`excede`): "86 de 30 veículos", "5 de 3 usuários" e o que está aberto nos módulos. */
export function textoDoQueExcede(p: Pick<PlanoParaMudar, "excede">): string[] {
  const e = p.excede;
  const linhas: string[] = [];
  if (e.veiculos) linhas.push(`${e.veiculos.usado} de ${e.veiculos.limite} veículos`);
  if (e.filiais) linhas.push(`${e.filiais.usado} de ${e.filiais.limite} filiais`);
  if (e.usuarios) linhas.push(`${e.usuarios.usado} de ${e.usuarios.limite} usuários`);
  if (e.abertos_texto) linhas.push(`Resolva antes: ${e.abertos_texto}`);
  return linhas;
}

function CartaoDoPlano({ p, ciclo, podeEscolher, ocupado, aoEscolher }: { p: PlanoParaMudar; ciclo: string; podeEscolher: boolean; ocupado: boolean; aoEscolher: () => void }) {
  const preco = ciclo === "anual" ? `${dinheiro(p.preco_anual_centavos)} por ano` : `${dinheiro(p.preco_mensal_centavos)} por mês`;
  const impedimentos = textoDoQueExcede(p);
  return (
    <article className={`flex flex-col gap-3 rounded-lg p-4 ${p.atual ? "bg-surface-sunken ring-2 ring-line-strong" : "border border-line bg-surface"}`} aria-label={`Plano ${p.nome}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-heading">{p.nome}</h3>
        {p.atual && (
          <StatusBadge tom="marca" compacto>
            Seu plano
          </StatusBadge>
        )}
      </div>
      <div className="text-title">{preco}</div>
      <div className="text-caption text-ink-muted">
        {[limite(p.limite_veiculos, "veículo", "veículos"), limite(p.limite_filiais, "filial", "filiais"), limite(p.limite_usuarios, "usuário", "usuários")].join(" · ")}
      </div>
      <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-body">
        {p.itens.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
      {!p.atual && !p.cabe && (
        <div role="note" className="rounded-md bg-warning-soft p-3 text-caption text-warning-ink">
          <strong className="block font-medium">Seu uso não cabe neste plano hoje.</strong>
          {impedimentos.map((l) => (
            <span key={l} className="block">
              {l}
            </span>
          ))}
        </div>
      )}
      {p.mudanca && podeEscolher && (
        <div className="mt-auto">
          <Button variante={p.mudanca === "upgrade" ? "solido" : "quieto"} disabled={!p.cabe || ocupado} onClick={aoEscolher}>
            {p.mudanca === "upgrade" ? `Mudar para o ${p.nome}` : `Descer para o ${p.nome}`}
          </Button>
        </div>
      )}
    </article>
  );
}

/** Lista de planos, simulação e confirmação da mudança. Sem `podeMudar` vira só a comparação. */
export function PlanosDaAssinatura({ podeMudar, aoFechar, aoConcluir }: { podeMudar: boolean; aoFechar: () => void; aoConcluir: (mensagem: string) => void }) {
  const cliente = useQueryClient();
  const planos = useQuery({ queryKey: ["assinatura", "planos"], queryFn: () => api.planos() });
  const [escolhido, setEscolhido] = useState<{ plano: PlanoParaMudar; simulacao: SimulacaoDeMudanca } | null>(null);
  const ciclo = planos.data?.ciclo_atual ?? "mensal";

  const simular = useMutation({
    mutationFn: (p: PlanoParaMudar) => api.simularMudanca({ plano_id: p.id, ciclo }).then((simulacao) => ({ plano: p, simulacao })),
    onSuccess: setEscolhido,
  });
  const confirmar = useMutation({
    mutationFn: () => {
      if (!escolhido) throw new Error("Escolha um plano.");
      return api.mudarPlano({ plano_id: escolhido.plano.id, ciclo, confirmar_valor_centavos: escolhido.simulacao.diferenca_centavos });
    },
    onSuccess: async () => {
      await Promise.all([cliente.invalidateQueries({ queryKey: ["assinatura"] }), cliente.invalidateQueries({ queryKey: ["usuarios"] }), cliente.invalidateQueries({ queryKey: ["contadores"] })]);
      aoConcluir(escolhido?.simulacao.mensagem ?? "Plano alterado.");
      aoFechar();
    },
  });

  const valorMudou = confirmar.error instanceof ErroApi && confirmar.error.codigo === "valor_mudou";

  if (escolhido) {
    const s = escolhido.simulacao;
    return (
      <Dialogo
        aberto
        aoFechar={aoFechar}
        fecharAoClicarFora={false}
        titulo={s.tipo === "upgrade" ? `Mudar para o ${escolhido.plano.nome}` : `Descer para o ${escolhido.plano.nome}`}
        descricao={s.mensagem}
        acoes={
          <>
            <Button
              variante="quieto"
              onClick={() => {
                confirmar.reset();
                setEscolhido(null);
              }}
            >
              Voltar
            </Button>
            {valorMudou ? (
              <Button variante="solido" disabled={simular.isPending} onClick={() => simular.mutate(escolhido.plano, { onSuccess: () => confirmar.reset() })}>
                Ver o novo valor
              </Button>
            ) : (
              <Button variante="solido" disabled={confirmar.isPending} onClick={() => confirmar.mutate()}>
                {confirmar.isPending ? "Confirmando…" : "Confirmar mudança"}
              </Button>
            )}
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <dl className="m-0 rounded-md bg-surface-sunken px-4 py-1">
            <Linha rotulo="Vale a partir de" valor={dataCurta(s.vale_em)} />
            <Linha rotulo="Preço do plano" valor={`${dinheiro(s.preco_novo_centavos)} por ${ciclo === "anual" ? "ano" : "mês"}`} />
            {s.fatura_diferenca && <Linha rotulo="Diferença agora" valor={dinheiro(s.fatura_diferenca.valor_centavos)} />}
            {s.proxima_fatura && <Linha rotulo="Próxima fatura" valor={`${dinheiro(s.proxima_fatura.valor_centavos)} em ${dataCurta(s.proxima_fatura.vencimento)}`} />}
          </dl>
          {s.fatura_diferenca && (
            <p className="text-caption text-ink-muted">
              {s.fatura_diferenca.descricao}, vence em {dataCurta(s.fatura_diferenca.vencimento)}.
            </p>
          )}
          {confirmar.isError && (
            <p role="alert" className="rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
              {mensagemDoErro(confirmar.error)}
            </p>
          )}
        </div>
      </Dialogo>
    );
  }

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={podeMudar ? "Mudar de plano" : "Comparar planos"}
      descricao={podeMudar ? "Escolha o plano. Antes de confirmar, mostramos o que muda e quanto custa." : "O que cada plano inclui."}
      tamanho="medio"
      acoes={
        <Button variante="quieto" onClick={aoFechar}>
          Fechar
        </Button>
      }
    >
      {planos.isPending && (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando os planos…
        </p>
      )}
      {planos.isError && (
        <p role="alert" className="text-body">
          {mensagemDoErro(planos.error)}
        </p>
      )}
      {simular.isError && (
        <p role="alert" className="mb-3 rounded-md bg-critical-soft p-3 text-caption text-critical-ink">
          {mensagemDoErro(simular.error)}
        </p>
      )}
      <div className="grid gap-3 md:grid-cols-3">
        {planos.data?.resultados.map((p) => (
          <CartaoDoPlano key={p.id} p={p} ciclo={ciclo} podeEscolher={podeMudar} ocupado={simular.isPending} aoEscolher={() => simular.mutate(p)} />
        ))}
      </div>
    </Dialogo>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-2 last:border-b-0">
      <dt className="text-caption text-ink-muted">{rotulo}</dt>
      <dd className="m-0 text-body font-medium">{valor}</dd>
    </div>
  );
}
