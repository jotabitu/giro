import type { CSSProperties } from "react";
import { hexValido } from "@/design-system";
import type { MarcaSimulada } from "@/lib/api";

/** Variáveis da marca só neste bloco, com os valores que a API calculou (nada de conta de cor aqui). */
export function variaveisDaPrevia(m: Pick<MarcaSimulada, "cor" | "cor_sobre" | "cor_suave">): CSSProperties {
  if (![m.cor, m.cor_sobre, m.cor_suave].every(hexValido)) return {};
  return { "--brand": m.cor, "--on-brand": m.cor_sobre, "--brand-soft": m.cor_suave } as CSSProperties;
}

export function LogoOuIniciais({ logoUrl, iniciais, tamanho, raio = 20, fonte = 22 }: { logoUrl: string | null; iniciais: string; tamanho: number; raio?: number; fonte?: number }) {
  return (
    <div className="wl-logo-slot" aria-hidden="true" style={{ width: tamanho, height: tamanho, borderRadius: raio, fontSize: fonte }}>
      {logoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- logo do usuário (S-12): sempre <img>, nunca inline
        <img src={logoUrl} alt="" width={tamanho} height={tamanho} style={{ borderRadius: "inherit", objectFit: "contain", width: "100%", height: "100%" }} />
      ) : (
        iniciais
      )}
    </div>
  );
}

/** Admin-Marca, "Prévia": a tela de entrada vista pelo cliente, com a cor, o nome e o logo escolhidos. */
export function PreviaDaMarca({ marca, logoUrl }: { marca: MarcaSimulada; logoUrl: string | null }) {
  return (
    <div className="mx-auto w-60 rounded-[36px] bg-canvas p-[18px] shadow-[inset_0_0_0_8px_var(--solid)] md:w-[260px]" style={variaveisDaPrevia(marca)} role="img" aria-label={`Prévia da tela de entrada de ${marca.nome_exibicao}`}>
      <div className="flex flex-col items-center gap-3.5 px-2.5 py-[18px] text-center">
        <LogoOuIniciais logoUrl={logoUrl} iniciais={marca.iniciais} tamanho={56} raio={18} fonte={18} />
        <div className="text-heading">{marca.nome_exibicao}</div>
        <div className="h-11 w-full rounded-[14px] bg-surface" />
        <div className="h-11 w-full rounded-[14px] bg-surface" />
        <div className="grid h-11 w-full place-items-center rounded-full bg-brand font-medium text-on-brand">Entrar</div>
        <div className="text-[11px] text-ink-muted">contrato e recibos também saem com a sua marca</div>
      </div>
    </div>
  );
}
