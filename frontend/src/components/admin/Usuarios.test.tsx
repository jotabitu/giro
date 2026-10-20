// Administração › Usuários (T-169) contra docs/telas/html/Admin-Usuarios-*.dc.html, com o seed da tela (USR-01 a USR-09, PLT-03).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { contas, usuarios, type Eu } from "@/lib/api";
import { filiaisDoUsuario, situacaoDoUsuario, ultimoAcesso } from "@/lib/usuarios";
import { reiniciarUsuariosFalso } from "@/testes/falsos/falso-usuarios";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push() {}, replace() {} }), usePathname: () => "/admin/usuarios", useSearchParams: () => new URLSearchParams() }));

import { ListaUsuarios } from "./ListaUsuarios";
import { PainelDoUsuario } from "./PainelDoUsuario";

const texto = (h: string) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, "|");

async function entrar(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa === "configurar_2fa") await contas.configurar2fa(r.token_pre_2fa);
  if (r.etapa !== "pronto") {
    const v = await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
    if (v.etapa !== "pronto") throw new Error("esperava pronto");
  }
  sessao.eu = await contas.eu();
}

async function pagina(): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["usuarios", { aba: "todos", cursor: undefined }], await usuarios.listar());
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <ListaUsuarios />
    </QueryClientProvider>,
  );
}

async function painel(id: number): Promise<string> {
  const cache = new QueryClient();
  cache.setQueryData(["usuarios", "detalhe", id], await usuarios.obter(id));
  cache.setQueryData(["usuarios", "sessoes", id], await usuarios.sessoes(id));
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <PainelDoUsuario id={id} eu={sessao.eu as Eu} aoConcluir={() => {}} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-07T15:00:00Z"));
  reiniciarUsuariosFalso();
});
afterEach(() => vi.useRealTimers());

describe("lista de usuários (Admin-Usuarios)", () => {
  it("cabeçalho, plano 5 de 10 e abas com as contagens da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("Administração|Usuários");
    expect(t).toContain("5 de 10 no plano");
    expect(t).toContain("Convidar pessoa");
    expect(t).toContain("Todos|6");
    expect(t).toContain("Ativos|3");
    expect(t).toContain("Convites pendentes|2");
    expect(t).toContain("Desativados|1");
    expect(t).toContain("Usuários do plano");
  });

  it("as seis pessoas com perfil, filial, último acesso e situação", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    for (const trecho of ["Mariana Costa (você)", "Administrador", "Todas", "agora", "Ativo · 2FA", "Rodrigo Pinheiro", "Gerente", "Centro", "há 2 h", "Bruna Alves", "ontem", "João Silva", "Convite enviado", "Reenviar", "Felipe Nunes", "12 set", "Desativado"]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(t).toContain("Pessoa|Perfil|Filial|Último acesso|Situação");
  });

  it("celular: convite pendente leva Reenviar e Cancelar, e o desativado aparece como Inativo", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("Pendente");
    expect(t).toContain("Cancelar");
    expect(t).toContain("Inativo");
    expect(t).toContain("desativado em 12 set");
  });

  it("só o administrador acessa (USR-05)", async () => {
    await entrar("rodrigo@motorapida.com.br");
    const t = texto(await pagina());
    expect(t).toContain("Só o administrador acessa Usuários.");
    expect(t).not.toContain("Rodrigo Pinheiro");
  });
});

describe("painel da pessoa", () => {
  it("gerente: perfil, filiais, permissões com o padrão do perfil travado e desativar", async () => {
    await entrar("mariana@motorapida.com.br");
    const html = await painel(2);
    const t = texto(html);
    for (const trecho of ["Rodrigo Pinheiro", "Entrou em 07 out", "2FA ativa", "Perfil", "Filiais com acesso", "Permissões extras", "Aprovar descontos acima de 5%", "Padrão do perfil Gerente", "Cancelar contratos", "Fica registrado na auditoria", "Ver relatórios de todas as filiais", "Hoje vê só Filial Centro", "Salvar alterações", "Desativar acesso", "Ele sai do sistema na hora."]) {
      expect(t, trecho).toContain(trecho);
    }
    expect(html).toMatch(/disabled=""[^>]*checked|checked=""[^>]*disabled=""/);
    expect(t).toContain("Sessões abertas");
    expect(t).toContain("Chrome no Windows");
    expect(t).toContain("Redefinir 2 etapas");
  });

  it("a própria pessoa não se desativa nem redefine as 2 etapas", async () => {
    await entrar("mariana@motorapida.com.br");
    const t = texto(await painel(1));
    expect(t).not.toContain("Desativar acesso");
    expect(t).not.toContain("Redefinir 2 etapas");
  });

  it("convite pendente: reenviar e cancelar; desativado: reativar", async () => {
    await entrar("mariana@motorapida.com.br");
    expect(texto(await painel(5))).toContain("Reenviar convite|Cancelar convite");
    expect(texto(await painel(5))).toContain("Copiar link do convite");
    const t = texto(await painel(8));
    expect(t).toContain("Reativar acesso");
    expect(t).not.toContain("Salvar alterações");
  });
});

