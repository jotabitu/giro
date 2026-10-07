"use client";

// Exemplos do preview. Os dados são de demonstração (Moto Rápida); telas reais mostram o que a API devolve.
import { ArrowUpRight, BarChart3, Bell, CarFront, FileText, LayoutGrid, Plus, Receipt, Settings, SlidersHorizontal, Tag, Users, Wrench } from "lucide-react";
import { useState, type ReactNode } from "react";
import {
  AlertCard,
  Button,
  CodigoVerificacao,
  CelulaDupla,
  Contador,
  Cover,
  DataTable,
  FleetBar,
  IconButton,
  Icone,
  KpiGrid,
  KpiTile,
  KpiVariacao,
  Panel,
  SearchField,
  SegmentedControl,
  Sidebar,
  StatusBadge,
  TextField,
  VehicleCard,
} from "@/design-system";

import type { SlugExemplo } from "./catalogo";

const Linha = ({ children }: { children: ReactNode }) => <div className="flex flex-wrap items-center gap-3">{children}</div>;

function ExemploButton() {
  return (
    <div className="flex flex-col gap-4">
      <Linha>
        <Button variante="solido" icone={<Icone de={Plus} />}>
          Nova locação
        </Button>
        <Button variante="marca">Ver alertas</Button>
        <Button>Exportar</Button>
        <Button variante="quieto">Cancelar</Button>
        <Button variante="solido" disabled>
          Salvar
        </Button>
      </Linha>
      <Linha>
        <Button variante="solido" compacto>
          Confirmar
        </Button>
        <Button variante="quieto" compacto>
          Detalhes
        </Button>
        <IconButton aria-label="Notificações" icone={<Icone de={Bell} />} notificacao />
        <IconButton aria-label="Abrir" icone={<Icone de={ArrowUpRight} />} quieto compacto />
        <IconButton aria-label="Filtros" icone={<Icone de={SlidersHorizontal} />} quieto compacto />
      </Linha>
    </div>
  );
}

function ExemploStatusBadge() {
  return (
    <div className="flex flex-col gap-4">
      <Linha>
        <StatusBadge tom="sucesso">Disponível</StatusBadge>
        <StatusBadge tom="info">Reservado</StatusBadge>
        <StatusBadge tom="solido">Alugado</StatusBadge>
        <StatusBadge tom="alerta">Em manutenção</StatusBadge>
        <StatusBadge>Em preparação</StatusBadge>
        <StatusBadge tom="critico">Atrasado</StatusBadge>
      </Linha>
      <Linha>
        <StatusBadge tom="alta">Alta</StatusBadge>
        <StatusBadge tom="alerta">Média</StatusBadge>
        <StatusBadge>Baixa</StatusBadge>
        <StatusBadge tom="atencao" ponto>
          Em vistoria
        </StatusBadge>
        <StatusBadge tom="marca">5 contratos pedem atenção</StatusBadge>
      </Linha>
      <Linha>
        <StatusBadge tom="sucesso" compacto>
          Pago
        </StatusBadge>
        <StatusBadge tom="info" compacto>
          A vencer
        </StatusBadge>
        <StatusBadge tom="critico" compacto>
          Inadimplente
        </StatusBadge>
        <Contador>128</Contador>
        <Contador>7</Contador>
      </Linha>
    </div>
  );
}

function ExemploSegmentedControl() {
  const [periodo, setPeriodo] = useState("7d");
  const [tipo, setTipo] = useState("todos");
  return (
    <Linha>
      <SegmentedControl
        rotulo="Período"
        valor={periodo}
        aoMudar={setPeriodo}
        opcoes={[
          { valor: "hoje", rotulo: "Hoje" },
          { valor: "7d", rotulo: "7 dias" },
          { valor: "30d", rotulo: "30 dias" },
        ]}
      />
      <SegmentedControl
        rotulo="Tipo de veículo"
        valor={tipo}
        aoMudar={setTipo}
        opcoes={[
          { valor: "todos", rotulo: "Todos" },
          { valor: "motos", rotulo: "Motos" },
          { valor: "carros", rotulo: "Carros" },
        ]}
      />
    </Linha>
  );
}

function ExemploKpiTile() {
  return (
    <Panel>
      <KpiGrid>
        <KpiTile destaque rotulo="Frota ativa" valor="86" contexto="52 motos · 34 carros" />
        <KpiTile rotulo="Alugados agora" valor="42" contexto={<><KpiVariacao>↗ 6</KpiVariacao> esta semana</>} />
        <KpiTile rotulo="Ocupação" valor="71%" contexto="meta de 80%" />
        <KpiTile rotulo="Em atraso" valor="7" contexto="R$ 4.380 a receber" />
      </KpiGrid>
    </Panel>
  );
}

