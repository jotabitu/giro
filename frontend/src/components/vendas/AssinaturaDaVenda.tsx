"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Aviso, Button, Dialogo, Etapas, Icone, StatusBadge, TextField, type Etapa } from "@/design-system";
import { LinkCopiado, useCopiarLink } from "@/components/comum/LinkParaCopiar";
import { BaixaDaConta } from "@/components/financeiro/BaixaDaConta";
import { PixGerado } from "@/components/financeiro/DetalheDaConta";
import { ErroApi, financeiro, vendas, type CobrancaDaConta, type VendaDetalhe } from "@/lib/api";
import { agoraDaTela } from "@/lib/ambiente";
import { ROTULO_PENDENCIA } from "@/lib/clientes";
import { campoDoErro, mensagemDoErro } from "@/lib/erros";
import { dataCompleta, dataHoraCurta, diaDe } from "@/lib/formatos";
import { atualizarVendas, comMaiuscula } from "@/lib/vendas";

// Fase 1b da T-502 (docs/api/vendas.md): passos 2 · Documentos e 3 · Assinatura, a conclusão em `vendida` e a
// transferência no Detran (VEN-14, VEN-15, VEN-17, VEN-19). Os textos de situação vêm prontos da API (`documentos.texto`,
// `contrato.situacao_texto`, `conta_entrada.texto`, `conclusao_texto`); a tela só escolhe onde mostrar e o que liberar
// pelas `acoes`. A entrada se paga pelas rotas do financeiro, com as ações que a própria conta devolve.

const COM_O_CONTRATO_E_A_ENTRADA = "Com o contrato assinado e a entrada paga, em qualquer ordem, a venda é concluída sozinha.";

export function Painel({ titulo, children, rotulo, acao }: { titulo: string; children: ReactNode; rotulo?: string; acao?: ReactNode }) {
  return (
    <section className="wl-panel flex flex-col gap-4" aria-label={rotulo ?? titulo}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-heading">{titulo}</h2>
        {acao}
      </div>
      {children}
    </section>
  );
}

function Erro({ erro }: { erro: unknown }) {
  // IMP-04: sem modelo de compra e venda publicado, a API manda o caminho para publicar um.
  const link = erro instanceof ErroApi && erro.codigo === "IMP-04" && typeof erro.detalhes?.link === "string" ? erro.detalhes.link : null;
  return (
    <Aviso tom="critico">
      {mensagemDoErro(erro)}
      {link && (
        <>
          {" "}
          <Link href={link} className="underline">
            Publicar modelo
          </Link>
        </>
      )}
    </Aviso>
  );
}

/** O PDF do contrato (o assinado, se houver), por uma URL de 15 minutos. */
export function BotaoDoContrato({ vendaId, rotulo = "Contrato" }: { vendaId: number; rotulo?: string }) {
  const pdf = useMutation({ mutationFn: () => vendas.pdfDoContrato(vendaId), onSuccess: (r) => window.open(r.url, "_blank", "noopener") });
  return (
    <span className="inline-flex flex-col items-start gap-1">
      <Button compacto variante="quieto" icone={<Icone de={Download} />} disabled={pdf.isPending} onClick={() => pdf.mutate()}>
        {rotulo}
      </Button>
      {pdf.isError && (
        <span role="alert" className="text-caption text-critical-ink">
          {mensagemDoErro(pdf.error)}
        </span>
      )}
    </span>
  );
}

