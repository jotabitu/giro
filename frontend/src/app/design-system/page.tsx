import Link from "next/link";
import { Cover } from "@/design-system/components";
import { CATALOGO } from "./catalogo";

export default function IndiceDoDesignSystem() {
  return (
    <>
      <Cover />
      <section className="wl-panel">
        <h2 className="wl-panel__title">Componentes</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {CATALOGO.map((e) => (
            <li key={e.slug}>
              <Link href={`/design-system/${e.slug}`} className="block rounded-lg bg-surface-sunken p-4">
                <span className="text-body-strong">{e.nome}</span>
                <span className="block text-caption text-ink-muted">{e.resumo}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
