// Controle do ambiente do E2E: banco com o seed novo e relógio do backend (ADR 0021).
//
// Tudo passa pelo `docker compose` da raiz do repositório e vale só para o desenvolvimento: o `prod.py` recusa
// subir com GIRO_DATA_REFERENCIA, e o override `infra/e2e/docker-compose.e2e.yml` nunca entra em outro ambiente.
//
// Seed novo a cada execução: o primeiro uso monta o seed num banco-modelo (`giro_e2e_<hash>`, o hash vem dos arquivos
// do seed e das migrações) e cada execução recria o banco `giro` a partir dele, em poucos segundos.
// Relógio: a data vem de GIRO_DATA_REFERENCIA; a hora é a real de São Paulo (ADR 0021, item 2). O fluxo
// usa a hora de agora como hora de retirada, por isso as duas datas fecham na tolerância da LOC-10.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readdirSync, statSync } from "node:fs";
import http from "node:http";
import path from "node:path";

const RAIZ = path.resolve(__dirname, "../../..");
const ARQUIVOS = ["-f", "docker-compose.yml", "-f", path.join("infra", "e2e", "docker-compose.e2e.yml")];
const USUARIO_DB = process.env.POSTGRES_USER ?? "giro";
const BANCO = process.env.POSTGRES_DB ?? "giro";
const SUBDOMINIO = process.env.E2E_SUBDOMINIO ?? "motorapida";
const PORTA_BACKEND = process.env.E2E_PORTA_BACKEND ?? process.env.PORTA_BACKEND ?? "8000";
const PORTA_FRONTEND = process.env.E2E_PORTA_FRONTEND ?? "3000";

export const DATA_DO_SEED = "2026-10-07";

