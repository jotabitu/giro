"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bike, Car, ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { Icone, Panel, TextField } from "@/design-system";
import { ErroApi, veiculos, type CategoriaVeiculo, type VeiculoDetalhe } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { km, placa as placaComHifen } from "@/lib/formatos";
import { esquemaVeiculo, paraCorpoEdicao, valoresDoVeiculo, type ValoresVeiculo } from "@/lib/veiculos";
import { Preco, Selecao } from "./NovoVeiculoForm";

// Referência: Veiculo-Novo-Desktop|Mobile com os dados preenchidos (T-243; a edição não tem tela própria).
// PATCH /api/veiculos/{id}/ (VEI-01): placa, chassi, km e filial aparecem só para leitura; a API valida e o erro volta no campo.

type Nome = FieldPath<ValoresVeiculo>;
const CAMPO_DA_API: Record<string, Nome> = { valor_compra_centavos: "valor_compra" };
const CAMPOS_EDITAVEIS: Nome[] = ["marca", "modelo", "ano_fabricacao", "ano_modelo", "renavam", "cor", "capacidade_tanque_litros", "categoria_id", "data_compra", "valor_compra"];

function Formulario({ ficha }: { ficha: VeiculoDetalhe }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const enviando = useRef(false);

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors },
  } = useForm<ValoresVeiculo>({ resolver: zodResolver(esquemaVeiculo), defaultValues: valoresDoVeiculo(ficha) });
  const v = watch();

  const categorias = useQuery({
    queryKey: ["categorias", { filial: String(ficha.filial.id), tipo: ficha.tipo_veiculo }],
    queryFn: () => veiculos.categorias({ filial: ficha.filial.id, tipo_veiculo: ficha.tipo_veiculo }),
  });
  // A categoria de hoje fica na lista mesmo que a consulta não a traga (sem preço vigente, por exemplo).
  const lista: CategoriaVeiculo[] = categorias.data ?? [];
  const opcoes = lista.map((c) => ({ valor: String(c.id), rotulo: c.nome }));
  if (!opcoes.some((o) => o.valor === String(ficha.categoria.id))) opcoes.unshift({ valor: String(ficha.categoria.id), rotulo: ficha.categoria.nome });
  const categoria = lista.find((c) => String(c.id) === v.categoria_id);

  const salvar = useMutation({ mutationFn: (valores: ValoresVeiculo) => veiculos.atualizar(ficha.id, paraCorpoEdicao(valores)) });
  const erro = (nome: Nome) => errors[nome]?.message;

  // Dois cliques antes do primeiro render não mandam duas edições.
  const enviar = handleSubmit(async (valores) => {
    if (enviando.current) return;
    enviando.current = true;
    setErroGeral(null);
    try {
      await salvar.mutateAsync(valores);
      void cliente.invalidateQueries({ queryKey: ["veiculo", ficha.id] });
      void cliente.invalidateQueries({ queryKey: ["veiculos"] });
      router.push(`/veiculos/${ficha.id}`);
    } catch (e) {
      if (e instanceof ErroApi && e.campos) {
        const sobra: string[] = [];
        for (const [campo, mensagem] of Object.entries(e.campos)) {
          const nome = CAMPO_DA_API[campo] ?? (campo as Nome);
          if (CAMPOS_EDITAVEIS.includes(nome)) setError(nome, { message: mensagem });
          else sobra.push(mensagem);
        }
        setErroGeral([e.message, ...sobra].join(". "));
      } else {
        setErroGeral(mensagemDoErro(e));
      }
    } finally {
      enviando.current = false;
    }
  });

  const titulo = [v.marca, v.modelo].filter(Boolean).join(" ") || "Veículo";
  const resumo = [placaComHifen(ficha.placa), v.ano_modelo, km(ficha.km_atual)].filter(Boolean).join(" · ");
  const ocupado = salvar.isPending;

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <Link href={`/veiculos/${ficha.id}`} aria-label="Voltar para a ficha" className="wl-icon-btn md:hidden">
          <Icone de={ChevronLeft} />
        </Link>
        <div className="min-w-0 flex-1">
          <nav aria-label="Caminho" className="hidden text-body text-ink-muted md:block">
            <Link href="/veiculos" className="text-ink">
              Veículos
            </Link>{" "}
            /{" "}
            <Link href={`/veiculos/${ficha.id}`} className="text-ink">
              {placaComHifen(ficha.placa)}
            </Link>{" "}
            / Editar
          </nav>
          <h1 className="text-title md:mt-1 md:text-display">Editar veículo</h1>
        </div>
      </header>

      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {erroGeral}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Panel titulo="Identificação">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono rotulo="Placa" value={placaComHifen(ficha.placa)} readOnly dica="Placa e chassi não mudam aqui. Para corrigir um erro de digitação, fale com o administrador." />
              <TextField cheio rotulo="Marca" autoComplete="off" erro={erro("marca")} {...register("marca")} />
              <TextField cheio rotulo="Modelo" autoComplete="off" erro={erro("modelo")} {...register("modelo")} />
              <div className="grid grid-cols-2 gap-3">
                <TextField cheio mono rotulo="Ano de fabricação" inputMode="numeric" maxLength={4} erro={erro("ano_fabricacao")} {...register("ano_fabricacao")} />
                <TextField cheio mono rotulo="Ano do modelo" inputMode="numeric" maxLength={4} erro={erro("ano_modelo")} {...register("ano_modelo")} />
              </div>
              <TextField cheio mono rotulo="Chassi" value={ficha.chassi} readOnly />
              <TextField cheio mono rotulo="Renavam" inputMode="numeric" erro={erro("renavam")} {...register("renavam")} />
              <TextField cheio rotulo="Cor" erro={erro("cor")} {...register("cor")} />
              <TextField cheio mono rotulo="Km atual" value={km(ficha.km_atual)} readOnly dica="O km sobe pela leitura ou pela vistoria e nunca diminui" />
              <TextField cheio mono rotulo="Capacidade do tanque (litros)" inputMode="decimal" dica="Opcional. Sem ela, o combustível da devolução é informado à mão" erro={erro("capacidade_tanque_litros")} {...register("capacidade_tanque_litros")} />
            </div>
          </Panel>

          <Panel titulo="Uso na frota">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio rotulo="Filial" value={ficha.filial.nome} readOnly dica="A filial só muda por transferência" />
              <Selecao id="categoria" rotulo="Categoria de preço" vazio="Escolha" opcoes={opcoes} dica="Vale para as locações novas; as em andamento mantêm o preço" erro={erro("categoria_id")} {...register("categoria_id")} />
            </div>
            {categoria && (
              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Preco rotulo="Diária" centavos={categoria.preco_vigente.diaria_centavos} />
                <Preco rotulo="Semanal" centavos={categoria.preco_vigente.semanal_centavos} />
                <Preco rotulo="Mensal" centavos={categoria.preco_vigente.mensal_centavos} />
                <Preco rotulo="Caução" centavos={categoria.preco_vigente.caucao_centavos} />
              </div>
            )}
          </Panel>

          <Panel titulo="Compra e valores">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono type="date" rotulo="Data da compra" erro={erro("data_compra")} {...register("data_compra")} />
              <TextField cheio rotulo="Valor de compra" inputMode="decimal" placeholder="R$ 0,00" dica="Base da rentabilidade do veículo" erro={erro("valor_compra")} {...register("valor_compra")} />
            </div>
          </Panel>
        </div>

        <aside className="flex flex-col gap-6">
          <section className="wl-panel overflow-hidden !p-0">
            <div className="grid h-[140px] place-items-center bg-surface-sunken text-ink-muted">
              <Icone de={ficha.tipo_veiculo === "moto" ? Bike : Car} />
            </div>
            <div className="p-5">
              <div className="text-heading font-semibold">{titulo}</div>
              <div className="wl-mono text-ink-muted">{resumo}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="wl-badge wl-badge--sm">{opcoes.find((o) => o.valor === v.categoria_id)?.rotulo ?? ficha.categoria.nome}</span>
                <span className="wl-badge wl-badge--sm">{ficha.filial.nome}</span>
              </div>
            </div>
          </section>

          <section className="wl-panel flex flex-col gap-3">
            <button type="submit" disabled={ocupado} className="wl-btn wl-btn--solid">
              {ocupado ? "Salvando…" : "Salvar alterações"}
            </button>
            <Link href={`/veiculos/${ficha.id}`} className="wl-btn wl-btn--quiet">
              Cancelar
            </Link>
          </section>
        </aside>
      </div>
    </form>
  );
}

/** Editar veículo: abre a ficha da API com os campos preenchidos e grava com PATCH. Só quem a API marca em `acoes.editar` edita. */
export function EditarVeiculo({ id }: { id: number }) {
  const ficha = useQuery({ queryKey: ["veiculo", id], queryFn: () => veiculos.obter(id), retry: false });
  if (ficha.isError)
    return (
      <div className="flex flex-col gap-4">
        <Link href="/veiculos" className="text-body text-ink-muted">
          Veículos
        </Link>
        <p role="alert" className="wl-panel text-body">
          {mensagemDoErro(ficha.error)}
        </p>
      </div>
    );
  if (!ficha.data)
    return (
      <p className="wl-panel text-body text-ink-muted" aria-busy="true">
        Carregando o veículo…
      </p>
    );
  if (!ficha.data.acoes.editar)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-title md:text-display">Editar veículo</h1>
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Seu perfil não edita veículos.{" "}
          <Link href={`/veiculos/${id}`} className="underline">
            Voltar para a ficha
          </Link>
        </p>
      </div>
    );
  return <Formulario ficha={ficha.data} />;
}