type Devolucao = { placa: string; veiculo: string; cliente: string; data: string; situacao: ReactNode } & Record<string, unknown>;

const DEVOLUCOES: Devolucao[] = [
  { placa: "QXA-4B21", veiculo: "Honda CG 160 Fan", cliente: "Carlos Menezes", data: "06 out", situacao: <StatusBadge tom="critico" compacto>Atrasado</StatusBadge> },
  { placa: "PNB-7C04", veiculo: "Yamaha Factor 150", cliente: "Juliana Rocha", data: "08 out", situacao: <StatusBadge tom="solido" compacto>Alugado</StatusBadge> },
  { placa: "ROE-2A88", veiculo: "Fiat Mobi Like", cliente: "Pedro Alencar", data: "09 out", situacao: <StatusBadge tom="solido" compacto>Alugado</StatusBadge> },
  { placa: "SAK-1D39", veiculo: "Honda Biz 125", cliente: "Aline Duarte", data: "10 out", situacao: <StatusBadge tom="info" compacto>Renovação</StatusBadge> },
];

function ExemploDataTable() {
  const [aberto, setAberto] = useState<string>();
  return (
    <Panel
      titulo="Devoluções da semana"
      subtitulo={aberto ? `Aberto: ${aberto}` : "4 contratos · atualizado há 6 min"}
      acao={<IconButton aria-label="Filtros" icone={<Icone de={SlidersHorizontal} />} quieto compacto />}
    >
      <DataTable
        legenda="Devoluções da semana"
        chaveDaLinha={(l) => l.placa}
        aoAbrir={(l) => setAberto(l.placa)}
        linhas={DEVOLUCOES}
        colunas={[
          { chave: "placa", titulo: "Placa", mono: true },
          { chave: "veiculo", titulo: "Veículo e cliente", celula: (l) => <CelulaDupla principal={l.veiculo} secundaria={l.cliente} /> },
          { chave: "data", titulo: "Devolução", mono: true },
          { chave: "situacao", titulo: "Situação" },
        ]}
      />
    </Panel>
  );
}

function ExemploFleetBar() {
  const [filtro, setFiltro] = useState<string>();
  return (
    <FleetBar
      nota="86 veículos · ocupação de 71%"
      selecionado={filtro}
      aoSelecionar={setFiltro}
      segmentos={[
        { chave: "disponivel", rotulo: "Disponível", contagem: 16 },
        { chave: "alugado", rotulo: "Alugado", contagem: 42, destaque: "marca" },
        { chave: "reservado", rotulo: "Reservado", contagem: 9 },
        { chave: "manutencao", rotulo: "Manutenção", contagem: 7 },
        { chave: "a-venda", rotulo: "À venda", contagem: 12, destaque: "solido" },
      ]}
    />
  );
}

function ExemploSearchField() {
  return (
    <Linha>
      <SearchField placeholder="Buscar placa, cliente ou contrato" />
      <IconButton aria-label="Notificações" icone={<Icone de={Bell} />} notificacao />
      <Button variante="solido" icone={<Icone de={Plus} />} style={{ height: 56, padding: "0 28px" }}>
        Nova locação
      </Button>
    </Linha>
  );
}

function ExemploTextField() {
  return (
    <Linha>
      <TextField rotulo="Placa" mono defaultValue="QXA-4B21" dica="Formato Mercosul ou antigo" />
      <TextField rotulo="Quilometragem na saída" placeholder="Ex.: 12.430" dica="Leia no painel do veículo" />
      <TextField rotulo="CNH" defaultValue="Vencida em 03/09/2026" erro="CNH vencida: renove antes de alugar" />
    </Linha>
  );
}

function ExemploCodigoVerificacao() {
  const [codigo, setCodigo] = useState("481");
  const [enviado, setEnviado] = useState("");
  const [erro, setErro] = useState(false);
  return (
    <div className="flex flex-col gap-6" style={{ maxWidth: 420 }}>
      <CodigoVerificacao
        rotulo="Código do aplicativo"
        valor={codigo}
        aoMudar={(v) => {
          setCodigo(v);
          setErro(false);
        }}
        aoCompletar={(v) => {
          setEnviado(v);
          setErro(v !== "123456");
        }}
        erro={erro ? "Código incorreto. Confira o horário do celular e tente de novo." : undefined}
        autoFocus
      />
      <p className="text-caption text-ink-muted">
        Digite, cole o código inteiro ou use as setas. Qualquer código diferente de 123456 mostra o erro. Último completo: {enviado || "nenhum"}.
      </p>
      <CodigoVerificacao rotulo="Desabilitado" valor="" aoMudar={() => {}} disabled />
    </div>
  );
}

