"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Panel, StatusBadge } from "@/design-system";
import { vendas } from "@/lib/api";
import { useAgora } from "@/lib/ambiente";
import { dinheiroSemZeros } from "@/lib/formatos";
import { linkDoWhatsApp, tomDaVenda, ultimoContato } from "@/lib/vendas";
import { LinhaDoPainel, ListaDoPainel, Vazio } from "./comuns";

// Referência: docs/telas/html/Vendedor-Desktop.dc.html e Vendedor-Mobile.dc.html (T-503, VEN-16, VEN-19).
// Fase 1a da T-502: as propostas abertas do vendedor (a API devolve só as dele, USR-08), na ordem em que a API manda.
// A ordem pelo último contato (VEN-16), o celular do cliente com cadastro, a meta, o funil e a comissão prevista chegam
// com a 1c. Sem o recurso de vendas no plano (403 PLT-12), o bloco não aparece.

export function PropostasDoVendedor() {
  const agora = useAgora();
  const abertas = useQuery({ queryKey: ["vendas", "abertas", "vendedor"], queryFn: () => vendas.listar({ aba: "abertas" }), retry: false });
  if (!abertas.data) return null;
  const itens = abertas.data.resultados;
  const n = !abertas.data.proximo ? itens.length : null;
  return (
    <Panel titulo={n ? `Propostas para retornar · ${n}` : "Propostas para retornar"}>
      {itens.length === 0 ? (
        <Vazio>Você não tem propostas abertas.</Vazio>
      ) : (
        <ListaDoPainel rotulo="Propostas para retornar">
          {itens.map((v) => (
            <LinhaDoPainel
              key={v.id}
              titulo={
                <Link href={`/vendas/${v.id}`} className="text-ink">
                  {v.comprador_nome}
                </Link>
              }
              apoio={
                <>
                  {v.veiculo.modelo} · <span className="font-semibold text-ink">{dinheiroSemZeros(v.preco_final_centavos)}</span> · {ultimoContato(v.ultimo_contato_em, agora)}
                </>
              }
              fim={
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <StatusBadge tom={tomDaVenda(v.status)} compacto>
                    {v.situacao_texto}
                  </StatusBadge>
                  {v.interessado && (
                    <a href={linkDoWhatsApp(v.interessado.celular)} target="_blank" rel="noreferrer" className="wl-btn wl-btn--quiet wl-btn--sm">
                      Chamar no WhatsApp
                    </a>
                  )}
                </div>
              }
            />
          ))}
        </ListaDoPainel>
      )}
    </Panel>
  );
}
