"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bike, Car, ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type SelectHTMLAttributes } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { Icone, Panel, SegmentedControl, TextField } from "@/design-system";
import { ErroApi, veiculos, type CategoriaVeiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dinheiro, km, placa as placaComHifen } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { esquemaVeiculo, paraCorpoVeiculo, VALORES_INICIAIS_VEICULO, type ValoresVeiculo } from "@/lib/veiculos";

type Nome = FieldPath<ValoresVeiculo>;

/** Campo da API que não tem campo próprio na tela vira o campo mais próximo. */
const CAMPO_DA_API: Record<string, Nome> = { valor_compra_centavos: "valor_compra" };

type SelecaoProps = SelectHTMLAttributes<HTMLSelectElement> & { rotulo: string; erro?: string; dica?: string; opcoes: { valor: string; rotulo: string }[]; vazio: string };

export function Selecao({ rotulo, erro, dica, opcoes, vazio, id, ...resto }: SelecaoProps) {
  const apoio = erro ?? dica;
  return (
    <div className={`wl-field wl-field--cheio ${erro ? "wl-field--error" : ""}`}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <select id={id} className="wl-input" aria-invalid={erro ? true : undefined} {...resto}>
        <option value="">{vazio}</option>
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </div>
  );
}

export function Preco({ rotulo, centavos }: { rotulo: string; centavos: number }) {
  return (
    <div className="rounded-md bg-surface-sunken px-4 py-3">
      <span className="block text-caption text-ink-muted">{rotulo}</span>
      <b className="font-semibold">{dinheiro(centavos)}</b>
    </div>
  );
}

