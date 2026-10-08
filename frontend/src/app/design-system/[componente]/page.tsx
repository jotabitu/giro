import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CATALOGO } from "../catalogo";
import { ExemploDe } from "../exemplos";

type Params = { componente: string };

export function generateStaticParams(): Params[] {
  return CATALOGO.map((e) => ({ componente: e.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { componente } = await params;
  const e = CATALOGO.find((x) => x.slug === componente);
  return { title: e ? `${e.nome} · Design system` : "Design system" };
}

export default async function PreviewDoComponente({ params }: { params: Promise<Params> }) {
  const { componente } = await params;
  const e = CATALOGO.find((x) => x.slug === componente);
  if (!e) notFound();
  return (
    <>
      <div>
        <h1 className="text-display">{e.nome}</h1>
        <p className="text-caption text-ink-muted">{e.resumo}</p>
        <Link href="/design-system" className="text-caption underline">
          Todos os componentes
        </Link>
      </div>
      <div className="rounded-xl bg-surface p-6">
        <ExemploDe slug={e.slug} />
      </div>
    </>
  );
}
