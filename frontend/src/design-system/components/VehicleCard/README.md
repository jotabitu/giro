# VehicleCard

Card de destaque com a foto do veículo ao fundo e um painel branco sobreposto com modelo, cliente, andamento do contrato e três números-chave.

- O consumidor fornece a foto (proporção livre, cobre a área com `object-fit: cover`; sem foto, aparece o desenho neutro sobre `surface-sunken`), placa, status, modelo, cliente e código do contrato, o progresso (dias corridos sobre dias contratados) e três fatos curtos.
- No canto superior: placa em pílula `surface` à esquerda e status à direita.
- A barra de progresso é `solid` sobre `surface-sunken`, com o texto ao lado ("28 de 30 dias").
- Use para o veículo que merece atenção agora (devolução hoje, revisão vencida), não como item de lista.

## Em React

Código em `frontend/src/design-system/components/VehicleCard/VehicleCard.tsx`; preview em `/design-system/vehicle-card`.

```tsx
import { IconButton, Icone, VehicleCard } from "@/design-system";

<VehicleCard
  placa="QXA-4B21" status="Devolução hoje" modelo="Honda CG 160 Fan" cliente="Carlos Menezes" contrato="LOC-2841"
  diasCorridos={28} diasContratados={30}
  fatos={[{ rotulo: "Diária", valor: "R$ 49,90" }, { rotulo: "Rodados", valor: "2.140 km" }, { rotulo: "Próxima revisão", valor: "15.000 km" }]}
  acao={<IconButton aria-label="Abrir contrato" icone={<Icone de={ArrowUpRight} />} quieto compacto />}
/>
```

`fotoSrc` é opcional; sem ela aparece o desenho neutro, escolhido por `tipo` (`moto`, padrão, ou `carro`; `IlustracaoVeiculo`, SVG próprio com `currentColor`). A barra de progresso é só visual: os dias vêm da API. `tomDoStatus` segue a tabela do StatusBadge (padrão `atencao`).
