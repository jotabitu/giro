"use client";

import { useQuery } from "@tanstack/react-query";
import { Bike, Car, User } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button, Dialogo, Icone, SearchField, StatusBadge } from "@/design-system";
import { clientes, veiculos, type ClienteCompleto, type ClienteResumo, type Veiculo } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { dataCompleta, km, placa } from "@/lib/formatos";
import { tomDoStatus } from "@/lib/tom";

function Miniatura({ icone }: { icone: typeof User }) {
  return (
    <span aria-hidden="true" className="grid h-[52px] w-[52px] shrink-0 place-items-center rounded-md bg-surface-sunken text-ink-muted">
      <Icone de={icone} />
    </span>
  );
}

/** Cartão de escolha: o que foi escolhido, o que a API diz sobre isso e o botão Trocar. */
function Cartao({ icone, rotulo, vazio, onTrocar, children }: { icone: typeof User; rotulo: string; vazio: string; onTrocar: () => void; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-surface-sunken p-3">
      <Miniatura icone={icone} />
      <div className="min-w-0 flex-1">{children ?? <span className="text-body text-ink-muted">{vazio}</span>}</div>
      <Button compacto onClick={onTrocar} aria-label={`${rotulo}: escolher`}>
        {children ? "Trocar" : "Escolher"}
      </Button>
    </div>
  );
}

/** "CNH A · válida até 2029" para quem tem o cadastro completo; vencida vira aviso. */
export function textoDaCnh(c: ClienteResumo | ClienteCompleto | undefined, hoje: string): { texto: string; tom: "sucesso" | "alerta" } | null {
  if (!c || !("cnh" in c) || !c.cnh?.categoria) return null;
  const validade = c.cnh.validade;
  if (!validade) return { texto: `CNH ${c.cnh.categoria}`, tom: "sucesso" };
  return validade < hoje ? { texto: `CNH ${c.cnh.categoria} · vencida em ${dataCompleta(validade)}`, tom: "alerta" } : { texto: `CNH ${c.cnh.categoria} · válida até ${validade.slice(0, 4)}`, tom: "sucesso" };
}

export function CartaoDoCliente({ cliente, completo, hoje, onTrocar }: { cliente: ClienteResumo | undefined; completo: ClienteResumo | ClienteCompleto | undefined; hoje: string; onTrocar: () => void }) {
  const cnh = textoDaCnh(completo, hoje);
  return (
    <Cartao icone={User} rotulo="Cliente" vazio="Nenhum cliente escolhido" onTrocar={onTrocar}>
      {cliente && (
        <>
          <div className="truncate text-body font-medium">{cliente.nome}</div>
          <div className="text-caption text-ink-muted">{cliente.tipo === "pj" ? "CNPJ" : "CPF"} {cliente.documento_mascarado}</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {cnh && (
              <StatusBadge tom={cnh.tom} compacto>
                {cnh.texto}
              </StatusBadge>
            )}
            {cliente.status !== "ativo" && (
              <StatusBadge tom={tomDoStatus(cliente.situacao.tom)} compacto>
                {cliente.situacao.rotulo}
              </StatusBadge>
            )}
          </div>
        </>
      )}
    </Cartao>
  );
}

export function CartaoDoVeiculo({ veiculo, onTrocar }: { veiculo: Veiculo | undefined; onTrocar: () => void }) {
  return (
    <Cartao icone={veiculo?.tipo_veiculo === "carro" ? Car : Bike} rotulo="Veículo" vazio="Nenhum veículo escolhido" onTrocar={onTrocar}>
      {veiculo && (
        <>
          <div className="truncate text-body font-medium">{`${veiculo.marca} ${veiculo.modelo}`}</div>
          <div className="wl-mono text-caption text-ink-muted">
            {placa(veiculo.placa)} · {km(veiculo.km_atual)}
          </div>
          <div className="mt-1">
            <StatusBadge tom={tomDoStatus(veiculo.situacao.tom)} compacto>
              {veiculo.situacao.rotulo}
            </StatusBadge>
          </div>
        </>
      )}
    </Cartao>
  );
}

