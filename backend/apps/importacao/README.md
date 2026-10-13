# app `importacao`

**Schema:** empresa · **Nível:** 13 na ordem da ADR 0011 (ADR 0017): chama `veiculos`, `clientes`, `filiais`, `plataforma`, `contas` e `notificacoes`; ninguém depende dele.
**Regras:** IMP-02, IMP-03, IMP-05, VEI-01, CLI-01, CLI-03, AUD-04, AUD-05, AUD-09
**Tela:** Onboarding-Importar (passo "Importar dados" do assistente)
**Contrato:** `docs/api/importacao.md`

## Estrutura

```
importacao/
├── models.py       Importacao (máquina de estados, auditada) e LinhaImportacao (temporária)
├── planilha.py     leitura do .xlsx/.csv (limites, conteúdo, cabeçalho) e o modelo para baixar
├── linhas.py       da célula para o corpo do cadastro e a validação de cada linha (IMP-02)
├── services.py     enviar, validar, corrigir, ignorar, importar/gravar, cancelar, limpar
├── selectors.py    representações; linha de cliente resumida para o suporte (AUD-09)
├── tasks.py        importacao_validar (5 min), importacao_importar (15 min), importacao_limpar (diária, 04:00)
└── api/            serializers, views e urls (só administrador; o suporte lê e, com "ver e editar", importa)
```

## Como funciona

- O envio confere o arquivo na hora (extensão, conteúdo, 5 MB, zip até 200 entradas e 50 MB, cabeçalho, 5.000 linhas) e grava a planilha no storage privado com nome aleatório. A validação das linhas roda na task, sem gravar nada nos cadastros.
- Cada linha passa por `veiculos.services.validar_novo` ou `clientes.services.validar_novo` (as validações do cadastro, sem gravar) e pela repetição dentro da planilha (`chave_placa`, `chave_chassi`, `chave_documento` com o hash da ADR 0014). As mensagens da tela ("Placa QXA4B2 está incompleta", "Chassi repetido na linha 12", "Ano do modelo em branco") saem de `linhas.py`. Em clientes, as mensagens não citam o valor.
- Linhas de clientes ficam em `dados_cifrados` (JSON cifrado); o arquivo de clientes é apagado logo depois da validação (no S3, com todas as versões).
- Importar trava o `UsoEmpresa` (`plataforma.services.vagas_no_plano`) numa transação só e grava cada linha num savepoint, pelo `cadastrar` do app dono, com o ator de quem pediu. O que passa do limite fica `acima_do_limite` e a importação termina com o `aviso` `IMP-03`. Ao concluir: auditoria `importacao.concluir`, passo `importar` da implantação (`IMP-05`) e aviso no sino.
- Arquivo e linhas saem 30 dias depois do envio (`apagar_em`).

Testes: `tests/aceitacao/test_t027_importacao.py`.
