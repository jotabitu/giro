// Editar cliente (T-516, CLI-01, CLI-03): o formulário do cadastro com os dados da ficha, o tipo fixo e o PATCH só com o que mudou.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { clientes, contas, type ClienteCompleto, type Eu } from "@/lib/api";
import { paraCorpoDeEdicao, valoresDoCliente } from "@/lib/clientes";
import { reiniciarClientesFalsos } from "@/testes/falsos/falso-clientes";

const sessao = vi.hoisted(() => ({ eu: null as unknown }));
vi.mock("@/lib/sessao", () => ({ useSessao: () => ({ eu: sessao.eu as Eu, sair: async () => {} }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {} }) }));

import { EditarCliente } from "./EditarCliente";
import { NovoClienteForm } from "./NovoClienteForm";

async function entrarComo(email: string) {
  const r = await contas.entrar({ email, senha: "senhaforte123", aparelho: "desktop" });
  if (r.etapa !== "pronto") await contas.verificar2fa(r.token_pre_2fa, { codigo: "123456" });
  sessao.eu = await contas.eu();
}

function html(id: number, c: unknown) {
  const cache = new QueryClient();
  cache.setQueryData(["cliente", id], c);
  return renderToStaticMarkup(
    <QueryClientProvider client={cache}>
      <EditarCliente id={id} />
    </QueryClientProvider>,
  );
}

afterEach(() => reiniciarClientesFalsos());