/** Passo 2 · Documentos (VEN-14, VEN-19): o cadastro do cliente antes da assinatura. A API diz o que falta e se libera. */
export function DocumentosDaVenda({ venda }: { venda: VendaDetalhe }) {
  const cliente = useQueryClient();
  const d = venda.documentos;
  const preparar = useMutation({ mutationFn: () => vendas.prepararAssinatura(venda.id), onSuccess: () => atualizarVendas(cliente) });
  if (!d) return null;
  const pode = d.pode_preparar && venda.acoes.preparar_assinatura;
  return (
    <Painel titulo="Documentos">
      {d.texto ? (
        <Aviso tom={d.gravidade === "critica" ? "critico" : "atencao"}>{d.texto}</Aviso>
      ) : (
        venda.cliente && (
          <div className="rounded-lg bg-surface-sunken p-3">
            <div className="text-body font-medium">{venda.cliente.nome}</div>
            <div className="text-caption text-ink-muted">Cadastro completo</div>
          </div>
        )
      )}
      {d.pendencias.length > 0 && (
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0" aria-label="O que falta no cadastro">
          {d.pendencias.map((p) => (
            <li key={p} className="wl-badge">
              {comMaiuscula(ROTULO_PENDENCIA[p] ?? p)}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        {d.pendencias.length > 0 && venda.cliente && (
          <Link href={`/clientes/${venda.cliente.id}`} className="wl-btn wl-btn--quiet no-underline">
            Completar cadastro
          </Link>
        )}
        <Button variante="solido" disabled={!pode || preparar.isPending} onClick={() => preparar.mutate()}>
          {preparar.isPending ? "Preparando…" : "Preparar assinatura"}
        </Button>
      </div>
      {preparar.isError && <Erro erro={preparar.error} />}
    </Painel>
  );
}

/** Passo 3 · Assinatura (VEN-15): contrato, assinatura do cliente, entrada e conclusão. Na `vendida`, o resumo dela. */
export function AssinaturaDaVenda({ venda }: { venda: VendaDetalhe }) {
  const cliente = useQueryClient();
  const c = venda.contrato;
  const e = venda.conta_entrada;
  const [aviso, setAviso] = useState<string | null>(null);
  const [cancelando, setCancelando] = useState(false);
  const [cobranca, setCobranca] = useState<CobrancaDaConta | null>(null);
  const [recebendo, setRecebendo] = useState(false);

  // As ações da entrada (Pix, boleto e caixa) são as da conta no financeiro, que a API libera por perfil e plano.
  const aberta = e?.status === "aberta";
  const conta = useQuery({ queryKey: ["contas-receber", "detalhe", e?.id], queryFn: () => financeiro.obterConta(e?.id ?? 0), enabled: aberta, retry: false });
  const gerar = useMutation({ mutationFn: (tipo: "pix" | "boleto") => financeiro.gerarCobranca(e?.id ?? 0, { tipo }), onSuccess: setCobranca });
  const reenviar = useMutation({ mutationFn: () => vendas.reenviarContrato(venda.id), onSuccess: () => setAviso("Contrato reenviado ao cliente, com um link novo.") });
  const link = useCopiarLink(() => vendas.copiarLinkDoContrato(venda.id));

  if (!c && !e) return null;
  const vendida = venda.status === "vendida";
  const assinado = c?.status === "assinado";
  const cancelado = c?.status === "cancelado";
  const paga = e?.status === "paga";
  const a = venda.acoes;
  const acoesDaConta = aberta ? conta.data?.acoes : undefined;

  const etapas: Etapa[] = [];
  if (c) {
    etapas.push({
      titulo: "Contrato enviado",
      texto: c.enviado_em ? dataHoraCurta(c.enviado_em) : c.situacao_texto,
      estado: c.enviado_em || assinado ? "feita" : cancelado ? "pendente" : "atual",
      acoes:
        a.copiar_link_contrato || a.reenviar_contrato ? (
          <>
            {a.copiar_link_contrato && (
              <Button compacto disabled={link.pendente} onClick={link.copiar}>
                {link.pendente ? "Copiando…" : "Copiar link para assinar"}
              </Button>
            )}
            {a.reenviar_contrato && (
              <Button compacto variante="quieto" disabled={reenviar.isPending} onClick={() => reenviar.mutate()}>
                {reenviar.isPending ? "Reenviando…" : "Reenviar contrato"}
              </Button>
            )}
          </>
        ) : undefined,
    });
    etapas.push({
      titulo: "Assinatura do cliente",
      texto: assinado && c.assinado_em ? `Assinado em ${dataHoraCurta(c.assinado_em)}` : c.situacao_texto,
      estado: assinado ? "feita" : cancelado ? "pendente" : "atual",
    });
  }
  if (e) {
    etapas.push({
      titulo: e.rotulo,
      texto: e.texto,
      estado: paga ? "feita" : aberta ? "atual" : "pendente",
      acoes:
        acoesDaConta && (acoesDaConta.gerar_pix || acoesDaConta.gerar_boleto || acoesDaConta.receber) ? (
          <>
            {acoesDaConta.gerar_pix && (
              <Button compacto disabled={gerar.isPending} onClick={() => gerar.mutate("pix")}>
                Gerar Pix
              </Button>
            )}
            {acoesDaConta.gerar_boleto && (
              <Button compacto disabled={gerar.isPending} onClick={() => gerar.mutate("boleto")}>
                Gerar boleto
              </Button>
            )}
            {acoesDaConta.receber && (
              <Button compacto onClick={() => setRecebendo(true)}>
                Receber no caixa
              </Button>
            )}
          </>
        ) : undefined,
    });
  }
  etapas.push({
    titulo: "Venda concluída",
    texto: vendida && venda.vendida_em ? dataHoraCurta(venda.vendida_em) : COM_O_CONTRATO_E_A_ENTRADA,
    estado: vendida ? "feita" : "pendente",
  });

  return (
    <Painel titulo="Assinatura" acao={vendida && c?.pdf_disponivel ? <BotaoDoContrato vendaId={venda.id} /> : undefined}>
      {/* No painel branco, o botão padrão das etapas ganha o contorno fino da referência (Copiar link, Pix, boleto, caixa). */}
      <div className="[&_.wl-btn:not(.wl-btn--quiet):not(.wl-btn--solid)]:shadow-[inset_0_0_0_1px_var(--line)]">
        <Etapas etapas={etapas} rotulo="Assinatura e entrada" />
      </div>
      {link.resultado && (
        <LinkCopiado resultado={link.resultado} copiado={!link.falhouACopia} aviso="Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." aoFechar={link.limpar} />
      )}
      {cobranca && aberta && <PixGerado cobranca={cobranca} rotuloDoCopiar={cobranca.tipo === "boleto" ? "Copiar boleto" : "Copiar Pix"} />}
      {venda.conclusao_texto && <p className="m-0 text-body">{venda.conclusao_texto}</p>}
      {aviso && (
        <p role="status" className="m-0 text-caption text-ink-muted">
          {aviso}
        </p>
      )}
      {(link.erro || reenviar.isError || gerar.isError || conta.isError) && (
        <Aviso tom="critico">{link.erro ?? mensagemDoErro(reenviar.error ?? gerar.error ?? conta.error)}</Aviso>
      )}
      {a.cancelar_assinatura && (
        <div className="flex justify-end">
          <Button compacto variante="quieto" onClick={() => setCancelando(true)}>
            Cancelar assinatura
          </Button>
        </div>
      )}
      {cancelando && <CancelarAssinatura venda={venda} aoFechar={() => setCancelando(false)} />}
      {recebendo && conta.data && (
        <BaixaDaConta
          conta={conta.data}
          aoFechar={() => setRecebendo(false)}
          aoConcluir={(m) => {
            setAviso(m);
            void atualizarVendas(cliente);
          }}
        />
      )}
    </Painel>
  );
}

/** "Cancelar a assinatura?" (VEN-19): contrato e cobrança da entrada cancelados; a proposta volta a se editar. */
function CancelarAssinatura({ venda, aoFechar }: { venda: VendaDetalhe; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const cancelar = useMutation({
    mutationFn: () => vendas.cancelarAssinatura(venda.id),
    onSuccess: async () => {
      await atualizarVendas(cliente);
      aoFechar();
    },
  });
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo="Cancelar a assinatura?"
      descricao="O contrato e a cobrança da entrada são cancelados, e você pode mudar a proposta."
      acoes={
        <>
          <Button variante="quieto" onClick={aoFechar}>
            Manter assinatura
          </Button>
          <Button variante="solido" disabled={cancelar.isPending} onClick={() => cancelar.mutate()}>
            {cancelar.isPending ? "Cancelando…" : "Cancelar assinatura"}
          </Button>
        </>
      }
    >
      {cancelar.isError ? <Aviso tom="critico">{mensagemDoErro(cancelar.error)}</Aviso> : null}
    </Dialogo>
  );
}

/** "Transferência no Detran" da venda de balcão concluída (VEN-17): pendente, com a data e "Transferência feita", ou feita. */
export function TransferenciaDaVenda({ venda }: { venda: VendaDetalhe }) {
  const cliente = useQueryClient();
  const hoje = diaDe(agoraDaTela().toISOString());
  const [data, setData] = useState(hoje);
  const registrar = useMutation({ mutationFn: () => vendas.registrarTransferencia(venda.id, data), onSuccess: () => atualizarVendas(cliente) });
  if (venda.status !== "vendida" || venda.origem !== "balcao") return null;
  const t = venda.transferencia;
  return (
    <Painel
      titulo="Transferência no Detran"
      acao={
        <StatusBadge tom={t.pendente ? "alerta" : "sucesso"} compacto>
          {t.pendente ? "Falta a transferência no Detran" : "Feita"}
        </StatusBadge>
      }
    >
      {t.pendente ? (
        venda.acoes.registrar_transferencia && (
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(ev) => {
              ev.preventDefault();
              if (!registrar.isPending && data) registrar.mutate();
            }}
          >
            <div className="min-w-[200px] flex-1">
              <TextField cheio rotulo="Data da transferência" type="date" max={hoje} min={venda.vendida_em ? diaDe(venda.vendida_em) : undefined} value={data} onChange={(ev) => setData(ev.target.value)} erro={campoDoErro(registrar.error, "feita_em")} />
            </div>
            <Button variante="solido" type="submit" disabled={registrar.isPending || !data}>
              {registrar.isPending ? "Registrando…" : "Transferência feita"}
            </Button>
          </form>
        )
      ) : (
        <p className="m-0 text-body">
          Transferência feita em {t.feita_em ? dataCompleta(t.feita_em) : "—"}
          {t.registrada_por ? ` · ${t.registrada_por.nome}` : ""}
        </p>
      )}
      {registrar.isError && !campoDoErro(registrar.error, "feita_em") && <Aviso tom="critico">{mensagemDoErro(registrar.error)}</Aviso>}
    </Painel>
  );
}
