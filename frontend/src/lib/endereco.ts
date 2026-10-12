import { useSyncExternalStore } from "react";

// Endereço sem empresa (ADR 0008): a empresa vem do subdomínio (`motorapida.giro...`). Em `localhost`,
// no IP e em `admin.*` (painel da plataforma) não há schema de locadora, e o login da empresa responderia 404.
export function enderecoSemEmpresa(hostname: string): boolean {
  const host = hostname.toLowerCase();
  if (host === "localhost" || host === "[::1]" || host === "::1") return true;
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return true;
  return host === "admin" || host.startsWith("admin.");
}

const semAssinatura = () => () => {};

/** `true` no navegador quando o endereço aberto não é de uma locadora; no servidor e na hidratação, `false`. */
export function useEnderecoSemEmpresa(): boolean {
  return useSyncExternalStore(
    semAssinatura,
    () => enderecoSemEmpresa(window.location.hostname),
    () => false,
  );
}
