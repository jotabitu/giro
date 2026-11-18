// Landing pública (T-489): em "/" o domínio da plataforma mostra a landing; o subdomínio de uma
// empresa (suaempresa.giro.ceo) continua indo para /entrar. localhost entra como domínio da
// plataforma no desenvolvimento (a empresa do seed abre em <subdominio>.localhost).
const HOSTS_DA_LANDING = new Set([
  "giro.ceo",
  "www.giro.ceo",
  "homolog.giro.ceo",
  "www.homolog.giro.ceo",
  "localhost",
  "127.0.0.1",
]);

/** Nome do host sem porta e em minúsculas ("Giro.ceo:443" vira "giro.ceo"). */
function semPorta(host: string): string {
  return host.trim().toLowerCase().replace(/:\d+$/, "");
}

export function mostraLanding(host: string | null | undefined): boolean {
  if (!host) return false;
  return HOSTS_DA_LANDING.has(semPorta(host));
}
