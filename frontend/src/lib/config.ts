// Navegador usa NEXT_PUBLIC_API_URL; o servidor Next (SSR) usa API_URL_INTERNA.
// Nunca coloque segredo em variável NEXT_PUBLIC_*.
const PADRAO = "http://localhost:8000";

export function urlDaApi(): string {
  const url =
    typeof window === "undefined"
      ? (process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL)
      : process.env.NEXT_PUBLIC_API_URL;
  return (url || PADRAO).replace(/\/+$/, "");
}
