"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bike, Car, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Aviso, Button, Escolha, Icone, StatusBadge, TextField, Valores } from "@/design-system";
import { EscolherCliente, EscolherVeiculo } from "@/components/locacoes/SeletoresDaLocacao";
import { vendas, veiculos, type FormaDaVenda, type PropostaDaVenda, type Veiculo, type VendaDetalhe } from "@/lib/api";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { celular, dinheiro, km, mascaraCelular, placa, soDigitos } from "@/lib/formatos";
import { reaisDoCentavos } from "@/lib/precos";
import { centavosDoCampo } from "@/lib/precos-veiculo";
import { atualizarVendas, campoDoPct, dataDaProposta, FORMAS, linhasDoResumo, linkDoWhatsApp, pctDoCampo, pctTexto, tomDaVenda } from "@/lib/vendas";
import { PerderVenda, RespostaDoCliente } from "./DialogosDaVenda";

// Referência: docs/telas/html/Venda-Desktop.dc.html e Venda-Mobile.dc.html (T-503; VEN-01 a VEN-04, VEN-10, VEN-13 a VEN-19).
// Fase 1a da T-502: o passo 1 · Negócio (simular, criar, editar, enviar, pedir aprovação, registrar resposta, marcar como
// perdida). Preço final, desconto em reais, saldo, parcelas, comissão e "precisa do gerente" vêm do `simular`; o que a
// pessoa pode fazer vem em `acoes`. Os passos 2 · Documentos e 3 · Assinatura, o contrato e a entrada entram com a 1b;
// o e-mail, o PDF e o "Copiar link" da proposta, com a 1c. A troca (VEN-05) é da fase 2 e não aparece.

/** VEN-15: o que acontece depois da assinatura, como a tela de referência diz. */
const NOTA_DA_CONCLUSAO = "Depois de assinada e com a entrada paga, a venda gera as parcelas em Contas a receber, lança a comissão e tira o veículo da frota de locação.";
const AJUDA_DO_INTERESSADO = "O CPF é pedido para enviar a proposta, e o cadastro completo, na etapa Documentos.";

type Formulario = { forma: FormaDaVenda | ""; desconto: string; entrada: string; parcelas: string };
type Cliente = { id: number; nome: string; detalhe?: string };
type Acao = "interessado" | "enviar" | "pedir_aprovacao" | "salvar";

function useAtraso<T>(valor: T, ms = 300): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}

const formaValida = (f: string | undefined): FormaDaVenda | "" => (f === "a_vista" || f === "entrada_parcelas" ? f : "");

export function formularioDaVenda(v?: VendaDetalhe): Formulario {
  const c = v?.calculo;
  const forma = formaValida(c?.forma ?? v?.forma);
  return {
    forma,
    desconto: campoDoPct(c?.desconto_pct),
    entrada: forma === "entrada_parcelas" && c?.entrada_centavos != null ? reaisDoCentavos(c.entrada_centavos) : "",
    parcelas: forma === "entrada_parcelas" && c?.num_parcelas ? String(c.num_parcelas) : "",
  };
}

/** O que se digitou, no formato da API. Nenhuma conta: entrada em centavos e desconto com 2 casas. */
export function propostaDoFormulario(f: Formulario): PropostaDaVenda {
  const p: PropostaDaVenda = { forma: f.forma, desconto_pct: pctDoCampo(f.desconto) };
  if (f.forma === "entrada_parcelas") {
    p.entrada_centavos = centavosDoCampo(f.entrada) ?? null;
    const n = Number(soDigitos(f.parcelas));
    p.num_parcelas = n > 0 ? n : null;
  }
  return p;
}

function Cartao({ icone, titulo, detalhe, acao }: { icone: typeof User; titulo: ReactNode; detalhe?: ReactNode; acao?: ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-surface-sunken p-3">
      <span aria-hidden="true" className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface text-ink-muted">
        <Icone de={icone} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-body font-medium">{titulo}</div>
        {detalhe && <div className="text-caption text-ink-muted">{detalhe}</div>}
      </div>
      {acao}
    </div>
  );
}

/** Os três passos da tela. Só o 1 · Negócio existe nesta fase; os outros chegam com a 1b. */
function Passos() {
  const passos = ["1 · Negócio", "2 · Documentos", "3 · Assinatura"];
  return (
    <ol className="m-0 flex list-none flex-wrap gap-2 p-0" aria-label="Etapas da venda">
      {passos.map((p, i) => (
        <li key={p} aria-current={i === 0 ? "step" : undefined} className={`wl-badge ${i === 0 ? "wl-badge--solid" : "wl-badge--surface"}`}>
          {p}
        </li>
      ))}
    </ol>
  );
}

