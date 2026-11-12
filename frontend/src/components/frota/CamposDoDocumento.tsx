"use client";

import { useId } from "react";
import type { UseFormRegister } from "react-hook-form";
import { Panel, TextField } from "@/design-system";
import { COMBUSTIVEIS, ESPECIES, type ValoresVeiculo } from "@/lib/veiculos";
import { CampoSelecao } from "@/components/lista/CampoSelecao";

type Nome = keyof ValoresVeiculo;

function AreaDeTexto({ rotulo, dica, erro, ...resto }: { rotulo: string; dica?: string; erro?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  const apoio = erro ?? dica;
  return (
    <div className={`wl-field wl-field--cheio ${erro ? "wl-field--error" : ""}`}>
      <label className="wl-field__label" htmlFor={id}>
        {rotulo}
      </label>
      <textarea id={id} className="wl-input h-auto resize-none pt-3" rows={3} aria-invalid={erro ? true : undefined} {...resto} />
      {apoio && <span className="wl-field__hint">{apoio}</span>}
    </div>
  );
}

/**
 * Combustível, dados do CRLV-e, rastreador e anotações (VEI-09), no cadastro e no editar. Todos opcionais; o formato é conferido pela API
 * e o erro volta no campo. O número do motor e as observações só aparecem quando a API os mandou (administrador e gerente, CA-421-12).
 */
export function CamposDoDocumento({
  register,
  erro,
  dica,
  comMotorEObservacoes,
}: {
  register: UseFormRegister<ValoresVeiculo>;
  erro: (nome: Nome) => string | undefined;
  /** "Lido do documento" enquanto o valor é o que veio do CRLV-e. */
  dica: (nome: Nome, padrao?: string) => string | undefined;
  comMotorEObservacoes: boolean;
}) {
  return (
    <>
      <Panel titulo="Dados do documento">
        <div className="grid gap-4 md:grid-cols-2">
          <CampoSelecao rotulo="Combustível" vazio="Não informado" opcoes={COMBUSTIVEIS.map((c) => ({ valor: c.valor, rotulo: c.rotulo }))} dica={dica("combustivel")} erro={erro("combustivel")} {...register("combustivel")} />
          <CampoSelecao rotulo="Espécie" vazio="Não informada" opcoes={ESPECIES.map((e) => ({ valor: e.valor, rotulo: e.rotulo }))} dica={dica("especie")} erro={erro("especie")} {...register("especie")} />
          <TextField cheio rotulo="Tipo no CRLV-e" autoComplete="off" maxLength={30} dica={dica("tipo_documento", "Como no documento: Motocicleta, Automóvel. Não é o tipo do veículo, que fica em Uso na frota.")} erro={erro("tipo_documento")} {...register("tipo_documento")} />
          <TextField cheio rotulo="Carroceria" autoComplete="off" maxLength={30} dica={dica("carroceria")} erro={erro("carroceria")} {...register("carroceria")} />
          <TextField cheio mono rotulo="Potência (cv)" inputMode="numeric" dica={dica("potencia_cv")} erro={erro("potencia_cv")} {...register("potencia_cv")} />
          <TextField cheio mono rotulo="Cilindrada (cc)" inputMode="numeric" dica={dica("cilindrada_cc")} erro={erro("cilindrada_cc")} {...register("cilindrada_cc")} />
          <TextField cheio mono rotulo="Lotação (pessoas)" inputMode="numeric" dica={dica("lotacao", "Com o motorista")} erro={erro("lotacao")} {...register("lotacao")} />
          <TextField cheio mono rotulo="Peso bruto total (kg)" inputMode="numeric" dica={dica("peso_bruto_kg")} erro={erro("peso_bruto_kg")} {...register("peso_bruto_kg")} />
          {comMotorEObservacoes && (
            <>
              <TextField cheio mono rotulo="Número do motor" autoComplete="off" autoCapitalize="characters" maxLength={21} dica={dica("numero_motor")} erro={erro("numero_motor")} {...register("numero_motor")} />
              <div className="md:col-span-2">
                <AreaDeTexto rotulo="Observações do CRLV-e" maxLength={500} dica={dica("observacoes_crlv", "Como no documento, por exemplo alienação fiduciária. Só informa, não bloqueia nada")} erro={erro("observacoes_crlv")} {...register("observacoes_crlv")} />
              </div>
            </>
          )}
        </div>
      </Panel>

      <Panel titulo="Rastreador e anotações">
        <div className="grid gap-4 md:grid-cols-2">
          <TextField cheio mono rotulo="Rastreador · número ou IMEI" autoComplete="off" autoCapitalize="characters" maxLength={20} erro={erro("rastreador_numero")} {...register("rastreador_numero")} />
          <TextField cheio rotulo="Rastreador · empresa" autoComplete="off" maxLength={60} erro={erro("rastreador_empresa")} {...register("rastreador_empresa")} />
          <div className="md:col-span-2">
            <AreaDeTexto rotulo="Anotações" maxLength={500} dica="Da locadora, por exemplo risco no tanque. Avaria vai na vistoria" erro={erro("anotacoes")} {...register("anotacoes")} />
          </div>
        </div>
      </Panel>
    </>
  );
}
