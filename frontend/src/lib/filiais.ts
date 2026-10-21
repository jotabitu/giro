// Formulário de filial (docs/api/filiais.md). A API confere CNPJ, CEP, UF e horário; aqui só o formato do formulário e do corpo.
import type { CorpoDaFilial, DiaDaSemana, FilialDetalhada, HorarioDaFilial, Intervalo } from "@/lib/api";
import { soDigitos } from "@/lib/formatos";
import { centavosDoTexto, textoDeCentavos } from "@/lib/veiculos";

export const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];

export type SegundoIntervalo = { abre: string; fecha: string };
/** Uma linha da tela de horário: a semana inteira (seg a sex), o sábado ou o domingo, com até 2 intervalos (FIL-03). */
export type LinhaDeHorario = { fechado: boolean; abre: string; fecha: string; segundo?: SegundoIntervalo };
export type HorarioDoFormulario = { semana: LinhaDeHorario; sab: LinhaDeHorario; dom: LinhaDeHorario };

export type ValoresDaFilial = {
  nome: string;
  nomeCurto: string;
  matriz: boolean;
  cnpj: string;
  inscricaoEstadual: string;
  inscricaoMunicipal: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  uf: string;
  telefone: string;
  whatsapp: string;
  email: string;
  precoLitro: string;
  horario: HorarioDoFormulario;
};

const DIAS_DA_SEMANA: DiaDaSemana[] = ["seg", "ter", "qua", "qui", "sex"];

const linha = (d: Intervalo[]): LinhaDeHorario => {
  const primeiro = d[0];
  if (!primeiro) return { fechado: true, abre: "08:00", fecha: "18:00" };
  const segundo = d[1];
  return segundo
    ? { fechado: false, abre: primeiro.abre, fecha: primeiro.fecha, segundo: { abre: segundo.abre, fecha: segundo.fecha } }
    : { fechado: false, abre: primeiro.abre, fecha: primeiro.fecha };
};

/** Resumo de uma linha de horário no celular ("08:00 – 12:00 · 14:00 – 18:00" ou "Fechado"). */
export function resumoDaLinha(l: LinhaDeHorario): string {
  if (l.fechado) return "Fechado";
  return l.segundo ? `${l.abre} – ${l.fecha} · ${l.segundo.abre} – ${l.segundo.fecha}` : `${l.abre} – ${l.fecha}`;
}

export const HORARIO_INICIAL: HorarioDoFormulario = {
  semana: { fechado: false, abre: "08:00", fecha: "18:00" },
  sab: { fechado: false, abre: "08:00", fecha: "12:00" },
  dom: { fechado: true, abre: "08:00", fecha: "12:00" },
};

export const VALORES_INICIAIS_DA_FILIAL: ValoresDaFilial = {
  nome: "",
  nomeCurto: "",
  matriz: false,
  cnpj: "",
  inscricaoEstadual: "",
  inscricaoMunicipal: "",
  cep: "",
  logradouro: "",
  numero: "",
  complemento: "",
  bairro: "",
  cidade: "",
  uf: "CE",
  telefone: "",
  whatsapp: "",
  email: "",
  precoLitro: "",
  horario: HORARIO_INICIAL,
};

export const horarioDoFormulario = (h: HorarioDaFilial): HorarioDoFormulario => ({ semana: linha(h.seg), sab: linha(h.sab), dom: linha(h.dom) });

/** A tela edita seg a sex juntos e até dois intervalos por dia. Salvar o horário iguala os dias úteis. */
export function horarioPedeCuidado(h: HorarioDaFilial): boolean {
  const igual = (a: Intervalo[], b: Intervalo[]) => JSON.stringify(a) === JSON.stringify(b);
  return DIAS_DA_SEMANA.some((d) => !igual(h[d], h.seg)) || (Object.values(h) as Intervalo[][]).some((d) => d.length > 2);
}

export function horarioDaApi(h: HorarioDoFormulario): HorarioDaFilial {
  const dia = (l: LinhaDeHorario): Intervalo[] =>
    l.fechado ? [] : l.segundo ? [{ abre: l.abre, fecha: l.fecha }, { abre: l.segundo.abre, fecha: l.segundo.fecha }] : [{ abre: l.abre, fecha: l.fecha }];
  const semana = dia(h.semana);
  return { seg: semana, ter: semana, qua: semana, qui: semana, sex: semana, sab: dia(h.sab), dom: dia(h.dom) };
}

export const mascaraTelefone = (t: string): string => {
  const d = soDigitos(t).slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
};

export function valoresDaFilial(f: FilialDetalhada): ValoresDaFilial {
  return {
    nome: f.nome,
    nomeCurto: f.nome_curto && f.nome_curto !== f.nome ? f.nome_curto : "",
    matriz: f.matriz,
    cnpj: f.cnpj ?? "",
    inscricaoEstadual: f.inscricao_estadual ?? "",
    inscricaoMunicipal: f.inscricao_municipal ?? "",
    cep: f.endereco.cep,
    logradouro: f.endereco.logradouro,
    numero: f.endereco.numero,
    complemento: f.endereco.complemento ?? "",
    bairro: f.endereco.bairro,
    cidade: f.endereco.cidade,
    uf: f.endereco.uf,
    telefone: f.contato.telefone ?? "",
    whatsapp: f.contato.whatsapp ?? "",
    email: f.contato.email ?? "",
    precoLitro: f.preco_litro_centavos != null ? textoDeCentavos(f.preco_litro_centavos) : "",
    horario: horarioDoFormulario(f.horario),
  };
}

const ouNulo = (t: string): string | null => (t.trim() === "" ? null : t.trim());

/** Corpo do POST/PATCH: CEP e telefones só com dígitos, opcionais vazios como `null`. */
export function corpoDaFilial(v: ValoresDaFilial): CorpoDaFilial {
  return {
    nome: v.nome.trim(),
    nome_curto: ouNulo(v.nomeCurto),
    matriz: v.matriz,
    cnpj: ouNulo(soDigitos(v.cnpj)),
    inscricao_estadual: ouNulo(v.inscricaoEstadual),
    inscricao_municipal: ouNulo(v.inscricaoMunicipal),
    endereco: {
      cep: soDigitos(v.cep),
      logradouro: v.logradouro.trim(),
      numero: v.numero.trim(),
      complemento: ouNulo(v.complemento),
      bairro: v.bairro.trim(),
      cidade: v.cidade.trim(),
      uf: v.uf,
    },
    contato: { telefone: ouNulo(soDigitos(v.telefone)), whatsapp: ouNulo(soDigitos(v.whatsapp)), email: ouNulo(v.email.toLowerCase()) },
    preco_litro_centavos: v.precoLitro.trim() === "" ? null : centavosDoTexto(v.precoLitro),
    horario: horarioDaApi(v.horario),
  };
}

/** Os obrigatórios do contrato: nome, endereço (menos complemento) e horário (sempre tem). */
export const filialCompleta = (v: ValoresDaFilial): boolean => [v.nome, v.cep, v.logradouro, v.numero, v.bairro, v.cidade, v.uf].every((t) => t.trim() !== "");

/** Ano de uma data AAAA-MM-DD. */
export const anoDe = (iso: string): number => Number(iso.slice(0, 4));