/** Cadastrar veículo (Veiculo-Novo-Desktop|Mobile): POST /api/veiculos/ (VEI-01, PLT-03). A API valida; o erro volta no campo. */
export function NovoVeiculoForm() {
  const router = useRouter();
  const cliente = useQueryClient();
  const { eu } = useSessao();
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [existente, setExistente] = useState<{ id: number } | null>(null);
  const [salvo, setSalvo] = useState<string | null>(null);

  const filiaisDaPessoa = eu.filiais;
  const valoresIniciais: ValoresVeiculo = { ...VALORES_INICIAIS_VEICULO, filial_id: filiaisDaPessoa.length === 1 ? String(filiaisDaPessoa[0]!.id) : "" };
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    reset,
    formState: { errors },
  } = useForm<ValoresVeiculo>({ resolver: zodResolver(esquemaVeiculo), defaultValues: valoresIniciais });
  const v = watch();

  const categorias = useQuery({
    queryKey: ["categorias", { filial: v.filial_id, tipo: v.tipo }],
    queryFn: () => veiculos.categorias({ filial: v.filial_id ? Number(v.filial_id) : undefined, tipo_veiculo: v.tipo }),
  });
  const lista: CategoriaVeiculo[] = categorias.data ?? [];
  const categoria = lista.find((c) => String(c.id) === v.categoria_id);

  // Trocar tipo ou filial pode tirar a categoria escolhida da lista.
  useEffect(() => {
    if (categorias.data && v.categoria_id && !categorias.data.some((c) => String(c.id) === v.categoria_id)) setValue("categoria_id", "");
  }, [categorias.data, v.categoria_id, setValue]);

  const salvar = useMutation({ mutationFn: (valores: ValoresVeiculo) => veiculos.criar(paraCorpoVeiculo(valores)) });

  const erro = (nome: Nome) => errors[nome]?.message;

  async function enviar(valores: ValoresVeiculo, outro: boolean) {
    setErroGeral(null);
    setExistente(null);
    setSalvo(null);
    try {
      const criado = await salvar.mutateAsync(valores);
      void cliente.invalidateQueries({ queryKey: ["veiculos"] });
      if (outro) {
        reset({ ...valoresIniciais, tipo: valores.tipo, filial_id: valores.filial_id });
        setSalvo(`${criado.marca} ${criado.modelo}, placa ${placaComHifen(criado.placa)}, entrou na frota.`);
        window.scrollTo?.({ top: 0 });
      } else {
        router.push(`/veiculos/${criado.id}`);
      }
    } catch (e) {
      if (e instanceof ErroApi && e.status === 409 && e.codigo === "VEI-01") {
        const campo = e.detalhes?.campo === "chassi" ? "chassi" : "placa";
        const id = Number(e.detalhes?.veiculo_id);
        setExistente(id ? { id } : null);
        setError(campo, { message: e.message });
      } else if (e instanceof ErroApi && e.campos) {
        const sobra: string[] = [];
        for (const [campo, mensagem] of Object.entries(e.campos)) {
          const nome = CAMPO_DA_API[campo] ?? campo;
          if (nome in VALORES_INICIAIS_VEICULO) setError(nome as Nome, { message: mensagem });
          else sobra.push(mensagem);
        }
        setErroGeral([e.message, ...sobra].join(". "));
      } else {
        setErroGeral(mensagemDoErro(e));
      }
    }
  }

  const salvarEFicha = handleSubmit((valores) => enviar(valores, false));
  const salvarEOutro = handleSubmit((valores) => enviar(valores, true));
  const ocupado = salvar.isPending;

  if (eu.pode.veiculos !== "editar") {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-title md:text-display">Cadastrar veículo</h1>
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Seu perfil não cadastra veículos. Fale com o gerente ou o administrador.{" "}
          <Link href="/veiculos" className="underline">
            Voltar para a Frota
          </Link>
        </p>
      </div>
    );
  }

  const filiais = filiaisDaPessoa.map((f) => ({ valor: String(f.id), rotulo: f.nome }));
  const nomeDaFilial = filiaisDaPessoa.find((f) => String(f.id) === v.filial_id)?.nome;
  const titulo = [v.marca, v.modelo].filter(Boolean).join(" ") || "Novo veículo";
  const resumo = [v.placa && placaComHifen(v.placa.replace(/[\s-]/g, "").toUpperCase()), v.ano_modelo, v.km_atual && /^\d+$/.test(v.km_atual) ? km(Number(v.km_atual)) : ""].filter(Boolean).join(" · ");

  return (
    <form onSubmit={salvarEFicha} noValidate className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <Link href="/veiculos" aria-label="Voltar para a Frota" className="wl-icon-btn md:hidden">
          <Icone de={ChevronLeft} />
        </Link>
        <div className="min-w-0 flex-1 md:flex-none">
          <nav aria-label="Caminho" className="hidden text-body text-ink-muted md:block">
            <Link href="/veiculos" className="text-ink">
              Veículos
            </Link>{" "}
            / Cadastrar
          </nav>
          <h1 className="text-title md:mt-1 md:text-display">Cadastrar veículo</h1>
        </div>
        <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto">
          <button type="button" disabled title="Em breve" className="wl-btn hidden md:inline-flex">
            Importar planilha
          </button>
          <SegmentedControl
            rotulo="Tipo de veículo"
            valor={v.tipo}
            aoMudar={(t) => setValue("tipo", t, { shouldDirty: true })}
            opcoes={[
              { valor: "moto", rotulo: "Moto" },
              { valor: "carro", rotulo: "Carro" },
            ]}
          />
        </div>
      </header>

      {salvo && (
        <p role="status" className="rounded-lg bg-success-soft p-4 text-body text-success-ink">
          {salvo} Cadastre o próximo.
        </p>
      )}
      {erroGeral && (
        <p role="alert" className="rounded-lg bg-critical-soft p-4 text-body text-critical-ink">
          {erroGeral}
        </p>
      )}
      {existente && (
        <p role="alert" className="rounded-lg bg-warning-soft p-4 text-body text-warning-ink">
          Este veículo já está na frota.{" "}
          <Link href={`/veiculos/${existente.id}`} className="underline">
            Abrir o cadastro existente
          </Link>
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-6">
          <section className="wl-panel flex flex-wrap items-center gap-4">
            <div className="min-w-0 flex-1 basis-64">
              <div className="text-body font-semibold">Preencher pelo documento</div>
              <p className="text-body text-ink-muted">A leitura do CRLV-e ainda não está disponível. Preencha os dados abaixo.</p>
            </div>
            <button type="button" disabled className="wl-btn">
              Enviar CRLV-e
            </button>
          </section>

          <Panel titulo="Identificação">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono rotulo="Placa" autoComplete="off" autoCapitalize="characters" maxLength={8} dica="Padrão antigo ou Mercosul" erro={erro("placa")} {...register("placa")} />
              <TextField cheio rotulo="Marca" autoComplete="off" erro={erro("marca")} {...register("marca")} />
              <TextField cheio rotulo="Modelo" autoComplete="off" erro={erro("modelo")} {...register("modelo")} />
              <div className="grid grid-cols-2 gap-3">
                <TextField cheio mono rotulo="Ano de fabricação" inputMode="numeric" maxLength={4} erro={erro("ano_fabricacao")} {...register("ano_fabricacao")} />
                <TextField cheio mono rotulo="Ano do modelo" inputMode="numeric" maxLength={4} erro={erro("ano_modelo")} {...register("ano_modelo")} />
              </div>
              <TextField cheio mono rotulo="Chassi" autoComplete="off" autoCapitalize="characters" maxLength={17} dica="17 caracteres" erro={erro("chassi")} {...register("chassi")} />
              <TextField cheio mono rotulo="Renavam" inputMode="numeric" erro={erro("renavam")} {...register("renavam")} />
              <TextField cheio rotulo="Cor" erro={erro("cor")} {...register("cor")} />
              <TextField cheio mono rotulo="Km atual" inputMode="numeric" dica="Nunca diminui depois de salvo" erro={erro("km_atual")} {...register("km_atual")} />
              <TextField cheio mono rotulo="Capacidade do tanque (litros)" inputMode="decimal" dica="Opcional. Sem ela, o combustível da devolução é informado à mão" erro={erro("capacidade_tanque_litros")} {...register("capacidade_tanque_litros")} />
            </div>
          </Panel>

          <Panel titulo="Uso na frota">
            <div className="grid gap-4 md:grid-cols-2">
              <Selecao id="filial" rotulo="Filial" vazio="Escolha" opcoes={filiais} erro={erro("filial_id")} {...register("filial_id")} />
              <Selecao
                id="categoria"
                rotulo="Categoria de preço"
                vazio={categorias.isPending ? "Carregando…" : "Escolha"}
                opcoes={lista.map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
                erro={erro("categoria_id")}
                {...register("categoria_id")}
              />
            </div>
            {categoria && (
              <>
                <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Preco rotulo="Diária" centavos={categoria.preco_vigente.diaria_centavos} />
                  <Preco rotulo="Semanal" centavos={categoria.preco_vigente.semanal_centavos} />
                  <Preco rotulo="Mensal" centavos={categoria.preco_vigente.mensal_centavos} />
                  <Preco rotulo="Caução" centavos={categoria.preco_vigente.caucao_centavos} />
                </div>
                <p className="mt-3 text-body text-ink-muted">
                  Preços da categoria {categoria.nome}. Para mudar, edite a tabela de preços.
                </p>
              </>
            )}
          </Panel>

          <Panel titulo="Compra e valores">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField cheio mono type="date" rotulo="Data da compra" erro={erro("data_compra")} {...register("data_compra")} />
              <TextField cheio rotulo="Valor de compra" inputMode="decimal" placeholder="R$ 0,00" dica="Base da rentabilidade do veículo" erro={erro("valor_compra")} {...register("valor_compra")} />
              <TextField cheio rotulo="Referência FIPE" disabled dica="A consulta FIPE ainda não está disponível" />
            </div>
          </Panel>

          <Panel titulo="Documentos e fotos">
            <p className="text-body text-ink-muted">
              Depois de salvar, envie o CRLV-e, o seguro e as fotos na ficha do veículo. Veículo com CRLV ou seguro vencido não pode ser desbloqueado para locação.
            </p>
          </Panel>
        </div>

        <aside className="flex flex-col gap-6">
          <section className="wl-panel overflow-hidden !p-0">
            <div className="grid h-[140px] place-items-center bg-surface-sunken text-ink-muted">
              <Icone de={v.tipo === "moto" ? Bike : Car} />
            </div>
            <div className="p-5">
              <div className="text-heading font-semibold">{titulo}</div>
              {resumo && <div className="wl-mono text-ink-muted">{resumo}</div>}
              <div className="mt-3 flex flex-wrap gap-2">
                {categoria && <span className="wl-badge wl-badge--sm">{categoria.nome}</span>}
                {nomeDaFilial && <span className="wl-badge wl-badge--sm">{nomeDaFilial}</span>}
              </div>
            </div>
          </section>

          <section className="wl-panel">
            <p className="text-body text-ink-muted">O veículo entra na frota como Disponível. Placa e chassi não podem repetir, nem de veículo vendido ou baixado.</p>
          </section>

          <section className="wl-panel flex flex-col gap-3">
            <button type="submit" disabled={ocupado} className="wl-btn wl-btn--solid">
              Salvar veículo
            </button>
            <button type="button" disabled={ocupado} onClick={() => void salvarEOutro()} className="wl-btn wl-btn--quiet">
              Salvar e cadastrar outro
            </button>
            <Link href="/veiculos" className="wl-btn wl-btn--quiet">
              Cancelar
            </Link>
          </section>
        </aside>
      </div>
    </form>
  );
}