function Painel({ titulo, children, rotulo }: { titulo: string; children: ReactNode; rotulo?: string }) {
  return (
    <section className="wl-panel flex flex-col gap-4" aria-label={rotulo ?? titulo}>
      <h2 className="m-0 text-heading">{titulo}</h2>
      {children}
    </section>
  );
}

/** A venda: `id` abre a que existe; sem `id`, a Nova venda. */
export function TelaDaVenda({ id, veiculoInicial }: { id?: number; veiculoInicial?: number }) {
  const venda = useQuery({ queryKey: ["venda", id], queryFn: () => vendas.obter(id ?? 0), enabled: !!id, retry: false });
  if (id) {
    if (venda.isPending)
      return (
        <p className="text-body text-ink-muted" aria-busy="true">
          Carregando a venda…
        </p>
      );
    if (venda.isError)
      return (
        <p role="alert" className="text-body">
          {mensagemDoErro(venda.error)}
        </p>
      );
    const v = venda.data;
    return <FormularioDaVenda key={`${v.id}-${v.status}-${v.ultimo_contato_em ?? ""}`} venda={v} />;
  }
  return <FormularioDaVenda veiculoInicial={veiculoInicial} />;
}

export function FormularioDaVenda({ venda, veiculoInicial }: { venda?: VendaDetalhe; veiculoInicial?: number }) {
  const router = useRouter();
  const cliente = useQueryClient();
  const nova = !venda;
  const editavel = nova || venda.acoes.editar;
  const quitacao = venda?.origem === "quitacao_locacao";

  const [veiculo, setVeiculo] = useState<Veiculo | null>(null);
  const [comprador, setComprador] = useState<Cliente | null>(venda?.cliente ? { id: venda.cliente.id, nome: venda.cliente.nome } : null);
  const [semCadastro, setSemCadastro] = useState(!!venda?.interessado && !venda.cliente);
  const [interessado, setInteressado] = useState({ nome: venda?.interessado?.nome ?? "", celular: venda?.interessado?.celular ? celular(venda.interessado.celular) : "" });
  const [form, setForm] = useState<Formulario>(() => formularioDaVenda(venda));
  const [escolhendo, setEscolhendo] = useState<"veiculo" | "cliente" | null>(null);
  const [dialogo, setDialogo] = useState<"resposta" | "perder" | null>(null);

  // `?veiculo=`: a venda começa com o veículo da ficha.
  const inicial = useQuery({ queryKey: ["veiculo", veiculoInicial], queryFn: () => veiculos.obter(veiculoInicial ?? 0), enabled: nova && !!veiculoInicial, retry: false });
  useEffect(() => {
    if (inicial.data && !veiculo) setVeiculo(inicial.data as Veiculo);
  }, [inicial.data, veiculo]);

  const veiculoId = venda?.veiculo.id ?? veiculo?.id;
  const proposta = useMemo(() => propostaDoFormulario(form), [form]);
  const corpo = editavel && !quitacao && veiculoId ? JSON.stringify({ ...proposta, ...(venda ? { venda_id: venda.id } : { veiculo_id: veiculoId }) }) : null;
  const corpoAtrasado = useAtraso(corpo);
  const simulacao = useQuery({
    queryKey: ["venda-simulacao", corpoAtrasado],
    queryFn: () => vendas.simular(JSON.parse(corpoAtrasado ?? "{}") as Parameters<typeof vendas.simular>[0]),
    enabled: !!corpoAtrasado,
    placeholderData: (a) => a,
    retry: false,
  });
  const calculo = editavel && !quitacao ? (simulacao.data ?? venda?.calculo ?? null) : (venda?.calculo ?? null);
  const precisaGerente = !!calculo?.precisa_aprovacao;

  const quem = semCadastro ? { interessado: { nome: interessado.nome.trim(), celular: soDigitos(interessado.celular) } } : { cliente_id: comprador?.id ?? null };
  const executar = useMutation({
    mutationFn: async (acao: Acao): Promise<VendaDetalhe> => {
      if (nova) return vendas.criar({ veiculo_id: veiculoId ?? 0, ...quem, ...proposta, acao: acao === "salvar" ? "interessado" : acao });
      const id = venda.id;
      if (acao === "pedir_aprovacao") {
        // O desconto acima do limite vai só pelo pedido; o resto da proposta grava antes.
        const { desconto_pct, ...resto } = proposta;
        await vendas.editar(id, { ...quem, ...resto });
        return vendas.pedirAprovacao(id, desconto_pct ?? "0");
      }
      const salva = await vendas.editar(id, { ...quem, ...proposta });
      if (acao === "enviar") return (await vendas.enviar(id)).venda;
      return salva;
    },
    onSuccess: async (v) => {
      await atualizarVendas(cliente);
      if (nova) router.replace(`/vendas/${v.id}`);
    },
  });

  const erroSim = (campo: string) => simulacao.data?.erros?.[campo]?.[0];
  const erro = (campo: string) => campoDoErro(executar.error, campo) ?? erroSim(campo);
  const erroGeral = executar.isError && !["cliente_id", "interessado", "desconto_pct", "entrada_centavos", "num_parcelas", "forma", "veiculo_id"].some((c) => campoDoErro(executar.error, c)) ? executar.error : null;
  const ocupado = executar.isPending;
  const definir = (parte: Partial<Formulario>) => {
    executar.reset();
    setForm((f) => ({ ...f, ...parte }));
  };

  const aprovacao = venda?.aprovacao;
  const enviadaEm = dataDaProposta(venda?.proposta_enviada_em);
  const venceEm = dataDaProposta(venda?.proposta_vence_em);
  const titulo = nova ? "Nova venda" : `${venda.codigo} · ${venda.comprador_nome}`;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <nav aria-label="Caminho" className="text-caption text-ink-muted">
          <Link href="/vendas" className="text-ink-muted">
            Vendas
          </Link>{" "}
          / {nova ? "Nova" : venda.codigo}
        </nav>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="m-0 text-title md:text-display">{titulo}</h1>
          {venda && <StatusBadge tom={tomDaVenda(venda.status)}>{venda.situacao_texto}</StatusBadge>}
        </div>
        {!quitacao && <Passos />}
      </header>

      {quitacao && venda && (
        <Aviso tom="info">
          {venda.descricao}.{" "}
          {venda.locacao && (
            <Link href={`/locacoes/${venda.locacao.id}`} className="underline">
              Abrir locação
            </Link>
          )}
        </Aviso>
      )}
      {aprovacao?.texto && <Aviso tom={aprovacao.situacao === "recusado" ? "critico" : "info"}>{aprovacao.texto}</Aviso>}
      {venda?.status === "perdida" && venda.motivo_perda && <Aviso tom="info">Motivo da perda: {venda.motivo_perda}</Aviso>}

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-col gap-6 lg:flex-[999_1_560px]">
          <Painel titulo="Veículo e cliente">
            {nova ? (
              <Cartao
                icone={veiculo?.tipo_veiculo === "carro" ? Car : Bike}
                titulo={veiculo ? `${veiculo.marca} ${veiculo.modelo}` : <span className="font-normal text-ink-muted">Nenhum veículo escolhido</span>}
                detalhe={veiculo ? <span className="wl-mono">{`${placa(veiculo.placa)} · ${km(veiculo.km_atual)}`}</span> : undefined}
                acao={
                  <Button compacto onClick={() => setEscolhendo("veiculo")} aria-label="Veículo: escolher">
                    {veiculo ? "Trocar" : "Escolher"}
                  </Button>
                }
              />
            ) : (
              <Cartao icone={Bike} titulo={venda.veiculo.modelo} detalhe={<span className="wl-mono">{placa(venda.veiculo.placa)}</span>} />
            )}
            {erro("veiculo_id") && <p className="m-0 text-caption text-critical-ink">{erro("veiculo_id")}</p>}

            {semCadastro ? (
              <div className="flex flex-col gap-3 rounded-lg bg-surface-sunken p-3">
                <div className="grid gap-3 md:grid-cols-2">
                  <TextField cheio rotulo="Nome" value={interessado.nome} disabled={!editavel} onChange={(e) => setInteressado((i) => ({ ...i, nome: e.target.value }))} erro={erro("interessado")} />
                  <TextField cheio rotulo="Celular" inputMode="tel" value={interessado.celular} disabled={!editavel} onChange={(e) => setInteressado((i) => ({ ...i, celular: mascaraCelular(e.target.value) }))} />
                </div>
                <p className="m-0 text-caption text-ink-muted">{AJUDA_DO_INTERESSADO}</p>
                <div className="flex flex-wrap gap-2">
                  {editavel && (
                    <Button compacto onClick={() => setEscolhendo("cliente")}>
                      Escolher cliente com cadastro
                    </Button>
                  )}
                  {!nova && venda.interessado && (
                    <a href={linkDoWhatsApp(venda.interessado.celular)} target="_blank" rel="noreferrer" className="wl-btn wl-btn--sm">
                      Chamar no WhatsApp
                    </a>
                  )}
                </div>
              </div>
            ) : (
              <>
                <Cartao
                  icone={User}
                  titulo={comprador ? comprador.nome : <span className="font-normal text-ink-muted">Nenhum cliente escolhido</span>}
                  detalhe={comprador?.detalhe}
                  acao={
                    editavel ? (
                      <Button compacto onClick={() => setEscolhendo("cliente")} aria-label="Cliente: escolher">
                        {comprador ? "Trocar" : "Escolher"}
                      </Button>
                    ) : undefined
                  }
                />
                {nova && (
                  <div>
                    <Button
                      compacto
                      variante="quieto"
                      onClick={() => {
                        executar.reset();
                        setSemCadastro(true);
                      }}
                    >
                      Cliente sem cadastro: só nome e celular
                    </Button>
                  </div>
                )}
              </>
            )}
            {erro("cliente_id") && <p className="m-0 text-caption text-critical-ink">{erro("cliente_id")}</p>}
          </Painel>

          {!quitacao && (
            <Painel titulo="Pagamento">
              <Escolha rotulo="Forma de pagamento" opcoes={FORMAS} valor={form.forma} aoMudar={(f) => definir({ forma: f as FormaDaVenda })} desabilitado={!editavel} />
              {erro("forma") && <p className="m-0 text-caption text-critical-ink">{erro("forma")}</p>}
              <div className="grid gap-3 md:grid-cols-2">
                <TextField cheio mono rotulo="Preço de tabela" value={calculo ? dinheiro(calculo.preco_tabela_centavos) : ""} readOnly disabled />
                <TextField
                  cheio
                  mono
                  rotulo="Desconto (%)"
                  inputMode="decimal"
                  value={form.desconto}
                  disabled={!editavel}
                  onChange={(e) => definir({ desconto: e.target.value })}
                  dica={`Acima de ${pctTexto(calculo?.limite_desconto_pct ?? "5")} precisa do gerente`}
                  erro={erro("desconto_pct")}
                />
                {form.forma === "entrada_parcelas" && (
                  <>
                    <TextField cheio mono rotulo="Entrada (R$)" inputMode="decimal" value={form.entrada} disabled={!editavel} onChange={(e) => definir({ entrada: e.target.value })} erro={erro("entrada_centavos")} />
                    <TextField cheio mono rotulo="Parcelas" inputMode="numeric" value={form.parcelas} disabled={!editavel} onChange={(e) => definir({ parcelas: soDigitos(e.target.value).slice(0, 2) })} dica="De 2 a 24" erro={erro("num_parcelas")} />
                  </>
                )}
              </div>
            </Painel>
          )}
        </div>

        <aside className="flex min-w-0 flex-col gap-6 lg:sticky lg:top-6 lg:flex-[1_1_340px]">
          <Painel titulo="Resumo">
            {calculo ? <Valores linhas={linhasDoResumo(calculo)} /> : <p className="m-0 text-body text-ink-muted">{quitacao ? "Venda de R$ 0,00 da quitação da locação." : "Escolha o veículo para ver o preço."}</p>}
            {venda && (enviadaEm || venceEm) && (
              <Valores
                linhas={[
                  ...(enviadaEm ? [{ rotulo: "Enviada em", valor: enviadaEm }] : []),
                  ...(venceEm ? [{ rotulo: "Vence em", valor: venceEm }] : []),
                ]}
              />
            )}
            {editavel && precisaGerente && <Aviso tom="atencao">Desconto acima de {pctTexto(calculo?.limite_desconto_pct ?? "5")}. O gerente aprova pelo celular.</Aviso>}
            {erroGeral && <Aviso tom="critico">{mensagemDoErro(erroGeral)}</Aviso>}
            {simulacao.isError && <Aviso tom="critico">{mensagemDoErro(simulacao.error)}</Aviso>}

            <BotoesDaVenda
              venda={venda}
              semCadastro={semCadastro}
              precisaGerente={precisaGerente}
              ocupado={ocupado}
              aoExecutar={(a) => executar.mutate(a)}
              aoResponder={() => setDialogo("resposta")}
              aoPerder={() => setDialogo("perder")}
            />
            {!quitacao && venda?.status !== "perdida" && <p className="m-0 text-caption text-ink-muted">{NOTA_DA_CONCLUSAO}</p>}
          </Painel>
        </aside>
      </div>

      {escolhendo === "veiculo" && (
        <EscolherVeiculo
          aVenda
          aoFechar={() => setEscolhendo(null)}
          aoEscolher={(v) => {
            executar.reset();
            setVeiculo(v);
            setEscolhendo(null);
          }}
        />
      )}
      {escolhendo === "cliente" && (
        <EscolherCliente
          vazio="Nenhum cliente encontrado. Use Cliente sem cadastro para registrar só o nome e o celular."
          aoFechar={() => setEscolhendo(null)}
          aoEscolher={(c) => {
            executar.reset();
            setComprador({ id: c.id, nome: c.nome, detalhe: `${c.tipo === "pj" ? "CNPJ" : "CPF"} ${c.documento_mascarado}` });
            setSemCadastro(false);
            setEscolhendo(null);
          }}
        />
      )}
      {venda && dialogo === "resposta" && <RespostaDoCliente venda={venda} aoFechar={() => setDialogo(null)} />}
      {venda && dialogo === "perder" && <PerderVenda venda={venda} aoFechar={() => setDialogo(null)} />}
    </div>
  );
}

