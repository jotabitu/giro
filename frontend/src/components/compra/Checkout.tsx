"use client";

import { CircleCheck, Info } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, TextField } from "@/design-system/components";
import { Icone } from "@/design-system/Icone";
import { compraApi } from "@/lib/api/compra";
import { ErroApi } from "@/lib/api/tipos";
import type { CatalogoDaCompra, PedidoCriado, PlanoAVenda, SituacaoDoCnpj } from "@/lib/api/tipos-compra";
import { diaEMes, mascararCelular, mascararCnpj, reais, soDigitos } from "@/lib/compra";
import { mensagemDoErro } from "@/lib/erros";
import type { Ciclo } from "./EscolhaDoPlano";

const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];
const FORMAS = [
  { valor: "cartao", rotulo: "Cartão" },
  { valor: "pix_automatico", rotulo: "Pix" },
  { valor: "boleto", rotulo: "Boleto" },
] as const;
type Forma = (typeof FORMAS)[number]["valor"];
const ESPERA_DA_CHECAGEM_MS = 400;

type Endereco = { subdominio: string; disponivel: boolean; endereco?: string; mensagem?: string; sugestao?: string | null };

const titulo = { margin: "0 0 18px", fontSize: 20, lineHeight: "26px", fontWeight: 600, display: "flex", alignItems: "center", gap: 12 } as const;
const numero = { display: "grid", placeItems: "center", width: 30, height: 30, borderRadius: "50%", background: "var(--surface-sunken)", fontSize: 14 } as const;
const grade = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px 20px" } as const;

function Aviso({ tom, children }: { tom: "success" | "info" | "critical"; children: React.ReactNode }) {
  return (
    <div
      role={tom === "critical" ? "alert" : "status"}
      style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12, padding: "14px 16px", borderRadius: 18, background: `var(--${tom}-soft)`, color: `var(--${tom}-ink)`, fontSize: 15, lineHeight: "22px" }}
    >
      <Icone de={tom === "success" ? CircleCheck : Info} />
      <div>{children}</div>
    </div>
  );
}

