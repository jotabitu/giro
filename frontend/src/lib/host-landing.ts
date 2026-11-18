// Landing pública (T-489): em "/" o domínio da plataforma mostra a landing; o subdomínio de uma
// empresa (suaempresa.<DOMINIO_BASE>) continua indo para /entrar. A lista vem de DOMINIO_BASE (o
// mesmo do backend e do proxy), lida em execução pelo middleware: o domínio, o www. e localhost
// (no desenvolvimento a empresa do seed abre em <subdominio>.localhost).

/** Nome do host sem porta e em minúsculas ("Giro.ceo:443" vira "giro.ceo"). */
function semPorta(host: string): string {
  return host.trim().toLowerCase().replace(/:\d+$/, "");
}

export function hostsDaLanding(dominioBase: string | undefined): Set<string> {
  const hosts = new Set(["localhost", "127.0.0.1"]);
  const dominio = dominioBase ? semPorta(dominioBase) : "";
  if (dominio && dominio !== "localhost") {
    hosts.add(dominio);
    hosts.add(`www.${dominio}`);
  }
  return hosts;
}

export function mostraLanding(host: string | null | undefined, dominioBase: string | undefined = process.env.DOMINIO_BASE): boolean {
  if (!host) return false;
  return hostsDaLanding(dominioBase).has(semPorta(host));
}