/** Os botões vêm de `acoes` (a API diz o que a pessoa pode fazer agora) e do `precisa_aprovacao` do simular (VEN-02). */
function BotoesDaVenda({ venda, semCadastro, precisaGerente, ocupado, aoExecutar, aoResponder, aoPerder }: { venda?: VendaDetalhe; semCadastro: boolean; precisaGerente: boolean; ocupado: boolean; aoExecutar: (a: Acao) => void; aoResponder: () => void; aoPerder: () => void }) {
  const principal = (rotulo: string, a: Acao) => (
    <Button variante="solido" disabled={ocupado} onClick={() => aoExecutar(a)}>
      {rotulo}
    </Button>
  );
  const secundario = (rotulo: string, a: Acao) => (
    <Button disabled={ocupado} onClick={() => aoExecutar(a)}>
      {rotulo}
    </Button>
  );

  if (!venda) {
    if (semCadastro) return <div className="flex flex-col gap-2">{principal("Salvar interessado", "interessado")}</div>;
    return (
      <div className="flex flex-col gap-2">
        {precisaGerente ? principal("Pedir aprovação do gerente", "pedir_aprovacao") : principal("Salvar proposta e enviar ao cliente", "enviar")}
        {secundario("Salvar como interessado", "interessado")}
      </div>
    );
  }

  const a = venda.acoes;
  const botoes: ReactNode[] = [];
  if (a.pedir_aprovacao && precisaGerente) botoes.push(<span key="pedir">{principal("Pedir aprovação do gerente", "pedir_aprovacao")}</span>);
  else if (a.enviar) botoes.push(<span key="enviar">{principal(venda.status === "interessado" ? "Salvar proposta e enviar ao cliente" : "Reenviar proposta", "enviar")}</span>);
  if (a.editar) botoes.push(<span key="salvar">{secundario("Salvar alterações", "salvar")}</span>);
  if (a.registrar_resposta)
    botoes.push(
      <Button key="resposta" disabled={ocupado} onClick={aoResponder}>
        Registrar resposta do cliente
      </Button>,
    );
  if (a.perder)
    botoes.push(
      <Button key="perder" variante="quieto" disabled={ocupado} onClick={aoPerder}>
        Marcar como perdida
      </Button>,
    );
  if (venda.status === "aguardando_aprovacao" && venda.aprovacao?.pedido_id)
    botoes.push(
      <Link key="pedido" href={`/aprovacoes/${venda.aprovacao.pedido_id}`} className="wl-btn">
        Ver o pedido
      </Link>,
    );
  if (botoes.length === 0) return null;
  return <div className="flex flex-col gap-2 [&>span>button]:w-full [&>button]:w-full [&>a]:w-full">{botoes}</div>;
}