/** Tela 2 · Criar conta (`Compra-Checkout`). A API decide tudo: situação do CNPJ (PLT-16), endereço livre e o código no e-mail. */
export function Checkout({
  catalogo,
  plano,
  ciclo,
  aoTrocarPlano,
  aoCriar,
}: {
  catalogo: CatalogoDaCompra;
  plano: PlanoAVenda;
  ciclo: Ciclo;
  aoTrocarPlano: () => void;
  aoCriar: (pedido: PedidoCriado) => void;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [celular, setCelular] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [razao, setRazao] = useState("");
  const [nomeExibicao, setNomeExibicao] = useState("");
  const [cidade, setCidade] = useState("");
  const [uf, setUf] = useState("");
  const [subdominio, setSubdominio] = useState("");
  const [editouEndereco, setEditouEndereco] = useState(false);
  const [forma, setForma] = useState<Forma | null>(null);
  const [aceite, setAceite] = useState(false);
  const [situacao, setSituacao] = useState<SituacaoDoCnpj | null>(null);
  const [endereco, setEndereco] = useState<Endereco | null>(null);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const preenchido = useRef(false);

  // CNPJ completo: a API diz se pode comprar e devolve os dados da Receita para preencher (ADR 0039).
  const digitos = soDigitos(cnpj);
  useEffect(() => {
    setSituacao(null);
    if (digitos.length !== 14) return;
    let vale = true;
    compraApi
      .cnpj(digitos)
      .then((resposta) => {
        if (!vale) return;
        setSituacao(resposta);
        setErros((e) => ({ ...e, "empresa.cnpj": "" }));
        const dados = resposta.dados;
        if (dados && !preenchido.current) {
          preenchido.current = true;
          setRazao((v) => v || dados.razao_social);
          setNomeExibicao((v) => v || dados.nome_fantasia || dados.razao_social);
          setCidade((v) => v || dados.cidade);
          setUf((v) => v || dados.uf);
        }
      })
      .catch((erro: unknown) => {
        if (vale) setErros((e) => ({ ...e, "empresa.cnpj": erro instanceof ErroApi ? (erro.campos?.cnpj ?? erro.message) : mensagemDoErro(erro) }));
      });
    return () => {
      vale = false;
    };
  }, [digitos]);

  // Endereço de acesso: sugerido pelo nome da empresa até a pessoa editar; depois, só conferido (D-430-02).
  const alvoDoEndereco = editouEndereco ? subdominio : nomeExibicao.trim();
  useEffect(() => {
    const pedido = !alvoDoEndereco ? null : editouEndereco ? { subdominio: alvoDoEndereco } : { nome: alvoDoEndereco };
    if (!pedido) return;
    let vale = true;
    const espera = setTimeout(() => {
      compraApi
        .subdominio(pedido)
        .then((r) => {
          if (!vale) return;
          setEndereco(r);
          if (!editouEndereco) setSubdominio(r.subdominio);
          setErros((e) => ({ ...e, "empresa.subdominio": "" }));
        })
        .catch((erro: unknown) => {
          if (vale) setErros((e) => ({ ...e, "empresa.subdominio": erro instanceof ErroApi ? (erro.campos?.subdominio ?? erro.message) : mensagemDoErro(erro) }));
        });
    }, ESPERA_DA_CHECAGEM_MS);
    return () => {
      vale = false;
      clearTimeout(espera);
    };
  }, [alvoDoEndereco, editouEndereco]);

  const bloqueado = situacao?.pode_comprar === false;
  const semTeste = situacao?.teste_gratis === false;
  const preco = ciclo === "anual" ? plano.anual_centavos : plano.mensal_centavos;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErroGeral(null);
    setEnviando(true);
    try {
      const pedido = await compraApi.criarPedido({
        plano: plano.codigo,
        ciclo,
        forma_pagamento: forma,
        administrador: { nome, email, celular: soDigitos(celular), aceita_whatsapp: false },
        empresa: { cnpj: digitos, razao_social: razao, nome_exibicao: nomeExibicao, cidade, uf, subdominio },
        aceite_termos: aceite,
      });
      aoCriar(pedido);
    } catch (erro) {
      if (erro instanceof ErroApi && erro.campos) {
        setErros(erro.campos);
        setErroGeral("Confira os campos destacados.");
      } else if (erro instanceof ErroApi && erro.codigo === "subdominio_em_uso") {
        setErros({ "empresa.subdominio": erro.message });
      } else if (erro instanceof ErroApi && (erro.codigo === "cnpj_em_uso" || erro.codigo === "fatura_anterior_em_atraso")) {
        setErros({ "empresa.cnpj": erro.message });
      } else {
        setErroGeral(mensagemDoErro(erro));
      }
    } finally {
      setEnviando(false);
    }
  }

  const erro = (campo: string) => erros[campo] || undefined;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start", maxWidth: 1240, width: "100%", margin: "0 auto" }}>
      <form onSubmit={enviar} noValidate style={{ flex: "999 1 600px", minWidth: 0, display: "flex", flexDirection: "column", gap: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 40, lineHeight: "44px", fontWeight: 600, letterSpacing: "-0.02em" }}>Crie sua conta</h1>
          <p style={{ margin: "8px 0 0", color: "var(--ink-muted)" }}>Leva 2 minutos. Seu sistema fica pronto logo em seguida.</p>
        </div>

        <section className="wl-panel">
          <h2 style={titulo}>
            <span style={numero}>1</span>Você, administrador da conta
          </h2>
          <div style={grade}>
            <div style={{ gridColumn: "1 / -1" }}>
              <TextField cheio rotulo="Nome completo" value={nome} onChange={(e) => setNome(e.target.value)} erro={erro("administrador.nome")} autoComplete="name" />
            </div>
            <TextField cheio rotulo="E-mail de trabalho" type="email" value={email} onChange={(e) => setEmail(e.target.value)} dica="É por ele que você entra no sistema" erro={erro("administrador.email")} autoComplete="email" />
            <TextField cheio rotulo="Celular com WhatsApp" inputMode="tel" value={celular} onChange={(e) => setCelular(mascararCelular(e.target.value))} erro={erro("administrador.celular")} autoComplete="tel-national" />
          </div>
        </section>

        <section className="wl-panel">
          <h2 style={titulo}>
            <span style={numero}>2</span>Sua empresa
          </h2>
          <div style={grade}>
            <TextField cheio mono rotulo="CNPJ" inputMode="numeric" value={cnpj} onChange={(e) => setCnpj(mascararCnpj(e.target.value))} erro={erro("empresa.cnpj")} />
            <TextField cheio rotulo="Razão social" value={razao} onChange={(e) => setRazao(e.target.value)} erro={erro("empresa.razao_social")} />
            <TextField cheio rotulo="Nome da empresa" value={nomeExibicao} onChange={(e) => setNomeExibicao(e.target.value)} dica="Como aparece para os seus clientes" erro={erro("empresa.nome_exibicao")} />
            <TextField cheio rotulo="Cidade" value={cidade} onChange={(e) => setCidade(e.target.value)} erro={erro("empresa.cidade")} />
            <div className={erro("empresa.uf") ? "wl-field wl-field--error wl-field--cheio" : "wl-field wl-field--cheio"}>
              <label className="wl-field__label" htmlFor="compra-uf">
                UF
              </label>
              <select id="compra-uf" className="wl-input" value={uf} onChange={(e) => setUf(e.target.value)}>
                <option value="">Escolha</option>
                {UFS.map((sigla) => (
                  <option key={sigla} value={sigla}>
                    {sigla}
                  </option>
                ))}
              </select>
              {erro("empresa.uf") && <span className="wl-field__hint">{erro("empresa.uf")}</span>}
            </div>
            <TextField
              cheio
              mono
              rotulo="Endereço de acesso"
              value={subdominio}
              onChange={(e) => {
                setEditouEndereco(true);
                setSubdominio(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""));
              }}
              dica={endereco?.disponivel && endereco.endereco ? endereco.endereco : "Seu endereço no Giro"}
              erro={erro("empresa.subdominio") || (endereco && !endereco.disponivel ? endereco.mensagem : undefined)}
            />
          </div>
          {situacao?.pode_comprar && situacao.dados && (
            <Aviso tom="success">
              <strong style={{ fontWeight: 600 }}>{situacao.dados.razao_social}</strong>
              {situacao.dados.cidade && ` · ${situacao.dados.cidade}, ${situacao.dados.uf}`}
              {situacao.dados.ativo ? " · CNPJ ativo." : "."} Confira os dados acima.
            </Aviso>
          )}
          {situacao?.aviso && <Aviso tom="info">{situacao.aviso}</Aviso>}
          {bloqueado && situacao?.mensagem && <Aviso tom="critical">{situacao.mensagem}</Aviso>}
          {endereco && !endereco.disponivel && endereco.sugestao && (
            <p style={{ margin: "10px 0 0", fontSize: 14 }}>
              <Button
                variante="quieto"
                compacto
                onClick={() => {
                  setEditouEndereco(true);
                  setSubdominio(endereco.sugestao ?? "");
                }}
              >
                Usar {endereco.sugestao}
              </Button>
            </p>
          )}
        </section>

        <section className="wl-panel">
          <h2 style={titulo}>
            <span style={numero}>3</span>Pagamento <span className="wl-badge wl-badge--sm">{semTeste ? "Opcional" : "Opcional durante o teste"}</span>
          </h2>
          <div className="wl-seg" role="group" aria-label="Forma de pagamento">
            {FORMAS.map((f) => (
              <button key={f.valor} type="button" aria-pressed={forma === f.valor} onClick={() => setForma(forma === f.valor ? null : f.valor)}>
                {f.rotulo}
              </button>
            ))}
          </div>
          <p style={{ margin: "14px 0 0", color: "var(--ink-muted)", fontSize: 15 }}>
            Nada é cobrado agora. No cartão, você digita os dados na página segura do parceiro de pagamento, só ao pagar a primeira fatura. Sem escolher, avisamos antes do fim do teste.
          </p>
        </section>

        <label style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <input type="checkbox" checked={aceite} onChange={(e) => setAceite(e.target.checked)} style={{ marginTop: 4 }} />
          <span>Li e aceito os Termos de uso e o Acordo de tratamento de dados.</span>
        </label>
        {erro("aceite_termos") && <p style={{ margin: 0, color: "var(--critical-ink)" }}>{erro("aceite_termos")}</p>}
        {erroGeral && (
          <p role="alert" style={{ margin: 0, color: "var(--critical-ink)" }}>
            {erroGeral}
          </p>
        )}
        <div>
          <Button type="submit" variante="solido" disabled={enviando || bloqueado}>
            {enviando ? "Criando..." : "Criar minha conta"}
          </Button>
        </div>
      </form>

      <aside style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 16 }}>
        <section className="wl-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "var(--ink-muted)" }}>Plano escolhido</span>
            <Button variante="quieto" compacto onClick={aoTrocarPlano}>
              Trocar
            </Button>
          </div>
          <p style={{ margin: "8px 0 0", fontSize: 22, fontWeight: 600 }}>{plano.nome}</p>
          <p style={{ margin: "4px 0 0" }}>
            {reais(preco)} {ciclo === "anual" ? "por ano" : "por mês"}
          </p>
          <p style={{ margin: "8px 0 0", color: "var(--ink-muted)", fontSize: 14 }}>
            {[
              plano.limites.veiculos === null ? "Veículos sem limite" : `${plano.limites.veiculos} veículos`,
              plano.limites.filiais === null ? "" : `${plano.limites.filiais} ${plano.limites.filiais === 1 ? "filial" : "filiais"}`,
              plano.limites.usuarios === null ? "" : `${plano.limites.usuarios} usuários`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </section>
        <section className="wl-panel">
          <h2 style={{ margin: "0 0 8px", fontSize: 17, fontWeight: 600 }}>{semTeste ? "Como funciona" : "Como funciona o teste"}</h2>
          {semTeste ? (
            <div style={{ display: "flex", gap: 14, padding: "12px 0" }}>
              <span style={{ width: 64, fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--ink-muted)" }}>hoje</span>
              <span>1ª fatura de {reais(preco)}, vencendo hoje.</span>
            </div>
          ) : (
            [
              { dia: "hoje", texto: `Sistema criado e teste de ${catalogo.teste.dias} dias começa. R$ 0,00` },
              { dia: diaEMes(catalogo.teste.lembrete), texto: `Lembrete por e-mail de que a primeira fatura vence em ${diaEMes(catalogo.teste.primeira_fatura)}.` },
              { dia: diaEMes(catalogo.teste.primeira_fatura), texto: "Primeira mensalidade, só se você quiser continuar." },
            ].map((linha) => (
              <div key={linha.dia} style={{ display: "flex", gap: 14, padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ flex: "none", width: 64, fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--ink-muted)" }}>{linha.dia}</span>
                <span>{linha.texto}</span>
              </div>
            ))
          )}
        </section>
      </aside>
    </div>
  );
}
