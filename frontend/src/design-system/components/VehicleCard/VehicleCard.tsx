import type { ReactNode } from "react";
import { StatusBadge, type TomStatus } from "../StatusBadge/StatusBadge";
import { IlustracaoVeiculo, type TipoVeiculo } from "./IlustracaoVeiculo";

export type FatoVeiculo = { rotulo: string; valor: string };

/** Veículo que merece atenção agora (devolução hoje, revisão vencida). Não é item de lista. */
export function VehicleCard({
  fotoSrc,
  tipo = "moto",
  placa,
  status,
  tomDoStatus = "atencao",
  modelo,
  cliente,
  contrato,
  diasCorridos,
  diasContratados,
  fatos,
  acao,
}: {
  /** Sem foto, aparece o desenho neutro sobre surface-sunken. */
  fotoSrc?: string;
  /** Escolhe a ilustração do card sem foto. */
  tipo?: TipoVeiculo;
  placa: string;
  status: string;
  tomDoStatus?: TomStatus;
  modelo: string;
  cliente: string;
  /** Código legível: LOC-2841. */
  contrato: string;
  diasCorridos: number;
  diasContratados: number;
  /** Três números-chave, já formatados. */
  fatos: readonly [FatoVeiculo, FatoVeiculo, FatoVeiculo];
  /** Botão de ícone que abre o contrato. */
  acao?: ReactNode;
}) {
  const progresso = diasContratados > 0 ? Math.min(100, Math.round((diasCorridos / diasContratados) * 100)) : 0;
  return (
    <article className="wl-vcard">
      <div className="wl-vcard__media">
        {fotoSrc ? (
          // eslint-disable-next-line @next/next/no-img-element -- foto do veículo vem de URL externa (S3)
          <img src={fotoSrc} alt={`${modelo}, placa ${placa}`} />
        ) : (
          <div className="wl-vcard__placeholder" aria-hidden="true">
            <IlustracaoVeiculo tipo={tipo} />
          </div>
        )}
        <div className="wl-vcard__top">
          <StatusBadge tom="superficie">
            <span className="wl-mono" style={{ fontWeight: 500 }}>
              {placa}
            </span>
          </StatusBadge>
          <StatusBadge tom={tomDoStatus} ponto={tomDoStatus === "atencao"}>
            {status}
          </StatusBadge>
        </div>
        <div className="wl-vcard__info">
          <div className="wl-vcard__name">
            <div>
              <h3 className="wl-vcard__model">{modelo}</h3>
              <div className="wl-muted" style={{ fontSize: 14 }}>
                {cliente} · contrato {contrato}
              </div>
            </div>
            {acao}
          </div>
          <div className="wl-progress">
            <div className="wl-progress__track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progresso} aria-label="Andamento do contrato">
              <div className="wl-progress__fill" style={{ width: `${progresso}%` }} />
            </div>
            {diasCorridos} de {diasContratados} dias
          </div>
          <dl className="wl-facts" style={{ margin: 0 }}>
            {fatos.map((f) => (
              <div key={f.rotulo}>
                <dt>{f.rotulo}</dt>
                <dd>{f.valor}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </article>
  );
}
