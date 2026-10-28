# T-383 · Comando do primeiro Dono da plataforma · backend → orquestrador, seguranca, devops, arquiteto

**O que foi feito:**
- `python manage.py criar_dono_da_plataforma <email> --nome "..."` (`apps/contas/management/commands/`):
  - recusa se a plataforma já tem um Dono ("Convide a equipe com o convidar_equipe_plataforma.") ou se o e-mail já tem conta;
  - pede a senha duas vezes pelo `getpass`, sem eco, e confere a força com os mesmos validadores da API (`validar_senha`). Não existe opção de senha: `--senha` dá erro de argumento;
  - cria a pessoa no `public` pelo `Usuario.objects.create_superuser`, a mesma porta do `createsuperuser`. Ela nasce com a função Dono, acesso ao Admin e superusuário, e fica `convite_pendente`. O evento é `usuario.criar_dono`, de segurança, regra `PLT-09`, sem a senha;
  - mostra o `otpauth://` (emissor Giro) e a chave legível, e pede o código de 6 dígitos. Com o código certo, confirma o autenticador, imprime os 8 códigos de recuperação uma vez e passa a pessoa a `ativo` (`usuario.ativar`). Com o código errado, nada fica criado: tudo roda numa transação só.
- `backend/README.md`: o comando entra no lugar do `createsuperuser` na lista.

**Onde:** `backend/apps/contas/management/commands/criar_dono_da_plataforma.py`. Nenhum serviço novo e nenhuma rota. O teste `test_t277_is_staff_so_pelo_createsuperuser` continua passando: o comando não cita o campo e usa o `create_superuser`.

**Contrato:** sem rota nova; o OpenAPI não muda.

**Regras cobertas:** PLT-08, PLT-09. Testes em `tests/aceitacao/test_t383_criar_dono.py`:
- `test_plt_09_criar_dono_com_2_etapas`: o Dono ativo, com o autenticador confirmado, 8 códigos e a auditoria. Depois ele entra no Django Admin com a senha e o código;
- `test_plt_08_codigo_errado_nao_cria_nada`, `test_plt_09_senhas_diferentes_ou_fraca_nao_criam`;
- `test_plt_09_so_o_primeiro_dono`, `test_plt_09_email_em_uso`;
- `test_plt_08_senha_nunca_na_linha_de_comando`.

**O que ficou de fora:**
- O `createsuperuser` continua existindo (é do Django). Ele aceita a senha pela variável `DJANGO_SUPERUSER_PASSWORD` e não exige as 2 etapas, mas o login do Admin recusa quem não tem autenticador. Desligá-lo ou deixá-lo é decisão da segurança.
- Os documentos que citam o `createsuperuser` como o jeito de criar o Dono não são do backend e ficaram como estavam: o ADR 0029 (itens 24 e 42), do arquiteto, e o `infra/README.md` ("Como abrir o Admin"), do devops.

**Próximo passo para quem recebe:**
- Segurança: revisar o comando (a chave do autenticador aparece no terminal de quem roda, como na tela de configurar) e decidir sobre o `createsuperuser`.
- DevOps: trocar o `createsuperuser` pelo `criar_dono_da_plataforma` no `infra/README.md` e no roteiro de subida da homologação.
- Arquiteto: atualizar o ADR 0029, se quiser citar o comando.