describe("editar cliente: Juliana Rocha", () => {
  let juliana: ClienteCompleto;
  beforeAll(async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    juliana = (await clientes.obter(1201)) as ClienteCompleto;
  });

  it("abre com os dados do cliente, o tipo fixo e a barra com Cancelar para a ficha e Salvar alterações", () => {
    const h = html(1201, juliana);
    expect(h).toContain("Editar cliente");
    // O formulário é não controlado: os valores entram pelo defaultValues e não saem no HTML do servidor.
    expect(valoresDoCliente(juliana)).toMatchObject({
      nome: "Juliana Rocha",
      celular: "(85) 98114-2290",
      nascimento: "1994-07-02",
      email: "juliana.rocha@email.com",
      profissao: "Entregadora",
      cnh: { numero: "03811234562", categoria: "A", validade: "2030-11-18", primeira_habilitacao: "2016-08-10" },
      endereco: { cep: "60115-190", logradouro: "Rua Monsenhor Bruno", numero: "1120", bairro: "Aldeota", cidade: "Fortaleza", uf: "CE" },
      referencia: { nome: "Sandra Rocha", parentesco: "mãe", telefone: "(85) 98822-4410" },
      consentimento: true,
    });
    expect(h).toContain('href="/clientes/1201">Juliana Rocha</a> / Editar');
    // Tipo travado: sem o seletor Pessoa física / Pessoa jurídica.
    expect(h).not.toContain("Tipo de cliente");
    expect(h).toContain("Pessoa física");
    expect(h).not.toContain("Pessoa jurídica");
    expect(h).toContain('href="/clientes/1201"');
    expect(h.match(/>Cancelar</g)).toHaveLength(1);
    expect(h.match(/>Salvar alterações</g)).toHaveLength(1);
    expect(h).not.toContain("Salvar e iniciar locação");
    expect(h).toContain("sticky bottom-[88px]");
  });

  it("os documentos já enviados aparecem como enviados", () => {
    const h = html(1201, juliana);
    expect(h.match(/Enviado\. Toque para trocar/g)).toHaveLength(4);
  });

  it("o cadastro novo continua com o seletor de tipo e sem o 'Editar cliente'", () => {
    const h = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <NovoClienteForm />
      </QueryClientProvider>,
    );
    expect(h).toContain("Tipo de cliente");
    expect(h).toContain("Novo cliente");
    expect(h).not.toContain("Editar cliente");
  });

  it("test_cli_01_patch_manda_so_o_que_mudou", () => {
    const antes = valoresDoCliente(juliana);
    expect(paraCorpoDeEdicao(antes, antes)).toEqual({});
    expect(paraCorpoDeEdicao({ ...antes, email: "nova@email.com", celular: "(85) 98888-0000" }, antes)).toEqual({ email: "nova@email.com", celular: "85988880000" });
    // O documento com a máscara de antes não conta como mudança; trocar o dígito conta, sempre só com números.
    expect(paraCorpoDeEdicao({ ...antes, documento: "529.982.247-25" }, antes)).toEqual({ documento: "52998224725" });
    // Bloco que mudou vai inteiro; o tipo nunca vai.
    const corpo = paraCorpoDeEdicao({ ...antes, endereco: { ...antes.endereco, numero: "1130" } }, antes);
    expect(corpo).toEqual({ endereco: { cep: "60115190", logradouro: "Rua Monsenhor Bruno", numero: "1130", bairro: "Aldeota", cidade: "Fortaleza", uf: "CE" } });
    expect(corpo).not.toHaveProperty("tipo");
  });

  it("test_cli_03_patch_manda_o_campo_apagado_vazio_ou_null", () => {
    const antes = valoresDoCliente(juliana);
    // Texto vai "", data vai null, bloco inteiro vai null (PatchedClienteEdicao; conferido na API real).
    expect(paraCorpoDeEdicao({ ...antes, email: "", profissao: "", nascimento: "" }, antes)).toEqual({ email: "", profissao: "", nascimento: null });
    expect(paraCorpoDeEdicao({ ...antes, cnh: { numero: "", categoria: "", validade: "", primeira_habilitacao: "" }, referencia: { nome: "", parentesco: "", telefone: "" } }, antes)).toEqual({ cnh: null, referencia: null });
    // Um subcampo apagado com o resto do bloco: a API junta o bloco com o que já tem, então omitir não apagaria.
    expect(paraCorpoDeEdicao({ ...antes, cnh: { ...antes.cnh, validade: "" }, referencia: { ...antes.referencia, parentesco: "" } }, antes)).toEqual({
      cnh: { numero: "03811234562", categoria: "A", validade: null, primeira_habilitacao: "2016-08-10" },
      referencia: { nome: "Sandra Rocha", parentesco: "", telefone: "85988224410" },
    });
  });

  it("test_cli_03_patch_apagar_dado_obrigatorio_leva_a_incompleto", async () => {
    const r = await clientes.atualizar(1201, { nascimento: null });
    expect(r.nascimento).toBeNull();
    expect(r.status).toBe("incompleto");
    expect(r.pendencias).toContain("nascimento");
  });

  it("test_cli_01_patch_com_documento_de_outro_cliente_volta_409_com_o_cadastro_existente", async () => {
    // O CPF do seed não tem dígito verificador válido; cadastra um cliente com CPF válido para ser o "outro".
    const outro = await clientes.criar({ tipo: "pf", nome: "Outro Cliente", documento: "52998224725", celular: "85988880000" });
    await expect(clientes.atualizar(1201, { documento: "529.982.247-25" })).rejects.toMatchObject({ status: 409, codigo: "CLI-01", detalhes: { cliente_id: outro.id, nome: "Outro Cliente" } });
    // O documento com dígito errado volta no campo.
    await expect(clientes.atualizar(1201, { documento: "11111111111" })).rejects.toMatchObject({ status: 400, campos: { documento: expect.any(String) } });
  });

  it("test_cli_03_patch_salva_e_a_ficha_devolve_o_novo_valor", async () => {
    const r = await clientes.atualizar(1201, { email: "outro@email.com" });
    expect(r.email).toBe("outro@email.com");
    expect(((await clientes.obter(1201)) as ClienteCompleto).email).toBe("outro@email.com");
  });
});

describe("editar cliente: perfil sem permissão", () => {
  it("sem clientes_cadastrar não abre o formulário", async () => {
    await entrarComo("rodrigo@motorapida.com.br");
    const c = await clientes.obter(1201);
    sessao.eu = { ...(sessao.eu as Eu), pode: { ...(sessao.eu as Eu).pode, clientes_cadastrar: false } };
    const h = html(1201, c);
    expect(h).toContain("Seu perfil não tem acesso a esta ação.");
    expect(h).not.toContain("Salvar alterações");
  });
});