function compose(args: string[], opcoes: { entrada?: string; env?: Record<string, string>; tolerarErro?: boolean } = {}): string {
  try {
    return execFileSync("docker", ["compose", ...ARQUIVOS, ...args], {
      cwd: RAIZ,
      input: opcoes.entrada,
      env: { ...process.env, ...opcoes.env },
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (erro) {
    if (opcoes.tolerarErro) return "";
    const e = erro as { stderr?: string; message: string };
    throw new Error(`docker compose ${args.join(" ")} falhou:\n${e.stderr ?? e.message}`);
  }
}

function psql(sql: string, banco = "postgres"): string {
  return compose(["exec", "-T", "db", "psql", "-U", USUARIO_DB, "-d", banco, "-v", "ON_ERROR_STOP=1", "-At", "-c", sql]);
}

/** Resume o que define o banco semeado: se o seed ou uma migração mudar, o modelo é refeito. */
function impressaoDoSeed(): string {
  const arquivos: string[] = [];
  const varrer = (pasta: string, filtro: (caminho: string) => boolean) => {
    for (const nome of readdirSync(pasta, { withFileTypes: true })) {
      const caminho = path.join(pasta, nome.name);
      if (nome.isDirectory()) {
        if (nome.name !== "__pycache__" && nome.name !== "tests") varrer(caminho, filtro);
      } else if (filtro(caminho)) {
        arquivos.push(`${path.relative(RAIZ, caminho)}:${statSync(caminho).size}`);
      }
    }
  };
  varrer(path.join(RAIZ, "backend", "seed"), (c) => !c.endsWith(".pyc"));
  varrer(path.join(RAIZ, "backend", "apps"), (c) => c.includes(`${path.sep}migrations${path.sep}`) && c.endsWith(".py"));
  return createHash("sha1").update(arquivos.sort().join("\n")).digest("hex").slice(0, 8);
}

const nomeDoModelo = () => `${BANCO}_e2e_${impressaoDoSeed()}`;

/** Espera a API subir. Com `dataEsperada`, espera a rota de ambiente da empresa dizer o dia; sem ela, basta o servidor responder (banco ainda sem empresa). */
function esperarApi(dataEsperada: string | null, limiteMs = 240_000): Promise<void> {
  const fim = Date.now() + limiteMs;
  const tentar = (resolver: () => void, rejeitar: (e: Error) => void) => {
    const pedido = http.get(
      { host: "127.0.0.1", port: Number(PORTA_BACKEND), path: "/api/ambiente/", headers: { host: `${SUBDOMINIO}.localhost:${PORTA_FRONTEND}` }, timeout: 3000 },
      (resposta) => {
        let corpo = "";
        resposta.on("data", (p) => (corpo += p));
        resposta.on("end", () => {
          try {
            if (dataEsperada === null) return resolver();
            const j =JSON.parse(corpo) as { hoje?: string; data_simulada?: boolean };
            if (resposta.statusCode === 200 && j.hoje === dataEsperada && j.data_simulada === true) return resolver();
          } catch {
            /* ainda subindo */
          }
          repetir();
        });
      },
    );
    pedido.on("error", repetir);
    pedido.on("timeout", () => pedido.destroy());
    function repetir() {
      if (Date.now() > fim) return rejeitar(new Error(`A API não respondeu com a data ${dataEsperada} em ${limiteMs / 1000} s.`));
      setTimeout(() => tentar(resolver, rejeitar), 1000);
    }
  };
  return new Promise((resolver, rejeitar) => tentar(resolver, rejeitar));
}

function subirComData(data: string) {
  compose(["up", "-d", "--force-recreate", "--no-deps", "backend", "worker", "beat"], { env: { E2E_DATA_REFERENCIA: data } });
}

/** Troca o dia do relógio de backend, worker e beat (a hora continua a real). Leva uns 20 s. */
export async function definirData(data: string) {
  subirComData(data);
  await esperarApi(data);
}

function semear(): void {
  compose(["up", "-d", "db", "redis"]);
  // Banco vazio: o backend aplica as migrações ao subir (RODAR_MIGRACOES) e depois o seed roda dentro dele.
  compose(["stop", "backend", "worker", "beat"], { tolerarErro: true });
  psql(`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${BANCO}' AND pid <> pg_backend_pid()`);
  psql(`DROP DATABASE IF EXISTS ${BANCO}`);
  psql(`CREATE DATABASE ${BANCO}`);
  compose(["up", "-d", "--force-recreate", "--no-deps", "backend"], { env: { E2E_DATA_REFERENCIA: DATA_DO_SEED } });
}

/** Garante o banco-modelo com o seed da Moto Rápida. Só monta se o modelo desta versão do seed não existir. */
async function garantirModelo(): Promise<string> {
  const modelo = nomeDoModelo();
  compose(["up", "-d", "db", "redis"]);
  if (psql(`SELECT 1 FROM pg_database WHERE datname = '${modelo}'`).trim() === "1") return modelo;

  console.log(`[e2e] Montando o banco-modelo ${modelo} com o seed da Moto Rápida (só na primeira vez ou quando o seed muda).`);
  semear();
  await esperarApi(null);
  compose(["exec", "-T", "backend", "python", "manage.py", "seed_moto_rapida"]);
  compose(["stop", "backend", "worker", "beat"]);
  psql(`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${BANCO}' AND pid <> pg_backend_pid()`);
  for (const antigo of psql(`SELECT datname FROM pg_database WHERE datname LIKE '${BANCO}_e2e_%'`).split("\n").filter(Boolean)) {
    psql(`DROP DATABASE IF EXISTS ${antigo}`);
  }
  psql(`CREATE DATABASE ${modelo} TEMPLATE ${BANCO}`);
  return modelo;
}

/** Banco com o seed novo e o relógio em 07 out. Chame uma vez por fluxo. */
export async function restaurarSeed() {
  const modelo = await garantirModelo();
  compose(["stop", "backend", "worker", "beat"], { tolerarErro: true });
  psql(`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${BANCO}' AND pid <> pg_backend_pid()`);
  psql(`DROP DATABASE IF EXISTS ${BANCO}`);
  psql(`CREATE DATABASE ${BANCO} TEMPLATE ${modelo}`);
  // Cache da marca, sessões e filas ficam no Redis: recomeçam do zero com o banco.
  compose(["exec", "-T", "redis", "redis-cli", "FLUSHALL"]);
  subirComData(DATA_DO_SEED);
  await esperarApi(DATA_DO_SEED);
}

/**
 * Roda um trecho de Python no `manage.py shell` do backend e devolve o que ele imprimiu.
 * Só para o que a tela ainda não oferece (ver CA-025-05). A saída que importa vem em linhas `CHAVE=valor`.
 */
export function executarNoBackend(codigo: string): Record<string, string> {
  const saida = compose(["exec", "-T", "backend", "python", "manage.py", "shell"], { entrada: codigo });
  const valores: Record<string, string> = {};
  for (const linha of saida.split(/\r?\n/)) {
    const achou = /^([A-Z_]+)=(.*)$/.exec(linha);
    if (achou?.[1] !== undefined) valores[achou[1]] = achou[2] ?? "";
  }
  return valores;
}

export const SUBDOMINIO_DA_EMPRESA = SUBDOMINIO;