describe("copiar link do convite (USR-01, CA-248-12 a 15)", () => {
  it("o botão e o aviso aparecem só no convite pendente, pelo acoes da API", async () => {
    await entrar("mariana@motorapida.com.br");
    const pendente = texto(await painel(5));
    expect(pendente).toContain("Copiar link do convite");
    expect(pendente).toContain("O link anterior deixa de valer.");
    for (const id of [1, 8]) expect(texto(await painel(id)), `usuário ${id}`).not.toContain("Copiar link do convite");
  });

  it("sem acoes.copiar_link_convite o botão some, mesmo com convite pendente", async () => {
    await entrar("mariana@motorapida.com.br");
    const cache = new QueryClient();
    const u = await usuarios.obter(5);
    cache.setQueryData(["usuarios", "detalhe", 5], { ...u, acoes: { ...u.acoes, copiar_link_convite: false } });
    cache.setQueryData(["usuarios", "sessoes", 5], []);
    const t = texto(
      renderToStaticMarkup(
        <QueryClientProvider client={cache}>
          <PainelDoUsuario id={5} eu={sessao.eu as Eu} aoConcluir={() => {}} />
        </QueryClientProvider>,
      ),
    );
    expect(t).not.toContain("Copiar link do convite");
    expect(t).toContain("Reenviar convite");
  });

  it("a API devolve o link novo e o aviso; ativo e desativado respondem 409", async () => {
    const r = await usuarios.copiarLinkDoConvite(5);
    expect(r.link).toContain("/convite/");
    expect(r.aviso).toBe("O link anterior deixa de valer.");
    await expect(usuarios.copiarLinkDoConvite(1)).rejects.toMatchObject({ status: 409, codigo: "transicao_usuario" });
  });
});

describe("regras na API falsa (contas.md)", () => {
  it("convidar conta no plano e o 11º é recusado com PLT-03", async () => {
    await usuarios.convidar({ email: "a@x.com", perfil: "vendedor", filiais: [1] });
    expect((await usuarios.listar()).plano.usado).toBe(6);
    for (const n of [1, 2, 3, 4]) await usuarios.convidar({ email: `n${n}@x.com`, perfil: "vendedor", filiais: [1] });
    await expect(usuarios.convidar({ email: "z@x.com", perfil: "vendedor", filiais: [1] })).rejects.toMatchObject({ codigo: "PLT-03" });
  });

  it("e-mail repetido responde email_em_uso e filial é obrigatória fora do administrador", async () => {
    await expect(usuarios.convidar({ email: "bruna@motorapida.com.br", perfil: "vendedor", filiais: [1] })).rejects.toMatchObject({ codigo: "email_em_uso" });
    await expect(usuarios.convidar({ email: "b@x.com", perfil: "gerente", filiais: [] })).rejects.toMatchObject({ status: 400 });
  });

  it("desativar libera vaga; não desativa a si mesmo; reativar quem nunca entrou volta como convite", async () => {
    await expect(usuarios.desativar(1)).rejects.toMatchObject({ codigo: "desativar_a_si_mesmo" });
    await usuarios.desativar(4);
    expect((await usuarios.listar()).plano.usado).toBe(4);
    await usuarios.cancelarConvite(5);
    expect((await usuarios.reativar(5)).status).toBe("convite_pendente");
    expect((await usuarios.reativar(8)).status).toBe("ativo");
  });

  it("o último administrador não perde o perfil", async () => {
    await expect(usuarios.alterar(1, { perfil: "gerente" })).rejects.toMatchObject({ codigo: "ultimo_administrador" });
  });

  it("redefinir 2 etapas exige motivo", async () => {
    await expect(usuarios.redefinir2fa(2, " ")).rejects.toMatchObject({ status: 400 });
    expect((await usuarios.redefinir2fa(2, "Perdeu o celular")).dois_fatores_ativo).toBe(false);
  });
});

describe("apoio da tela", () => {
  it("último acesso: agora, há N h, ontem, data e traço", () => {
    const agora = new Date("2026-10-07T15:00:00Z");
    expect(ultimoAcesso("2026-10-07T14:58:00Z", agora)).toBe("agora");
    expect(ultimoAcesso("2026-10-07T13:00:00Z", agora)).toBe("há 2 h");
    expect(ultimoAcesso("2026-10-06T14:00:00Z", agora)).toBe("ontem");
    expect(ultimoAcesso("2026-09-12T15:00:00Z", agora)).toBe("12 set");
    expect(ultimoAcesso(null, agora)).toBe("—");
  });

  it("situação e filiais como nas telas", () => {
    expect(situacaoDoUsuario({ status: "ativo", dois_fatores_ativo: false }).rotulo).toBe("Ativo");
    expect(situacaoDoUsuario({ status: "convite_pendente", dois_fatores_ativo: false }).tom).toBe("info");
    expect(filiaisDoUsuario({ filiais: [{ id: 1, nome: "Filial Centro", nome_curto: "Filial Centro" }], todas_filiais: false })).toBe("Centro");
    expect(filiaisDoUsuario({ filiais: [], todas_filiais: true })).toBe("Todas");
  });
});
