"""T-014 · Clientes, documentos, bloqueio, LGPD (docs/qa/criterios/T-014.md).

Os critérios marcados [integração] (CA-014-15, 16, 19, 20, 21 e a parte com locação/financeiro
de CA-014-18) ficam para a T-019, com o seed completo. Aqui entram só os que a T-014 sozinha prova.
"""

from .apoio import aguarda, pendente

T = "T-014"


@aguarda(T)
def test_cli_01_ca_014_01_cpf_validado_e_unico():
    pendente(
        cpf_digito_errado=("123.456.789-00", 400, "validacao"),
        cpf_repetido_digitos=("111.111.111-11", 400),
        cpf_de_juliana_duplicado=(409, "CLI-01", {"nome": "Juliana Rocha"}),
        cnpj_pj="12.345.678/0001-10 aceito; repetido 409 CLI-01",
    )


@aguarda(T)
def test_cli_03_ca_014_02_salvar_incompleto():
    pendente(
        quem="Bruna",
        cliente="Lucas Ferreira",
        cpf="12345678909",
        status=(201, "incompleto"),
        pendencias=["4 documentos", "consentimento", "cnh", "endereco", "referencia", "nascimento"],
    )


@aguarda(T)
def test_cli_03_ca_014_03_completar_leva_a_ativo():
    pendente(
        ultimo_documento="ativo, pendencias vazia",
        tirar_endereco="volta a incompleto",
        bloqueado_que_completa="continua bloqueado",
    )


@aguarda(T)
def test_cli_03_ca_014_04_consentimento():
    pendente(
        consentimento_true="grava consentimento_em do servidor",
        patch_false="não apaga consentimento_em",
    )


@aguarda(T)
def test_cli_08_ca_014_05_salvar_e_iniciar_locacao():
    pendente(post_devolve_id=True, endpoint_separado=False)


@aguarda(T)
def test_cli_08_ca_014_06_quem_cadastra():
    pendente(
        cadastram_e_editam=["Mariana", "Rodrigo", "Bruna"],
        recebem_403_em_post_e_patch=["João", "Lúcia"],
    )


@aguarda(T)
def test_aud_04_ca_014_07_mascara_nas_listas():
    pendente(
        juliana="***.218.330-**",
        lucas="***.456.789-**",
        qualquer_perfil=True,
        ausentes=["documento", "cnh", "endereco", "documentos"],
        pj="CNPJ inteiro",
    )


@aguarda(T)
def test_aud_04_ca_014_08_detalhe_completo_so_para_quem_cadastra():
    pendente(
        completo=["Mariana", "Rodrigo", "Bruna"],
        documento="05221833018",
        resumido_com_200=["João", "Lúcia"],
    )


@aguarda(T)
def test_aud_09_ca_014_09_suporte_giro_sempre_mascarado():
    pendente(
        suporte="Diego Santos",
        permissoes=["ver", "ver e editar"],
        detalhe_de_juliana="***.218.330-** resumido",
        ausentes=["cnh.numero", "endereço", "URLs de documentos"],
        busca_ou_exportacao_com_cpf_completo=False,
    )


@aguarda(T)
def test_aud_05_ca_014_10_documentos_privados():
    pendente(
        url_vence_minutos=15,
        cada_get="novas URLs",
        auditoria_de_acesso_a_documento="quem viu",
        foto_sem_exif_gps=True,
        mais_de_10_mb=400,
        reenviar_cnh_frente="anterior inativo e guardado",
    )


@aguarda(T)
def test_aud_04_ca_014_11_auditoria_sem_dado_pessoal_aberto():
    pendente(
        editar_endereco_de_juliana="evento com antes e depois mascarados",
        cpf_cnh_completos_no_evento=False,
    )


@aguarda(T)
def test_cli_01_ca_014_12_busca_por_cpf():
    pendente(
        busca_cpf_completo={"05221833018": "Juliana (por hash)"},
        cpf_parcial={"052.218": "ninguém"},
        nome={"Juli": "Juliana"},
        celular={"98114": "acha"},
    )


@aguarda(T)
def test_cli_02_ca_014_13_itens_da_analise():
    pendente(
        juliana={
            "cpf": "ok CPF válido",
            "cnh": "ok",
            "lista_bloqueio": "ok",
            "historico": "pendente Sem histórico",
            "documentos": "ok",
            "credito": "ausente",
        },
        lucas_sem_2_documentos="documentos pendente, Faltam 2 documentos",
        analisar="mesmo resultado sem gravar",
    )


@aguarda(T)
def test_cli_02_ca_014_14_impedimentos_para_retirada():
    pendente(
        data="2026-10-07",
        casos=[
            ("Lucas incompleto", "CLI-03"),
            ("CNH só B, moto", "CLI-02"),
            ("CNH A, carro", "CLI-02"),
            ("CNH vencida 2026-09-17 (20 dias)", None, "vencida"),
            ("CNH vencida 2026-09-06 (31 dias)", "CLI-02", "vencida_impede"),
            ("CNH vencida 2026-09-07 (30 dias)", None),
            ("Rafael bloqueado", "CLI-05"),
            ("cliente inativo", "cliente_inativo"),
            ("Juliana CNH A, moto", None),
        ],
    )


@aguarda(T)
def test_cli_05_ca_014_17_bloqueio_e_desbloqueio_manuais():
    pendente(
        bloquear=(
            "Rodrigo",
            "Ana Beatriz",
            "Documento falso",
            200,
            {"motivo": "manual", "desbloqueia_sozinho": False},
        ),
        bloquear_de_novo=(409, "transicao_cliente"),
        desbloquear_rodrigo_ou_mariana="200 na hora com auditoria",
        bruna_pede=(202, {"tipo": "APR-05", "status": "pendente"}),
        aprovado_por_rodrigo="ativo",
        bruna_com_extra_aprovar_o_proprio_pedido="recusado (APR-09)",
        bruna_bloquear=403,
        joao_lucia=403,
    )


@aguarda(T)
def test_cli_06_ca_014_18_inativar_e_reativar():
    pendente(
        rodrigo_inativa_ana=(200, "inativo"),
        fora_da_lista_padrao=True,
        filtro="?situacao=inativos",
        impedimentos_para_nova_locacao="cliente_inativo",
        reativar="ativo ou incompleto",
        bruna=403,
        integracao_t019=["Juliana com LOC-2836 e Carlos com R$ 299,40 → 422 cliente_com_pendencia"],
    )


@aguarda(T)
def test_cli_07_ca_014_22_filtros():
    pendente(
        bloqueados="só Rafael (e bloqueados à mão)", incompletos="Lucas", depende_de_x_filial=False
    )
