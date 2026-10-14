// Formulário de filial (docs/api/filiais.md). A API confere CNPJ, CEP, UF e horário; aqui só o formato do formulário e do corpo.
import type { CorpoDaFilial, DiaDaSemana, FilialDetalhada, HorarioDaFilial, Intervalo } from "@/lib/api";
import { soDigitos } from "@/lib/formatos";

export const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];

/** Uma linha da tela de horário: a semana inteira (seg a sex), o sábado ou o domingo. */
export type LinhaDeHorario = { fechado: boolean; abre: string; fecha: string };
export type HorarioDoFormulario = { semana: LinhaDeHorario; sab: LinhaDeHorario; dom: LinhaDeHorario };

export type ValoresDaFilial = {
  nome: string;
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
  horario: HorarioDoFormulario;
};

const DIAS_DA_SEMANA: DiaDaSemana[] = ["seg", "ter", "qua", "qui", "sex"];

const linha = (d: Intervalo[]): LinhaDeHorario => (d[0] ? { fechado: false, abre: d[0].abre, fecha: d[0].fecha } : { fechado: true, abre: "08:00", fecha: "18:00" });

export const HORARIO_INICIAL: HorarioDoFormulario = {
  semana: { fechado: false, abre: "08:00", fecha: "18:00" },
  sab: { fechado: false, abre: "08:00", fecha: "12:00" },
  dom: { fechado: true, abre: "08:00", fecha: "12:00" },
};

export const VALORES_INICIAIS_DA_FILIAL: ValoresDaFilial = {
  nome: "",
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
  horario: HORARIO_INICIAL,
};

export const horarioDoFormulario = (h: HorarioDaFilial): HorarioDoFormulario => ({ semana: linha(h.seg), sab: linha(h.sab), dom: linha(h.dom) });

/** A tela edita seg a sex juntos e um intervalo por dia. Salvar o horário iguala os dias úteis e troca dois intervalos por um. */
export function horarioPedeCuidado(h: HorarioDaFilial): boolean {
  const igual = (a: Intervalo[], b: Intervalo[]) => JSON.stringify(a) === JSON.stringify(b);
  return DIAS_DA_SEMANA.some((d) => !igual(h[d], h.seg)) || (Object.values(h) as Intervalo[][]).some((d) => d.length > 1);
}

export function horarioDaApi(h: HorarioDoFormulario): HorarioDaFilial {
  const dia = (l: LinhaDeHorario): Intervalo[] => (l.fechado ? [] : [{ abre: l.abre, fecha: l.fecha }]);
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
    horario: horarioDoFormulario(f.horario),
  };
}

const ouNulo = (t: string): string | null => (t.trim() === "" ? null : t.trim());

/** Corpo do POST/PATCH: CEP e telefones só com dígitos, opcionais vazios como `null`. */
export function corpoDaFilial(v: ValoresDaFilial): CorpoDaFilial {
  return {
    nome: v.nome.trim(),
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
    horario: horarioDaApi(v.horario),
  };
}

/** Os obrigatórios do contrato: nome, endereço (menos complemento) e horário (sempre tem). */
export const filialCompleta = (v: ValoresDaFilial): boolean => [v.nome, v.cep, v.logradouro, v.numero, v.bairro, v.cidade, v.uf].every((t) => t.trim() !== "");

/** Ano de uma data AAAA-MM-DD. */
export const anoDe = (iso: string): number => Number(iso.slice(0, 4));