function ExemploAlertCard() {
  return (
    <div style={{ maxWidth: 460 }}>
      <AlertCard
        atualizadoHa="há 6 min"
        titulo="7 contratos precisam de ação hoje"
        itens={[
          { texto: "3 devoluções estão atrasadas", gravidade: "critica" },
          { texto: "2 motos passaram da revisão de 5.000 km", gravidade: "atencao" },
          { texto: "2 parcelas vencem até amanhã" },
        ]}
        acao={<Button variante="marca">Ver pendências</Button>}
      />
    </div>
  );
}

function ExemploVehicleCard() {
  const fatos = [
    { rotulo: "Diária", valor: "R$ 49,90" },
    { rotulo: "Rodados", valor: "2.140 km" },
    { rotulo: "Próxima revisão", valor: "15.000 km" },
  ] as const;
  const abrir = <IconButton aria-label="Abrir contrato" icone={<Icone de={ArrowUpRight} />} quieto compacto />;
  return (
    <div className="flex flex-wrap gap-6">
      <div style={{ width: 520, maxWidth: "100%" }}>
        <VehicleCard placa="QXA-4B21" status="Devolução hoje" modelo="Honda CG 160 Fan" cliente="Carlos Menezes" contrato="LOC-2841" diasCorridos={28} diasContratados={30} fatos={fatos} acao={abrir} />
      </div>
      <div style={{ width: 520, maxWidth: "100%" }}>
        <VehicleCard tipo="carro" placa="ROE-2A88" status="Devolução hoje" modelo="Fiat Mobi Like" cliente="Pedro Alencar" contrato="LOC-2847" diasCorridos={27} diasContratados={30} fatos={fatos} acao={abrir} />
      </div>
    </div>
  );
}

function ExemploSidebar() {
  return (
    <div style={{ maxWidth: 280 }}>
      <Sidebar
        marca={{ nome: "Moto Rápida" }}
        filial={{ nome: "Filial Centro", cidade: "Fortaleza, CE" }}
        grupos={[
          {
            itens: [
              { rotulo: "Visão geral", href: "#", icone: <Icone de={LayoutGrid} />, ativo: true },
              { rotulo: "Veículos", href: "#", icone: <Icone de={CarFront} />, contador: 86 },
            ],
          },
          {
            rotulo: "Operação",
            itens: [
              { rotulo: "Locações", href: "#", icone: <Icone de={FileText} />, contador: 42 },
              { rotulo: "Vendas", href: "#", icone: <Icone de={Tag} /> },
              { rotulo: "Clientes", href: "#", icone: <Icone de={Users} /> },
              { rotulo: "Manutenções", href: "#", icone: <Icone de={Wrench} />, contador: 5 },
            ],
          },
          {
            rotulo: "Financeiro",
            itens: [
              { rotulo: "Contas a receber", href: "#", icone: <Icone de={Receipt} />, contador: 7 },
              { rotulo: "Relatórios", href: "#", icone: <Icone de={BarChart3} /> },
              { rotulo: "Configurações", href: "#", icone: <Icone de={Settings} /> },
            ],
          },
        ]}
      />
    </div>
  );
}

const EXEMPLOS: Record<SlugExemplo, () => ReactNode> = {
  "alert-card": ExemploAlertCard,
  "button": ExemploButton,
  "codigo-verificacao": ExemploCodigoVerificacao,
  "cover": () => <Cover />,
  "data-table": ExemploDataTable,
  "fleet-bar": ExemploFleetBar,
  "kpi-tile": ExemploKpiTile,
  "search-field": ExemploSearchField,
  "segmented-control": ExemploSegmentedControl,
  "sidebar": ExemploSidebar,
  "status-badge": ExemploStatusBadge,
  "text-field": ExemploTextField,
  "vehicle-card": ExemploVehicleCard,
};

export function ExemploDe({ slug }: { slug: SlugExemplo }) {
  const Exemplo = EXEMPLOS[slug];
  return <Exemplo />;
}