function Busca({ titulo, descricao, aoFechar, placeholder, children, texto, setTexto }: { titulo: string; descricao: string; aoFechar: () => void; placeholder: string; children: ReactNode; texto: string; setTexto: (t: string) => void }) {
  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={titulo}
      descricao={descricao}
      acoes={
        <Button variante="quieto" onClick={aoFechar}>
          Voltar
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        <SearchField data-autofocus placeholder={placeholder} value={texto} onChange={(e) => setTexto(e.target.value)} />
        {children}
      </div>
    </Dialogo>
  );
}

function Opcao({ aoEscolher, titulo, detalhe, selo }: { aoEscolher: () => void; titulo: string; detalhe: string; selo?: ReactNode }) {
  return (
    <li>
      <button type="button" onClick={aoEscolher} className="flex min-h-[44px] w-full items-center justify-between gap-3 rounded-md bg-surface-sunken px-4 py-3 text-left">
        <span className="min-w-0">
          <span className="block truncate text-body font-medium">{titulo}</span>
          <span className="block text-caption text-ink-muted">{detalhe}</span>
        </span>
        {selo}
      </button>
    </li>
  );
}

/** Procura o cliente por nome, CPF ou telefone. Quem não pode alugar (bloqueado, inativo) a API recusa na simulação. */
export function EscolherCliente({ aoEscolher, aoFechar }: { aoEscolher: (c: ClienteResumo) => void; aoFechar: () => void }) {
  const [busca, setBusca] = useState("");
  const consulta = useQuery({ queryKey: ["clientes", "escolher", busca], queryFn: () => clientes.listar({ busca: busca || undefined }), placeholderData: (a) => a });
  return (
    <Busca titulo="Escolher o cliente" descricao="Procure por nome, CPF ou telefone." aoFechar={aoFechar} placeholder="Nome, CPF ou telefone" texto={busca} setTexto={setBusca}>
      {consulta.isError && <p role="alert" className="text-body">{mensagemDoErro(consulta.error)}</p>}
      {consulta.isPending && <p className="text-body text-ink-muted" aria-busy="true">Procurando…</p>}
      {consulta.data && consulta.data.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhum cliente encontrado. Cadastre o cliente antes de alugar.</p>}
      <ul className="flex max-h-[320px] flex-col gap-2 overflow-y-auto">
        {consulta.data?.resultados.map((c) => (
          <Opcao
            key={c.id}
            aoEscolher={() => aoEscolher(c)}
            titulo={c.nome}
            detalhe={`${c.tipo === "pj" ? "CNPJ" : "CPF"} ${c.documento_mascarado}`}
            selo={
              <StatusBadge tom={tomDoStatus(c.situacao.tom)} compacto>
                {c.situacao.rotulo}
              </StatusBadge>
            }
          />
        ))}
      </ul>
    </Busca>
  );
}

/** Procura entre os veículos disponíveis (e os reservados que a API aceitar na simulação). */
export function EscolherVeiculo({ aoEscolher, aoFechar }: { aoEscolher: (v: Veiculo) => void; aoFechar: () => void }) {
  const [busca, setBusca] = useState("");
  const consulta = useQuery({ queryKey: ["veiculos", "escolher", busca], queryFn: () => veiculos.listar({ status: "disponivel", busca: busca || undefined }), placeholderData: (a) => a });
  return (
    <Busca titulo="Escolher o veículo" descricao="Só os veículos disponíveis aparecem aqui." aoFechar={aoFechar} placeholder="Placa ou modelo" texto={busca} setTexto={setBusca}>
      {consulta.isError && <p role="alert" className="text-body">{mensagemDoErro(consulta.error)}</p>}
      {consulta.isPending && <p className="text-body text-ink-muted" aria-busy="true">Procurando…</p>}
      {consulta.data && consulta.data.resultados.length === 0 && <p className="text-body text-ink-muted">Nenhum veículo disponível com essa busca.</p>}
      <ul className="flex max-h-[320px] flex-col gap-2 overflow-y-auto">
        {consulta.data?.resultados.map((v) => (
          <Opcao key={v.id} aoEscolher={() => aoEscolher(v)} titulo={`${v.marca} ${v.modelo}`} detalhe={`${placa(v.placa)} · ${km(v.km_atual)}`} />
        ))}
      </ul>
    </Busca>
  );
}
