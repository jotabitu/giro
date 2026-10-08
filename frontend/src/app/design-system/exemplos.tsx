"use client";

// Exemplos do preview. Os dados são de demonstração (Moto Rápida); telas reais mostram o que a API devolve.
import { ArrowUpRight, Menu as IconeMenu, BarChart3, Bell, CarFront, FileText, LayoutGrid, Plus, Receipt, Settings, SlidersHorizontal, Tag, Users, Wrench } from "lucide-react";
import { useState, type ReactNode } from "react";
import {
  AlertCard,
  Button,
  CodigoVerificacao,
  CelulaDupla,
  Dialogo,
  Gaveta,
  SeletorDeFilial,
  Contador,
  Cover,
  DataTable,
  FleetBar,
  IconButton,
  Icone,
  KpiGrid,
  KpiTile,
  KpiVariacao,
  LinhaDeLista,
  ListaDeLinhas,
  Panel,
  ProgressBar,
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
    <div className="flex flex-col gap-6">
      <Panel>
        <KpiGrid>
          <KpiTile destaque rotulo="Frota ativa" valor="86" contexto="52 motos · 34 carros" />
          <KpiTile rotulo="Alugados agora" valor="42" contexto={<><KpiVariacao>↗ 6</KpiVariacao> esta semana</>} />
          <KpiTile rotulo="Ocupação" valor="71%" contexto="meta de 80%" />
          <KpiTile rotulo="Em atraso" valor="7" contexto="R$ 4.380 a receber" />
        </KpiGrid>
      </Panel>
      <Panel titulo="Valores longos" subtitulo="O número encolhe até caber; nunca é cortado">
        <KpiGrid>
          <KpiTile destaque rotulo="Receita do mês" valor="R$ 1.284.350,00" contexto="meta de R$ 1.500.000,00" />
          <KpiTile rotulo="A receber" valor="R$ 48.920,50" contexto="31 parcelas" />
          <KpiTile rotulo="Caução retida" valor="R$ 12.600,00" contexto="42 contratos" />
          <KpiTile rotulo="Em atraso" valor="R$ 4.380,00" contexto="7 contratos" />
        </KpiGrid>
      </Panel>
    </div>
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

function ExemploProgressBar() {
  return (
    <div className="flex max-w-md flex-col gap-4">
      <ProgressBar valor={40} rotulo="Primeiros passos" />
      <ProgressBar valor={100} rotulo="Implantação concluída" />
    </div>
  );
}

function ExemploLinhaDeLista() {
  return (
    <Panel titulo="Parcelas em atraso" subtitulo="Filial Centro">
      <ListaDeLinhas rotulo="Parcelas em atraso">
        <LinhaDeLista titulo="Carlos Souza" apoio="LOC-2841 · parcela 2 de 5 · venceu em 30 set" acao={<Button variante="quieto" compacto>Cobrar</Button>} />
        <LinhaDeLista titulo="Rafael Lima" apoio="LOC-2839 · R$ 1.347,00 · 25 dias" acao={<Button variante="quieto" compacto>Cobrar</Button>} />
        <LinhaDeLista titulo="Sem ação" apoio="Linha só informativa" />
      </ListaDeLinhas>
    </Panel>
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

const FILIAIS = [
  { id: "centro", nome: "Filial Centro", cidade: "Fortaleza, CE" },
  { id: "aldeota", nome: "Filial Aldeota", cidade: "Fortaleza, CE" },
  { id: "messejana", nome: "Filial Messejana", cidade: "Fortaleza, CE" },
];

function ExemploSeletorDeFilial() {
  const [admin, setAdmin] = useState("todas");
  const [gerente, setGerente] = useState("centro");
  return (
    <div className="flex flex-wrap gap-8" style={{ minHeight: 360 }}>
      <div style={{ width: 280 }}>
        <p className="mb-2 text-caption text-ink-muted">Administrador: com Todas as filiais</p>
        <SeletorDeFilial filiais={FILIAIS} valor={admin} aoMudar={setAdmin} permiteTodas />
      </div>
      <div style={{ width: 280 }}>
        <p className="mb-2 text-caption text-ink-muted">Gerente com duas filiais</p>
        <SeletorDeFilial filiais={FILIAIS.slice(0, 2)} valor={gerente} aoMudar={setGerente} />
      </div>
      <div style={{ width: 280 }}>
        <p className="mb-2 text-caption text-ink-muted">Uma filial só: não aparece</p>
        <SeletorDeFilial filiais={FILIAIS.slice(0, 1)} valor="centro" aoMudar={() => {}} />
      </div>
    </div>
  );
}

function ExemploDialogo() {
  const [formulario, setFormulario] = useState(false);
  const [confirma, setConfirma] = useState(false);
  const [feito, setFeito] = useState("");
  return (
    <div className="flex flex-col gap-4">
      <Linha>
        <Button variante="solido" onClick={() => setFormulario(true)}>
          Abrir formulário
        </Button>
        <Button onClick={() => setConfirma(true)}>Abrir confirmação</Button>
      </Linha>
      <p className="text-caption text-ink-muted">Último resultado: {feito || "nenhum"}.</p>
      <Dialogo
        aberto={formulario}
        aoFechar={() => setFormulario(false)}
        titulo="Pedir cancelamento do contrato LOC-2841"
        descricao="O gerente vai analisar o pedido. O contrato continua ativo até a aprovação."
        fecharAoClicarFora={false}
        acoes={
          <>
            <Button variante="quieto" onClick={() => setFormulario(false)}>
              Voltar
            </Button>
            <Button
              variante="solido"
              onClick={() => {
                setFeito("pedido enviado");
                setFormulario(false);
              }}
            >
              Enviar pedido
            </Button>
          </>
        }
      >
        <TextField cheio data-autofocus rotulo="Motivo" placeholder="Ex.: cliente devolveu a moto antes do prazo" />
      </Dialogo>
      <Dialogo
        aberto={confirma}
        aoFechar={() => setConfirma(false)}
        tamanho="pequeno"
        titulo="Encerrar a sessão?"
        descricao="Você precisará entrar de novo com e-mail e senha."
        acoes={
          <>
            <Button variante="quieto" data-autofocus onClick={() => setConfirma(false)}>
              Continuar aqui
            </Button>
            <Button
              variante="solido"
              onClick={() => {
                setFeito("sessão encerrada");
                setConfirma(false);
              }}
            >
              Encerrar
            </Button>
          </>
        }
      />
    </div>
  );
}

function ExemploGaveta() {
  const [lado, setLado] = useState<"esquerda" | "baixo" | "direita" | null>(null);
  const [filial, setFilial] = useState("centro");
  const [tipo, setTipo] = useState("todos");
  const fechar = () => setLado(null);
  return (
    <div className="flex flex-col gap-4">
      <Linha>
        <Button variante="solido" icone={<Icone de={IconeMenu} />} onClick={() => setLado("esquerda")}>
          Menu
        </Button>
        <Button onClick={() => setLado("baixo")}>Filtros</Button>
        <Button onClick={() => setLado("direita")}>Detalhe</Button>
      </Linha>
      <Gaveta aberto={lado === "esquerda"} aoFechar={fechar} lado="esquerda" titulo="Menu">
        <Sidebar
          marca={{ nome: "Moto Rápida" }}
          seletorDeFilial={<SeletorDeFilial filiais={FILIAIS} valor={filial} aoMudar={setFilial} permiteTodas />}
          grupos={[
            {
              itens: [
                { rotulo: "Visão geral", href: "#", icone: <Icone de={LayoutGrid} />, ativo: true },
                { rotulo: "Veículos", href: "#", icone: <Icone de={CarFront} />, contador: 86 },
                { rotulo: "Locações", href: "#", icone: <Icone de={FileText} />, contador: 42 },
                { rotulo: "Clientes", href: "#", icone: <Icone de={Users} /> },
              ],
            },
          ]}
        />
      </Gaveta>
      <Gaveta
        aberto={lado === "baixo"}
        aoFechar={fechar}
        lado="baixo"
        titulo="Filtros"
        acoes={
          <>
            <Button variante="quieto" onClick={() => setTipo("todos")}>
              Limpar
            </Button>
            <Button variante="solido" onClick={fechar}>
              Ver 42 veículos
            </Button>
          </>
        }
      >
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
      </Gaveta>
      <Gaveta aberto={lado === "direita"} aoFechar={fechar} lado="direita" titulo="Contrato LOC-2841" descricao="Carlos Menezes · Honda CG 160 Fan">
        <p style={{ margin: 0 }}>Devolução prevista para hoje. Diária de R$ 49,90.</p>
      </Gaveta>
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
  "dialogo": ExemploDialogo,
  "gaveta": ExemploGaveta,
  "seletor-de-filial": ExemploSeletorDeFilial,
  "cover": () => <Cover />,
  "data-table": ExemploDataTable,
  "fleet-bar": ExemploFleetBar,
  "kpi-tile": ExemploKpiTile,
  "linha-de-lista": ExemploLinhaDeLista,
  "progress-bar": ExemploProgressBar,
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
